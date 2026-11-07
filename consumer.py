import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'payments',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='payments-analytics-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("Consumer started. Listening for events...")

total_count = 0
success_count = 0

try:
    for message in consumer:
        event = message.value
        total_count += 1
        if event.get('status') == 'success':
            success_count += 1
        
        print(f"Partition {message.partition} | Total: {total_count} | Success: {success_count} | Event: {event['invoiceId']}")
except KeyboardInterrupt:
    print("Consumer stopped.")
