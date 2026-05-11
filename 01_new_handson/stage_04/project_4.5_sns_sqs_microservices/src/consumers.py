"""
consumers.py — SQS consumer Lambda functions.
Each function processes messages from its own SQS queue.
"""

import json


def parse_order(record: dict) -> dict:
    """Extract order from SQS record (which wraps SNS message)."""
    sqs_body = json.loads(record["body"])
    # SNS wraps the message in a JSON envelope
    if "Message" in sqs_body:
        return json.loads(sqs_body["Message"])
    return sqs_body


# ─── Inventory Consumer ───────────────────────────────────────────────────────

def inventory_handler(event: dict, context) -> None:
    """Update inventory when an order is placed."""
    for record in event.get("Records", []):
        try:
            order = parse_order(record)
            print(f"[INVENTORY] Processing order {order['order_id']}")

            for item in order.get("items", []):
                print(f"  Reducing stock: {item.get('product_id')} by {item.get('quantity', 1)}")
                # In production: update DynamoDB inventory table

            print(f"[INVENTORY] Done: order {order['order_id']}")

        except Exception as e:
            print(f"[INVENTORY] Error: {e}")
            raise  # Re-raise to trigger SQS retry / DLQ


# ─── Email Consumer ───────────────────────────────────────────────────────────

def email_handler(event: dict, context) -> None:
    """Send order confirmation email."""
    for record in event.get("Records", []):
        try:
            order = parse_order(record)
            print(f"[EMAIL] Sending confirmation for order {order['order_id']}")
            print(f"  To: {order.get('customer')}")
            print(f"  Total: ${order.get('total', 0):.2f}")
            # In production: use SES to send email

        except Exception as e:
            print(f"[EMAIL] Error: {e}")
            raise


# ─── Analytics Consumer ───────────────────────────────────────────────────────

def analytics_handler(event: dict, context) -> None:
    """Record order metrics for analytics."""
    for record in event.get("Records", []):
        try:
            order = parse_order(record)
            print(f"[ANALYTICS] Recording metrics for order {order['order_id']}")
            print(f"  Revenue: ${order.get('total', 0):.2f}")
            print(f"  Items: {len(order.get('items', []))}")
            # In production: write to Kinesis or DynamoDB analytics table

        except Exception as e:
            print(f"[ANALYTICS] Error: {e}")
            raise
