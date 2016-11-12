#!/usr/bin/env python
import argparse
import logging
import os
import pathlib
import sys
from typing import Dict, Any

import yaml
from docker import Client


logging.basicConfig()
logger = logging.getLogger('buildr')
logger.setLevel(logging.DEBUG)


class BuildError(Exception):
    """Defines an error during the process, this doesn't mean
    anything failed but instead that either a precondition failed
    or a pre-build item."""


class BuildFailure(Exception):
    """Defines a failure in a build step,"""


class ManifestV1:
    def __init__(self, manifest_def):
        self._def = manifest_def

        self._stages = None  # type: Optional[List]
        self._env = None  # type: Optional[List[str]]

    @property
    def stages(self):
        """List of stages to be executed, in order"""
        if self._stages is None:
            self._stages = self._def.get('stages', [])
            if self._def.get('prepare'):
                if 'prepare' in self._stages:
                    self._stages.remove('prepare')
                self._stages.insert(0, 'prepare')
        return self._stages

    @property
    def image(self):
        """Base docker image to run within"""
        return self._def.get('image', 'buildr-ubuntu')

    @property
    def env(self):
        """Prepared environmental variables"""
        if self._env is None:
            self._env = []
            env = self._def.get('environment', {})
            if env.get('inherit', False):
                for e in os.environ.items():
                    self._env.append('='.join(e))
            for var in env.get('vars', []):
                self._env.append(var)
        return self._env

    def __getitem__(self, value):
        return self._def.get(value)


def parse_args():
    parser = argparse.ArgumentParser(prog='buildr',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)  # noqa
    parser.add_argument('--path', help='Local directory path', type=str,
                        default=True)
    parser.add_argument('--docker-sock', help='Docker sock', type=str,
                        default='unix://var/run/docker.sock')

    return parser.parse_args()


def load_manifest(project_dir: pathlib.Path) -> ManifestV1:
    if not project_dir.exists():
        sys.exit('Project directory does not exist')
    logger.debug('Searching for manifest in %s', project_dir)

    buildr = project_dir / '.buildr.yml'
    if not buildr.exists():
        sys.exit('Build definition not found in project.')

    logger.debug('Found manifest, loading...')

    with open(str(buildr.absolute()), 'r') as f:
        manifest = yaml.safe_load(f)
        if manifest.get('version', 1) == 1:
            return ManifestV1(manifest)
        sys.exit('Illegal manifest version')


def run_manifest(manifest: ManifestV1, target_dir: pathlib.Path, *,
                 docker_sock='unix://var/run/docker.sock'):
    logger.debug('Project directory: %s', target_dir)

    stages = manifest.stages
    image = manifest.image
    env_vars = manifest.env

    logger.debug('Connecting to docker sock: %s', docker_sock)
    cli = Client(base_url=docker_sock)

    # For debug, you can emulate this with:
    #   docker run -it -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}":/app \
    #   --workdir /app -e <your envvars> <manifest.image> sh
    container = cli.create_container(image=image,
                                     command='sh',
                                     detach=True,
                                     environment=env_vars,
                                     stdin_open=True,
                                     working_dir='/app',
                                     volumes=[
                                         '/app',
                                         '/var/run/docker.sock',
                                         '/root/.docker/config.json',
                                     ],
                                     host_config=cli.create_host_config(binds=[
                                         '{}:/app'.format(target_dir.absolute()),  # noqa
                                         '/var/run/docker.sock:/var/run/docker.sock',  # noqa
                                         # TODO: this is per user, not sure how it works
                                         # if we run in the container as a diff user
                                         '/root/.docker/config.json:/root/.docker/config.json'
                                     ]))

    container_id = container['Id']
    try:
        logger.debug('Created container: %s', container_id)
        cli.start(container_id)
        logger.debug('Started container')

        logger.debug('Running stages: %s', stages)
        for stage_name in stages:
            # TODO: precondition check once we decide how to do that.
            logger.info('Executing stage: %s', stage_name)
            stage = manifest[stage_name]
            for script in stage.get('script', []):
                logger.debug('Executing script "%s"', script)
                # TODO: Add user, by default run as non-root unless manifest suggests we need it
                # You can emulate this with:
                #   docker exec <container_name> <script>
                exec_ = cli.exec_create(container_id, script)
                exec_id = exec_['Id']

                for chunk in cli.exec_start(exec_id, stream=True):
                    try:
                        sys.stdout.write(chunk.decode())
                    except UnicodeDecodeError:
                        pass

                result = cli.exec_inspect(exec_id)
                ec = result['ExitCode']
                if ec != 0:
                    if stage_name == 'prepare':
                        logger.error('Command exited with error, unable to prepare the environment.')
                        raise BuildError('Prepare failed, unable to set up the environment.')
                    else:
                        logger.error('Command exited with error, build failed.')
                        raise BuildFailure('Stage failed.')

            logger.info('Stage "%s" passed', stage_name)
    except KeyboardInterrupt:
        print('Exiting gracefully')
    except Exception as e:
        logger.error('Error running manifest:', e)
    finally:
        print('Killing container...')
        cli.kill(container_id)
        print('Removing container...')
        cli.remove_container(container_id)
        print('Finished.')


def main():
    args = parse_args()

    target_dir = pathlib.Path(args.path)
    manifest = load_manifest(target_dir)
    run_manifest(manifest, target_dir, docker_sock=args.docker_sock)


if __name__ == '__main__':
    main()

