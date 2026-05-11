"""
handler.py — Serverless URL Shortener
"""

import json
import os
import random
import string
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
BASE_URL   = os.environ["BASE_URL"]          # e.g. https://api.example.com
TTL_DAYS   = int(os.environ.get("TTL_DAYS", "30"))

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(TABLE_NAME)

CHARS = string.ascii_letters + string.digits  # a-z A-Z 0-9


def response(status_code: int, body: dict = None, headers: dict = None) -> dict:
    resp = {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
    }
    if headers:
        resp["headers"].update(headers)
    if body is not None:
        resp["body"] = json.dumps(body, default=str)
    return resp


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(CHARS, k=length))


def handler(event: dict, context) -> dict:
    method  = event.get("requestContext", {}).get("http", {}).get("method", "")
    path    = event.get("rawPath", "")
    params  = event.get("pathParameters") or {}

    try:
        if method == "POST" and path == "/shorten":
            body = json.loads(event.get("body") or "{}")
            return shorten_url(body)

        elif method == "GET" and params.get("code"):
            code = params["code"]
            if path.startswith("/stats/"):
                return get_stats(code)
            else:
                return redirect(code)

        else:
            return response(404, {"error": "Route not found"})

    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON"})
    except Exception as e:
        print(f"Error: {e}")
        return response(500, {"error": "Internal server error"})


def shorten_url(body: dict) -> dict:
    original_url = body.get("url")
    if not original_url:
        return response(400, {"error": "Field 'url' is required"})

    if not original_url.startswith(("http://", "https://")):
        return response(400, {"error": "URL must start with http:// or https://"})

    # Generate unique code (retry on collision)
    for _ in range(5):
        code = generate_code()
        try:
            table.put_item(
                Item={
                    "code":         code,
                    "original_url": original_url,
                    "created_at":   datetime.now(timezone.utc).isoformat(),
                    "clicks":       0,
                    "ttl":          int(time.time()) + (TTL_DAYS * 86400),
                },
                ConditionExpression="attribute_not_exists(code)",  # fail if code exists
            )
            return response(201, {
                "short_url":    f"{BASE_URL}/{code}",
                "code":         code,
                "original_url": original_url,
                "expires_days": TTL_DAYS,
            })
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                continue  # code collision — try again
            raise

    return response(500, {"error": "Could not generate unique code — try again"})


def redirect(code: str) -> dict:
    result = table.get_item(Key={"code": code})
    item   = result.get("Item")

    if not item:
        return response(404, {"error": f"Short URL '{code}' not found or expired"})

    # Increment click counter atomically
    table.update_item(
        Key={"code": code},
        UpdateExpression="ADD clicks :one",
        ExpressionAttributeValues={":one": 1},
    )

    # Return 302 redirect
    return {
        "statusCode": 302,
        "headers": {
            "Location": item["original_url"],
            "Cache-Control": "no-cache",  # don't cache — we need to count every click
        },
    }


def get_stats(code: str) -> dict:
    result = table.get_item(Key={"code": code})
    item   = result.get("Item")

    if not item:
        return response(404, {"error": f"Short URL '{code}' not found"})

    return response(200, {
        "code":         item["code"],
        "short_url":    f"{BASE_URL}/{item['code']}",
        "original_url": item["original_url"],
        "clicks":       int(item.get("clicks", 0)),
        "created_at":   item["created_at"],
    })
