"""
consumer_lambda.py — Lambda function triggered by Kinesis Data Streams.
Processes each batch of records and writes aggregates to DynamoDB.
"""

import base64
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "handson-stream-aggregates")
dynamodb   = boto3.resource("dynamodb")
table      = dynamodb.Table(TABLE_NAME)


def handler(event: dict, context) -> dict:
    records = event.get("Records", [])
    print(f"Processing batch of {len(records)} records")

    # Aggregate by product for this batch
    product_totals = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    errors = []

    for record in records:
        try:
            # Kinesis data is base64-encoded
            payload = json.loads(base64.b64decode(record["kinesis"]["data"]))

            product = payload.get("product", "UNKNOWN")
            amount  = float(payload.get("amount", 0))

            product_totals[product]["count"]   += 1
            product_totals[product]["revenue"] += amount

            print(f"  Processed: {payload['event_type']} | "
                  f"Product: {product} | Amount: ${amount:.2f}")

        except Exception as e:
            print(f"  Error processing record: {e}")
            errors.append(record["kinesis"]["sequenceNumber"])

    # Write aggregates to DynamoDB
    hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")

    for product, totals in product_totals.items():
        table.update_item(
            Key={"pk": f"PRODUCT#{product}", "sk": f"HOUR#{hour_key}"},
            UpdateExpression="ADD order_count :c, total_revenue :r",
            ExpressionAttributeValues={
                ":c": totals["count"],
                ":r": int(totals["revenue"] * 100),   # store as cents
            },
        )

    print(f"Batch complete: {len(records)} records, {len(errors)} errors")

    # Return failed records for retry (bisect on error)
    if errors:
        return {
            "batchItemFailures": [
                {"itemIdentifier": seq} for seq in errors
            ]
        }

    return {"statusCode": 200, "processed": len(records)}
