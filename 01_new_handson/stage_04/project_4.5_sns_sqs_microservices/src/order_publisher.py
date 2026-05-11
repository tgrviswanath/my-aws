"""
order_publisher.py — Publishes order events to SNS.
Called by the Order Service API when a new order is placed.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
sns = boto3.client("sns")


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def handler(event: dict, context) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
        order = {
            "order_id":   str(uuid.uuid4()),
            "customer":   body.get("customer", "unknown"),
            "items":      body.get("items", []),
            "total":      body.get("total", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Publish to SNS — all subscribers receive this message
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(order),
            Subject="NewOrder",
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": "ORDER_CREATED",
                }
            },
        )

        print(f"Published order {order['order_id']} to SNS")
        return response(201, {"order_id": order["order_id"], "status": "processing"})

    except Exception as e:
        print(f"Error: {e}")
        return response(500, {"error": str(e)})
