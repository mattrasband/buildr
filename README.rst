The stuff we may actually use
-----------------------------

I am finding a lot of deficiencies with my work's current systems (as a developer), so the `buildr.py` script is meant to be the "job" and it will actually create its own stages. This makes it so we can literally clone the same job for all projects. You can also run the script locally to test builds before pushing them.

Problems with the common "enterprise" build systems (Bamboo and Jenkins) [or problems with how we set ours up...!]:

- Poor/Non Existent API for programmatically creating plans (and the jobs/stages), setting artifacts, and cloning deploy plans.
- Isolating/Clean Agents - AFAIK you pretty much make agents with capabilities and register those to builds. We end up with a lot of crap cluttering the system effecting other builds (this may be an issue with how we set them up)
- Builds are not versioned with the code, if I need to change my build I somehow have to time the build updates with the next version of the code.
- No good way to run locally while you figure out how you want the full build run to work

buildr
======

This simply parses the manifest (`.buildr.yml`) from your project, mounts the project in the target docker container and runs the build. The docker sock is mounted in the container too, so your build can install things like docker-compose and use them for builds/tests.

It then runs each stage and its scripts in the fresh container.

Manifest File (`.buildr.yml`)
=============================

This is pretty much a rip off of the things I like about Travis-CI and Gitlab's Runner, it's simply a yaml file that defines stages and the base image the build is run from.

Sample manifest (which is actually just a `.buildr.yml` in your project directory):

.. code:: yaml

    image: 'dockerimage:tag'

    # Environment defines environmental variables passed
    # to the build container (image from above).
    # 2.x may allow an encrypted field so your build config can
    # be versioned with your build plan.
    environment:
      # Optionally, you can inherit from the agent system.
      inherit: false
      # Just a list of NAME=VALUE
      vars:
        - FOO=BAR
        - API_KEY=<something>

    # Stages is just a list of the top level keys that define the standard build
    # directive, that will be demonstrated below.
    stages:
      - build
      - deploy

    # The prepare is a default stage, if present you can use it for project
    # specific config that your base image doesn't provide. It always runs
    # first if present.
    prepare:
      script:
        - apk add -U git

    # The standard stage definition has a list of scripts to be run.
    # Later I will add some tags and the like for limiting when a
    # stage will run (or not)
    build:
      script:
        - ./mvnw package

    # Another arbitrary stage, note the syntax for the command
    # that needs an envvar - since this is going through a number
    # of shells to the build container, it needs to be called this way.
    # If your application or build script needs envvars, it can access
    # them the "normal" way (e.g. `os.getenv('my_var')`)
    deploy:
      script:
        - docker push ...


The below is just for fun, don't actually use it ;)
---------------------------------------------------

**Experimental**

This is just an experiment to see what it would take to build a simple CI system around the `buildr.py`

Requirements
============

You can pretty much just use the Vagrantfile provided, but you'll need to copy your docker login and ssh keys if they're needed (they aren't for anything public :)

- docker
- rabbitmq (`docker run --rm -it -p 5672:5672 -p 15672:15672 rabbitmq:management`)
- ssh keys (for any repos you want to be able to clone), just put in `~/.ssh`
- docker login (`~/.docker/config.json`) - auth for any private docker repos

Agent
=====

An agent is effectively a build agent, you should be okay to run 1 agent per core on your box. It listens to a rabbit queue, clones the repo, and fires off a buildr run.

.. code:: bash

    python agent.py

If the repositories you are accessing require auth, you should have the SSH keys in the standard spots.

Agents will not run by default on OSX docker - primarily because of the volume mount restrictions (Python's tempdir makes temp directories in a spot that docker isn't happy mounting by default). You should be able to edit the allowed volumes, but it wasn't working for me so I just use Vagrant.

Coordinator
===========

TODO

Temporary: You can log into the rabbit ui and just dump a json message on the build_queue with "repo" and "branch" keys (the branch is optional).

There is no feedback yet other than watching the agent terminal output...

# TODO

Beyond the tons that is obvious...

- Orchestrator node(s)
- Backchannel with updates
- Allow using other containers for other stages, though this is technically already possible since the docker.sock is available in the container running the manifest, so you could do arbitrary docker commands in there.
  * This is especially powerful if you have deploy keys in a deploy container and only the agents can pull it.
- Protobuf probably...
