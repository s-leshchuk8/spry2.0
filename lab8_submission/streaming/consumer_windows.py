"""Event-time window experiment; 2-minute watermark grace by default.

Window metric: latest terminal status (success/failure) per invoice per window.
This is a bounded replay/demo, not a distributed exactly-once state store.
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from kafka import KafkaConsumer

p = argparse.ArgumentParser()
p.add_argument('--grace', type=int, default=120, help='Seconds after window end')
p.add_argument('--group', default='lab8-window-consumer')
p.add_argument('--broker', default='localhost:9092')
p.add_argument('--topic', default='payments')
p.add_argument('--idle-exit', type=int, default=15, help='Exit after N idle seconds')
a = p.parse_args()

def seconds(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()

def emit(start, records):
    methods = defaultdict(lambda: [0, 0])
    for event in records.values():
        if event['status'] not in ('success', 'failure'):
            continue
        row = methods[event.get('paymentMethod', 'unknown')]
        row[0] += 1
        row[1] += event['status'] == 'failure'
    for method, (total, failed) in sorted(methods.items()):
        pct = failed / total * 100
        print(f'WINDOW {datetime.fromtimestamp(start,timezone.utc).isoformat()} '
              f'method={method} total={total} failed={failed} failure_pct={pct:.2f}'
              f'{" ALERT >10%" if pct > 10 else ""}', flush=True)

consumer = KafkaConsumer(a.topic, bootstrap_servers=a.broker,
    group_id=a.group, auto_offset_reset='earliest', enable_auto_commit=True,
    value_deserializer=lambda b: json.loads(b.decode('utf-8')),
    consumer_timeout_ms=a.idle_exit * 1000)
windows = defaultdict(dict)
seen = set()
max_event_time = float('-inf')
late = duplicate = accepted = 0
try:
    for msg in consumer:
        event = msg.value
        # Exact duplicate identity: all payload fields; ignore JSON key order.
        identity = json.dumps(event, sort_keys=True, ensure_ascii=False)
        if identity in seen:
            duplicate += 1
            continue
        seen.add(identity)
        event_time = seconds(event['modifiedDate'])
        # Watermark based on maximum event-time seen minus allowed lateness.
        watermark = max_event_time - a.grace
        window = int(event_time // 60) * 60
        if window + 60 <= watermark:
            late += 1
            continue
        max_event_time = max(max_event_time, event_time)
        old = windows[window].get(event['invoiceId'])
        if old is None or (event['modifiedDate'], event.get('receivedAt', '')) > (old['modifiedDate'], old.get('receivedAt', '')):
            windows[window][event['invoiceId']] = event
        accepted += 1
        watermark = max_event_time - a.grace
        for start in sorted(list(windows)):
            if start + 60 <= watermark:
                emit(start, windows.pop(start))
except KeyboardInterrupt:
    print('Interrupted; flushing open windows')
finally:
    for start in sorted(windows):
        emit(start, windows[start])
    print(f'SUMMARY accepted={accepted} duplicates={duplicate} rejected_late={late} '
          f'grace_seconds={a.grace}', flush=True)
    consumer.close()
