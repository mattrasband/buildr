# Builder CI

**Experimental**

This is just an experiment to see what it would take to build a simple CI system built around containers being used to guarantee clean builds.

## Requirements

You can pretty much just use the Vagrantfile provided, but you'll need to copy your docker login and ssh keys if they're needed (they aren't for anything public :)

* docker
* rabbitmq (`docker run --rm -it -p 5672:5672 -p 15672:15672 rabbitmq:management`)
* ssh keys (for any repos you want to be able to clone), just put in `~/.ssh`
* docker login (`~/.docker/config.json`) - auth for any private docker repos

## Agent

An agent is effectively a build agent, you should be okay to run 1 agent per core on your box.

    python agent.py

If the repositories you are accessing require auth, you should have the SSH keys in the standard spots.

## Coordinator

TODO

Temporary: You can log into the rabbit ui and just dump a json message on the build_queue with "repo" and "branch" keys (the branch is optional).

There is no feedback yet other than watching the agent terminal output...

## Manifest File

This is pretty much a rip off of the things I like about Travis-CI and Gitlab's Runner, it's simply a yaml file that defines stages and the base image the build is run from.

Sample manifest (which is actually just a `.buildr.yml` in your project directory):

    # If you are unsure, just use `docker:1.12`
    # Note, that is an alpine image.
    image: 'which-docker-image'
    
    # Environment defines environmental variables passed
    # to the build container (image from above).
    # 2.x may allow an encrypted field so your config can
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
        - sh -c "dpl heroku --api-key - $API_KEY"


# TODO

Beyond the tons that is obvious...

* Orchestrator node(s)
* Backchannel with updates
* Allow using other containers for other stages, though this is technically already possible since the docker.sock is available in the container running the manifest, so you could do arbitrary docker commands in there. 
  * This is especially powerful if you have deploy keys in a deploy container and only the agents can pull it.
