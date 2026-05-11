"""
handler.py — Serverless REST API Lambda handler
Handles CRUD operations for items stored in DynamoDB.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# DynamoDB table name from environment variable
TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def response(status_code: int, body: dict) -> dict:
    """Build a standard API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def handler(event: dict, context) -> dict:
    """Main Lambda handler — routes to the correct function."""
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path   = event.get("rawPath", "")
    params = event.get("pathParameters") or {}
    item_id = params.get("id")

    try:
        if method == "GET" and not item_id:
            return list_items()
        elif method == "GET" and item_id:
            return get_item(item_id)
        elif method == "POST":
            body = json.loads(event.get("body") or "{}")
            return create_item(body)
        elif method == "PUT" and item_id:
            body = json.loads(event.get("body") or "{}")
            return update_item(item_id, body)
        elif method == "DELETE" and item_id:
            return delete_item(item_id)
        else:
            return response(404, {"error": "Route not found"})

    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return response(500, {"error": "Database error"})
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return response(500, {"error": "Internal server error"})


def list_items() -> dict:
    result = table.scan()
    return response(200, {
        "items": result.get("Items", []),
        "count": result.get("Count", 0),
    })


def get_item(item_id: str) -> dict:
    result = table.get_item(Key={"id": item_id})
    item = result.get("Item")
    if not item:
        return response(404, {"error": f"Item {item_id} not found"})
    return response(200, item)


def create_item(body: dict) -> dict:
    if not body.get("name"):
        return response(400, {"error": "Field 'name' is required"})

    item = {
        "id":         str(uuid.uuid4()),
        "name":       body["name"],
        "description": body.get("description", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    table.put_item(Item=item)
    return response(201, item)


def update_item(item_id: str, body: dict) -> dict:
    # Check item exists
    existing = table.get_item(Key={"id": item_id}).get("Item")
    if not existing:
        return response(404, {"error": f"Item {item_id} not found"})

    # Build update expression dynamically
    updates = {k: v for k, v in body.items() if k not in ("id", "created_at")}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    names  = {f"#{k}": k for k in updates}
    values = {f":{k}": v for k, v in updates.items()}

    result = table.update_item(
        Key={"id": item_id},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return response(200, result["Attributes"])


def delete_item(item_id: str) -> dict:
    existing = table.get_item(Key={"id": item_id}).get("Item")
    if not existing:
        return response(404, {"error": f"Item {item_id} not found"})

    table.delete_item(Key={"id": item_id})
    return response(200, {"message": f"Item {item_id} deleted"})
