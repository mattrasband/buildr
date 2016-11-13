"""\
Run the target project's manifest file, emulating a build
run on a CI system.
"""
import contextlib
import logging
import pathlib
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import Dict, Any, List

from buildr.buildr import Buildr
from buildr.exc import BuildError, BuildFailure
from buildr.manifest import ManifestV1

logger = logging.getLogger('buildr')


def run_manifest(manifest: ManifestV1, target_dir: pathlib.Path, *,
                 docker_sock='unix://var/run/docker.sock',
                 progress_writer=sys.stdout.write,
                 project_meta=None):
    """Run the manifest stages.

    :param manifest: The manifest to run
    :param target_dir: Which directory the source is in that the manifest
                       targets.
    :param docker_sock: Location of the docker engine socket.
    :param progress_writer: Stream to write echoed stdout from the
                            build container to, defaults to stdout."""
    logger.debug('Using docker sock: "%s"', docker_sock)

    with Buildr(target_dir, docker_sock=docker_sock, image=manifest.image,
                env=manifest.env) as buildr:
        for stage_name in manifest.stages:
            logger.info('Running stage "%s"', stage_name)
            stage = manifest[stage_name]
            for script in stage.get('script', []):
                rc = buildr.execute(script, writer=progress_writer)
                if rc != 0:
                    # TODO: get rid of the prepare concept and have a pre/post
                    # each stage instead, optionally.
                    if stage_name == 'prepare':
                        logger.error('Command exited with error, unable to '
                                        'prepare the environment.')
                        raise BuildError('Prepare failed, unable to set up '
                                            'the environment.')
                    else:
                        logger.error('Command exited with error, build '
                                        'failed.')
                        raise BuildFailure('Stage "%s" failed.', stage_name)
            logger.info('Stage "%s" success', stage_name)


def main():
    parser = ArgumentParser(prog='buildr',
                            description=__doc__,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--path', help='Local directory path', type=str,
                        default='.')
    parser.add_argument('--docker-sock', help='Docker sock', type=str,
                        default='unix://var/run/docker.sock')
    parser.add_argument('-d', '--debug', help='Debug logging',
                        action='store_const', dest='loglevel',
                        const=logging.DEBUG, default=logging.WARNING)
    parser.add_argument('-v', '--verbose', help='Be verbose',
                        action='store_const', dest='loglevel',
                        const=logging.INFO)
    args = parser.parse_args()

    logging.basicConfig()
    logger.setLevel(args.loglevel)

    target_dir = pathlib.Path(args.path)
    logger.info('Loading manifest from project directory %s',
                target_dir.absolute())
    manifest = ManifestV1.from_file(target_dir)
    try:
        run_manifest(manifest, target_dir, docker_sock=args.docker_sock)
    except BuildError as e:
        logger.error('Error preparing the environment, most likely unrelated to'
                     ' your code: %s', e)
        raise SystemExit(-1)
    except BuildFailure as e:
        logger.error('Build failed: %s', e)
        raise SystemExit(1)


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        main()
