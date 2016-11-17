import logging
import pathlib
import sys

import docker

logger = logging.getLogger('buildr')


class Buildr:
    def __init__(self, project_dir: pathlib.Path, *,
                 docker_sock='unix://var/run/docker.sock', image='docker',
                 env=None):
        """
        Main class that controls the build process, it provides a simple
        API so we can easily abstract out other ways to build if we don't
        end up using docker for them all. It could be cool to have a
        vagrant way.

        :param project_dir: Project directory path
        :param docker_sock: Docker socket
        :param image: Builder image, it must have docker installed in it.
                      Presuming you will be pulling/pushing from private
                      repos, you should have your docker/config.json in
                      the main user's home.
        """
        self.project_dir = project_dir
        self.base_url = docker_sock
        self.image = image
        self.env = env
        if env is None:
            self.env = []

        self.cli = None
        self.container_id = None
        self._cm = False

    def __enter__(self):
        logger.debug('Using docker sock %s', self.base_url)
        self.cli = docker.Client(base_url=self.base_url)
        self._pull_container()
        self.container_id = self._create_container()
        self._start_container()
        self._cm = True

        return self

    def __exit__(self, *args):
        self._close_container()
        self._cm = False

    def execute(self, command: str, writer=sys.stdout.write) -> int:
        """Execute a build command.
        :param command: Command to execute in the shell
        :returns: Exit code (int)"""
        if not self._cm:
            raise ValueError('Buildr must be run as a context manager to'
                             ' ensure all resources are reaped on exit.')

        # TODO: maybe we need to not log the command in case there is
        # something private in there...
        logger.debug('Executing command: "%s"', command)
        # You can emulate this with:
        #   docker exec <container_name> <script>
        exec_ = self.cli.exec_create(self.container_id, command)
        exec_id = exec_['Id']
        for chunk in self.cli.exec_start(exec_id, stream=True):
            try:
                writer(chunk.decode())
            except UnicodeDecodeError:
                pass

        result = self.cli.exec_inspect(exec_id)
        ec = result['ExitCode']
        if ec == 0:
            logger.debug('Command execution success')
        else:
            logger.error('Command execution failed: %r', result)
        return ec

    def _pull_container(self):
        if not ':' in self.image:
            sys.stderr.write('No tag provided on the image, defaulting '
                             'to latest')
            self.image += ':latest'
        for chunk in self.cli.pull(self.image, stream=True):
            try:
                sys.stdout.write(chunk.decode())
            except UnicodeDecodeError:
                pass

    def _create_container(self):
        """Creates the build runner container"""
        # For debug, you can emulate this with:
        #   docker run -it -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}":/app \
        #   --workdir /app -e <your envvars> <manifest.image> sh
        volumes = ['/app', '/var/run/docker.sock']
        host_config = self.cli.create_host_config(binds=[
            '{}:/app'.format(self.project_dir.absolute()),
            '/var/run/docker.sock:/var/run/docker.sock',
        ])
        logger.debug('Creating container "%s"', self.image)
        container = self.cli.create_container(image=self.image,
                                              command='sh',
                                              detach=True,
                                              environment=self.env,
                                              stdin_open=True,
                                              working_dir='/app',
                                              volumes=volumes,
                                              host_config=host_config)
        return container['Id']

    def _start_container(self):
        """Start the container"""
        logger.debug('Starting container "%s"', self.container_id)
        self.cli.start(self.container_id)

    def _close_container(self):
        """Close, shutdown, and remove the container"""
        logger.debug('Killing and removing container "%s"', self.container_id)
        self.cli.kill(self.container_id)
        self.cli.remove_container(self.container_id)
