"""
producer.py — Kinesis Data Streams producer.
Sends simulated order events to the stream.
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone

import boto3

STREAM_NAME = "handson-events"
kinesis = boto3.client("kinesis", region_name="us-east-1")

PRODUCTS   = ["Widget A", "Widget B", "Widget C", "Gadget X", "Gadget Y"]
CUSTOMERS  = [f"CUST-{i:03d}" for i in range(1, 21)]


def generate_event() -> dict:
    return {
        "event_id":    str(uuid.uuid4()),
        "event_type":  "ORDER_PLACED",
        "order_id":    f"ORD-{random.randint(10000, 99999)}",
        "customer_id": random.choice(CUSTOMERS),
        "product":     random.choice(PRODUCTS),
        "quantity":    random.randint(1, 5),
        "amount":      round(random.uniform(9.99, 99.99), 2),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }


def send_events(count: int = 10, delay: float = 0.1) -> None:
    print(f"Sending {count} events to stream: {STREAM_NAME}")
    sent = 0

    for i in range(count):
        event = generate_event()

        response = kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(event),
            PartitionKey=event["customer_id"],   # route by customer for ordering
        )

        print(f"  [{i+1}/{count}] Sent {event['event_type']} | "
              f"Shard: {response['ShardId']} | "
              f"Seq: {response['SequenceNumber'][:20]}...")
        sent += 1
        time.sleep(delay)

    print(f"\nDone. Sent {sent} events.")


if __name__ == "__main__":
    send_events(count=50, delay=0.05)
