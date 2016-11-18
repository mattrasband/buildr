import logging
import pathlib

import yaml

# from .abc import AbstractManifest, AbstractStage
from .exc import BuildError

logger = logging.getLogger('buildr')


class ManifestV1:
    """Required properties for a version 1 manifest"""
    def __init__(self, manifest_def):
        self._def = manifest_def
        self._stages = None  # type: Optional[List]
        self._env = None  # type: Optional[List[str]]

    @property
    def stages(self):
        """List of stages to be executed, in order"""
        if self._stages is None:
            logger.debug('Loading stages')
            self._stages = self._def.get('stages', [])
            if self._def.get('prepare'):
                logger.debug('Found prepare, inserting as stage 0')
                if 'prepare' in self._stages:
                    self._stages.remove('prepare')
                self._stages.insert(0, 'prepare')
            logger.debug('Loaded stages: %s', self._stages)
        return self._stages

    @property
    def image(self):
        """Base docker image to run within"""
        return self._def.get('image', 'ubuntu:latest')

    @property
    def env(self):
        """Prepared environmental variables"""
        if self._env is None:
            logger.debug('Loading envvars')
            self._env = []
            env = self._def.get('environment', {})
            if env.get('inherit', False):
                logger.debug('Loading parent envvars')
                for e in os.environ.items():
                    self._env.append('='.join(e))
            for var in env.get('vars', []):
                self._env.append(var)
            logger.debug('Loaded %d envvars', len(self._env))
        return self._env

    def __getitem__(self, value):
        """Access stage definitions as dict keys"""
        return self._def.get(value)


    @staticmethod
    def from_file(project_dir: pathlib.Path):
        """Load the manifest from the project directory,
        erroring on the manifest not being found or the
        project directory not existing.
        :param project_dir: Where the project is on disk
        :returns ManifestV1: The parsed manifest"""
        logger.info('Searching for manifest in %s', project_dir.absolute())
        if not project_dir.exists():
            logger.error('Project directory does not exist.')
            raise BuildError('Project directory does not exist.')

        buildr = None
        for file_name in ['.buildr', '.buildr.yml', '.buildr.yaml']:
            logger.debug('Manifest candidate: %s', file_name)
            candidate = project_dir / file_name
            if not candidate.exists():
                logger.debug('Not found, moving on.')
                continue
            buildr = candidate
            break

        if buildr is None:
            print('Manifest not found, unable to continue')
            raise BuildError('Build manifest not found')
        logger.info('Found manifest: %s', buildr.absolute())

        with open(str(buildr.absolute()), 'r') as f:
            return ManifestV1(yaml.safe_load(f))
