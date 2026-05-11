"""
app_with_tracing.py — Flask API with AWS X-Ray distributed tracing.
"""

import os
import socket
import boto3
from flask import Flask, jsonify, request

# ─── X-Ray Setup ──────────────────────────────────────────────────────────────
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# Patch all supported libraries (boto3, requests, etc.)
patch_all()

app = Flask(__name__)

# Configure X-Ray
xray_recorder.configure(
    service="flask-api",
    sampling=True,
    context_missing="LOG_ERROR",   # don't crash if no trace context
)

# Add X-Ray middleware to Flask
XRayMiddleware(app, xray_recorder)

TABLE_NAME = os.environ.get("TABLE_NAME", "handson-api-items")
dynamodb   = boto3.resource("dynamodb")
table      = dynamodb.Table(TABLE_NAME)


@app.route("/health")
def health():
    # Add custom annotation to trace
    xray_recorder.current_segment().put_annotation("endpoint", "health")
    return jsonify({
        "status":   "healthy",
        "hostname": socket.gethostname(),
    })


@app.route("/items")
def list_items():
    segment = xray_recorder.current_segment()
    segment.put_annotation("endpoint", "list_items")

    # This DynamoDB call is automatically traced as a subsegment
    result = table.scan()
    items  = result.get("Items", [])

    # Add metadata (not indexed, for debugging)
    segment.put_metadata("item_count", len(items))

    return jsonify({"items": items, "count": len(items)})


@app.route("/items/<item_id>")
def get_item(item_id):
    segment = xray_recorder.current_segment()
    segment.put_annotation("endpoint", "get_item")
    segment.put_annotation("item_id", item_id)

    result = table.get_item(Key={"id": item_id})
    item   = result.get("Item")

    if not item:
        # Mark segment as having an error
        segment.put_annotation("error", "item_not_found")
        return jsonify({"error": f"Item {item_id} not found"}), 404

    return jsonify(item)


@app.route("/items", methods=["POST"])
def create_item():
    import uuid
    from datetime import datetime, timezone

    body = request.get_json() or {}

    # Custom subsegment for business logic
    with xray_recorder.in_subsegment("validate_input") as subsegment:
        if not body.get("name"):
            subsegment.put_annotation("validation_error", "missing_name")
            return jsonify({"error": "name is required"}), 400

    item = {
        "id":          str(uuid.uuid4()),
        "name":        body["name"],
        "description": body.get("description", ""),
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }

    # DynamoDB write — automatically traced
    table.put_item(Item=item)

    xray_recorder.current_segment().put_annotation("created_item_id", item["id"])
    return jsonify(item), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
