"""\
Simple executor for yaml defined builds, plugs easily into existing CI
systems like Bamboo or Jenkins. Everything is intended to be built fully
isolated in fresh docker containers on each build.

The docker socket is mounted internally so if docker is installed in
the container, docker can be used from the host system.
"""
from setuptools import setup, find_packages

__version__ = '0.1.2'

BASE_URL = 'https://github.com/mrasband/builder_ci'


setup(name='buildr',
      description='Simple build manifest runner, mounting the build container via docker.',
      long_description=__doc__,
      version=__version__,
      author='Matt Rasband',
      author_email='matt.rasband@gmail.com',
      license='Apache-2.0',
      url=BASE_URL,
      download_url=BASE_URL + '/archive/v' + __version__ + '.tar.gz',
      keywords=['ci', 'build'],
      packages=find_packages(),
      classifiers=[
          'Programming Language :: Python :: 3.5',
          'License :: OSI Approved :: Apache Software License',
          'Intended Audience :: Developers',
          'Development Status :: 4 - Beta',
          'Topic :: Software Development',
      ],
      setup_requires=[],
      install_requires=[
          'docker-py',
          'pyyaml',
      ],
      extras_require={},
      tests_require=[],
      entry_points={
          'console_scripts': [
              'buildr = buildr.__main__:main'
          ]
      },
      zip_safe=False)
