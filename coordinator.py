#!/usr/bin/env python
import contextlib
import json

import pika


conn = pika.BlockingConnection(pika.ConnectionParameters())
chan = conn.channel()

response_q = chan.queue_declare(exclusive=True, auto_delete=True)

def consume(ch, method, props, body):
    print('Body:', body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


chan.basic_consume(consume, response_q.method.queue)

chan.basic_publish('',
                   'build_queue',
                   body=json.dumps({'repo': 'git@github.com:mrasband/builder_ci.git'}),
                   properties=pika.BasicProperties(reply_to=response_q.method.queue))

with contextlib.suppress(KeyboardInterrupt):
    chan.start_consuming()
conn.close()
