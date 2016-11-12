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

