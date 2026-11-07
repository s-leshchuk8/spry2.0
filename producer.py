import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

statuses = ['success', 'failure', 'pending']
methods = ['card', 'paypal', 'apple_pay', 'google_pay']
devices = ['iOS', 'Android', 'Web']

print("Streaming data to Redpanda... Press Ctrl+C to stop.")

try:
    while True:
        event = {
            "invoiceId": f"inv_{random.randint(1000, 9999)}",
            "status": random.choice(statuses),
            "amount": random.randint(100, 10000),
            "ccy": "USD",
            "paymentMethod": random.choice(methods),
            "device": random.choice(devices),
            "createdDate": datetime.utcnow().isoformat(),
            "modifiedDate": datetime.utcnow().isoformat(),
            "receivedAt": datetime.utcnow().isoformat()
        }
        producer.send('payments', value=event)
        print(f"Sent: {event['invoiceId']} | Status: {event['status']}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Producer stopped.")
