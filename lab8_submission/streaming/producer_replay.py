"""Replay a local JSONL day ordered by receivedAt, keyed by invoiceId."""
import argparse
import json
import random
import time
from kafka import KafkaProducer

p = argparse.ArgumentParser()
p.add_argument('jsonl', help='Downloaded single-day events.jsonl')
p.add_argument('--rate', type=float, default=20)
p.add_argument('--failure-probability', type=float, default=None)
p.add_argument('--broker', default='localhost:9092')
p.add_argument('--topic', default='payments')
a = p.parse_args()
with open(a.jsonl, encoding='utf-8') as f:
    events = [json.loads(line) for line in f if line.strip()]
events.sort(key=lambda e: e['receivedAt'])
producer = KafkaProducer(bootstrap_servers=a.broker,
    key_serializer=lambda x: x.encode(),
    value_serializer=lambda x: json.dumps(x).encode())
try:
    for index, event in enumerate(events, 1):
        if a.failure_probability is not None and event.get('status') in ('success', 'failure'):
            event = dict(event)
            event['status'] = 'failure' if random.random() < a.failure_probability else 'success'
            event['finalAmount'] = 0 if event['status'] == 'failure' else event.get('amount', 0)
            event['failureReason'] = 'Simulated failure' if event['status'] == 'failure' else None
        producer.send(a.topic, key=event['invoiceId'], value=event)
        if index % 100 == 0:
            print(f'Sent {index}/{len(events)}')
        time.sleep(1 / a.rate)
finally:
    producer.flush()
    producer.close()
