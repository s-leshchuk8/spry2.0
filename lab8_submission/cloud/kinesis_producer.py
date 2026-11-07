"""Send local JSONL events to an EXISTING Kinesis Data Stream in us-east-1."""
import argparse
import json
import time
import boto3
p = argparse.ArgumentParser()
p.add_argument('jsonl')
p.add_argument('--stream', required=True)
p.add_argument('--region', default='us-east-1')
p.add_argument('--rate', type=float, default=20)
a = p.parse_args()
client = boto3.client('kinesis', region_name=a.region)
count = 0
with open(a.jsonl, encoding='utf-8') as source:
    for line in source:
        if not line.strip():
            continue
        event = json.loads(line)
        payload = (json.dumps(event) + '\n').encode()
        client.put_record(StreamName=a.stream, Data=payload,
                          PartitionKey=str(event['invoiceId']))
        count += 1
        if count % 100 == 0:
            print(f'Uploaded {count} events')
        time.sleep(1 / a.rate)
print(f'Finished: {count} records')
