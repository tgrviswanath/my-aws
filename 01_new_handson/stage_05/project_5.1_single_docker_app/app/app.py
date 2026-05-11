"""
app.py — Simple Flask REST API for Docker learning.
"""

import os
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_ENV     = os.environ.get("APP_ENV", "development")

# In-memory store (for demo only — use a real DB in production)
items: dict = {}


@app.route("/health")
def health():
    """Health check endpoint — used by Docker and load balancers."""
    return jsonify({
        "status":    "healthy",
        "version":   APP_VERSION,
        "env":       APP_ENV,
        "hostname":  socket.gethostname(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/info")
def info():
    """Container info — useful for debugging."""
    return jsonify({
        "hostname":   socket.gethostname(),
        "version":    APP_VERSION,
        "env":        APP_ENV,
        "python_pid": os.getpid(),
    })


@app.route("/items", methods=["GET"])
def list_items():
    return jsonify({"items": list(items.values()), "count": len(items)})


@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    item = items.get(item_id)
    if not item:
        return jsonify({"error": f"Item {item_id} not found"}), 404
    return jsonify(item)


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Field 'name' is required"}), 400

    import uuid
    item_id = str(uuid.uuid4())[:8]
    item = {"id": item_id, "name": data["name"], "description": data.get("description", "")}
    items[item_id] = item
    return jsonify(item), 201


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(APP_ENV == "development"))
