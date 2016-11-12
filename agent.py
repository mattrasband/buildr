#!/usr/bin/env python
import json
import tempfile
import pathlib

import pika
from git import Repo

import buildr


conn = pika.BlockingConnection(pika.ConnectionParameters(host='127.0.0.1',
                                                         port=5672))
chan = conn.channel()

print('Creating queue')
chan.queue_declare(queue='build_queue', durable=True)

def do_build(ch, method, props, body):
    print('Build task received, starting build')
    try:
        print('Payload:', body.decode())
        body = json.loads(body.decode())

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_url = body['repo']
            branch = body.get('branch', 'master')

            print('Cloning repo', repo_url + '@' + branch , 'to', tmpdir)
            repo = Repo.clone_from(url=repo_url, to_path=tmpdir,
                                   branch=branch)
            manifest = None
            project_dir = pathlib.Path(tmpdir)
            try:
                manifest = buildr.load_manifest(project_dir)
            except SystemExit:
                print('No manifest found in project.')
                raise ValueError('Manifest not found')

            buildr.run_manifest(manifest, project_dir)

        print('Cleaned')
    except buildr.BuildError as e:
        print('ERROR SETTING UP BUILD')
    except buildr.BuildFailure as e:
        print('BUILD FAILED')
    except FileNotFoundError as e:
        print('Branch does not exist')
    except Exception as e:
        print('Error during build:', e)
    finally:
        print('Build finished, acking')
        ch.basic_ack(delivery_tag=method.delivery_tag)


chan.basic_qos(prefetch_count=0)
chan.basic_consume(do_build, queue='build_queue')
print('Listening for work')
try:
    chan.start_consuming()
except KeyboardInterrupt:
    print('Shutting down...')
finally:
    conn.close()

