#!/usr/bin/env python
import functools
import enum
import json
import logging
import tempfile
import pathlib
import sys

import pika
from git import Repo
from git.exc import GitCommandError

import buildr

logging.basicConfig()
logger = logging.getLogger('buildr')
logger.setLevel(logging.DEBUG)


class Result(enum.Enum):
    PASS = 'Pass'
    FAIL = 'Fail'
    ERROR = 'Error'
    PENDING = 'Pending'


def do_build(ch, method, props, body):
    result = Result.PENDING
    response_queue = sys.stdout.write

    if props.reply_to:
        logger.debug('Received a reply_to queue, publishing output'
                     ' to rabbit')
        # If a response queue is given, write all messages to
        # it so the orchestrater can give a live feed.
        reply_props = pika.BasicProperties(correlation_id=props.correlation_id,
                                           content_type='appliction/json')

        def response_writer(output):
            """Dump blindly to the response queue,
            we should probably buffer up to some length..."""
            body = json.dumps({
                'message': output,
                'result': result.value,
            })
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=props,
                             body=body)

        response_queue = response_writer

    response_queue('Starting new build')
    logger.debug('New build started')
    try:
        body = body.decode()
        logger.debug('Payload: %s', body)
        body = json.loads(body)

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_url = body.get('repo')
            if not repo_url:
                raise buildr.BuildError('Repository url not provided.')
            branch = body.get('branch', 'master')

            response_queue('Cloning repository "{}@{}"'.format(repo_url,
                                                               branch))

            logger.debug('Cloning repo %s@%s to %s', repo_url, branch, tmpdir)
            repo = Repo.clone_from(url=repo_url, to_path=tmpdir,
                                branch=branch)
            manifest = None
            project_dir = pathlib.Path(tmpdir)
            try:
                logger.debug('Loading manifest from project dir %s', tmpdir)
                manifest = buildr.load_manifest(project_dir)
            except SystemExit as e:
                logger.error('No manifest found in the project: %s', e)
                raise ValueError('Manifest not found')

            logger.debug('Running manifest')
            buildr.run_manifest(manifest, project_dir, progress_writer=response_queue)

        result = Result.PASS
    except buildr.BuildError as e:
        logger.error('Build prep error: %s', e)
        result = Result.ERROR
        response_queue('Build prep error.')
    except buildr.BuildFailure as e:
        logger.error('Build execution failure: %s', e)
        result = Result.FAIL
        response_queue('Build execution failed')
    except FileNotFoundError as e:
        logger.error('Branch does not exist')
        result = Result.ERROR
        response_queue('Build prep failed, branch doesn\'t exist')
    except GitCommandError as e:
        logger.error('Repository does not exist')
        result = Result.ERROR
        response_queue('Build prep failed, repository inaccessible')
    except Exception as e:
        logger.error('Unknown error during build: %r', e)
        result = Result.ERROR
        response_queue('Unknown error {!r}'.format(e))
    finally:
        logger.debug('Build finished, result: "%s"', result)
        response_queue('Build Finished')
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main(host='127.0.0.1', port=5672, queue_name='build_queue'):
    logger.debug('Connecting to rabbit')
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=host,
                                                             port=port))
    chan = conn.channel()

    logger.debug('Creating queue, if it does not already exist')
    chan.queue_declare(queue=queue_name, durable=True)

    # Disable prefetch, all tasks will be long-running...
    chan.basic_qos(prefetch_count=0)
    chan.basic_consume(do_build, queue=queue_name)

    logger.info('Listening for work on queue "%s"', queue_name)
    try:
        chan.start_consuming()
    except KeyboardInterrupt:
        logger.info('Shutting down...')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
