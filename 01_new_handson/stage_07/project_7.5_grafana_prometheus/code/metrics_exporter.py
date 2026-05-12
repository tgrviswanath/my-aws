"""
metrics_exporter.py — Flask app with Prometheus metrics endpoint.

Usage:
    python metrics_exporter.py
    curl http://localhost:8080/metrics
    curl http://localhost:8080/health
    curl http://localhost:8080/api/orders

Endpoints:
    GET /health       — Health check (always 200)
    GET /api/orders   — Simulated orders API (random latency + occasional errors)
    GET /metrics      — Prometheus metrics in text exposition format

Metrics exposed:
    http_requests_total{method, endpoint, status}   — Request counter
    http_request_duration_seconds{method, endpoint} — Latency histogram
    http_errors_total{method, endpoint}             — Error counter
    app_info{version}                               — Static app info gauge

Example PromQL queries (use in Grafana or Prometheus UI):
    # Request rate per endpoint (last 5 min)
    rate(http_requests_total[5m])

    # 95th percentile latency for /api/orders
    histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/api/orders"}[5m]))

    # Error rate percentage
    rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100

    # Total requests in last hour
    increase(http_requests_total[1h])

Prerequisites:
    pip install flask prometheus-client
"""

import random
import time
import threading

from flask import Flask, jsonify, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────

# Counter: total HTTP requests, labelled by method, endpoint, and HTTP status code
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

# Histogram: request duration in seconds, labelled by method and endpoint.
# Buckets cover fast API responses (5ms – 2s).
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

# Counter: total HTTP errors (4xx / 5xx responses)
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total number of HTTP errors (4xx/5xx)",
    ["method", "endpoint"],
)

# Gauge: number of orders currently being processed (simulated in-flight requests)
ORDERS_IN_FLIGHT = Gauge(
    "orders_in_flight",
    "Number of orders currently being processed",
)

# Info: static application metadata (version, environment)
APP_INFO = Info("app", "Application metadata")
APP_INFO.info({"version": "1.0.0", "environment": "production"})


# ── Instrumentation decorator ─────────────────────────────────────────────────

def track_metrics(endpoint: str):
    """
    Decorator that records request count, duration, and errors for a route.

    Args:
        endpoint: The endpoint path string used as a Prometheus label value
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            method = "GET"  # All demo routes are GET
            start = time.time()
            status = "200"
            try:
                result = func(*args, **kwargs)
                # Extract status code if the result is a tuple (response, code)
                if isinstance(result, tuple):
                    status = str(result[1])
                return result
            except Exception:
                status = "500"
                ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()
                raise
            finally:
                duration = time.time() - start
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                # Record errors for 4xx/5xx responses
                if status.startswith(("4", "5")):
                    ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()

        wrapper.__name__ = func.__name__  # Preserve Flask route name
        return wrapper
    return decorator


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
@track_metrics("/health")
def health():
    """
    Health check endpoint.
    Returns 200 with a simple JSON body. Used by load balancers and monitoring.
    """
    return jsonify({"status": "healthy", "timestamp": time.time()})


@app.route("/api/orders")
@track_metrics("/api/orders")
def get_orders():
    """
    Simulated orders API endpoint.

    Behaviour:
        - Adds random latency (10–300ms) to simulate real-world variance
        - Returns HTTP 500 ~5% of the time to simulate errors
        - Tracks in-flight order count with a Gauge
    """
    ORDERS_IN_FLIGHT.inc()
    try:
        # Simulate variable processing time (10ms – 300ms)
        latency = random.uniform(0.01, 0.3)
        time.sleep(latency)

        # Simulate ~5% error rate
        if random.random() < 0.05:
            return jsonify({"error": "Internal server error"}), 500

        # Return a fake orders payload
        orders = [
            {"id": i, "product": f"Product-{random.randint(1, 50)}", "amount": round(random.uniform(10, 500), 2)}
            for i in range(1, random.randint(2, 10))
        ]
        return jsonify({"orders": orders, "count": len(orders)})
    finally:
        ORDERS_IN_FLIGHT.dec()


@app.route("/api/orders/<int:order_id>")
@track_metrics("/api/orders/:id")
def get_order(order_id: int):
    """
    Simulated single-order lookup.
    Returns 404 for order IDs > 1000 to simulate missing resources.
    """
    if order_id > 1000:
        return jsonify({"error": f"Order {order_id} not found"}), 404

    return jsonify({
        "id": order_id,
        "product": f"Product-{order_id % 50}",
        "amount": round(order_id * 1.5, 2),
        "status": "shipped",
    })


@app.route("/metrics")
def metrics():
    """
    Prometheus metrics endpoint.
    Returns all registered metrics in the Prometheus text exposition format.
    Prometheus scrapes this endpoint at a configured interval (default: 15s).
    """
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


# ── Background traffic simulator ──────────────────────────────────────────────

def simulate_background_traffic():
    """
    Generate synthetic background traffic so the /metrics endpoint has data.
    Runs in a daemon thread — stops automatically when the main process exits.
    Sends ~2 requests/second to /api/orders.
    """
    import urllib.request

    time.sleep(2)  # Wait for Flask to start
    while True:
        try:
            urllib.request.urlopen("http://localhost:8080/api/orders", timeout=5)
        except Exception:
            pass  # Ignore errors from the simulated 500s
        time.sleep(0.5)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Prometheus Metrics Exporter ===")
    print("  Endpoints:")
    print("    http://localhost:8080/health")
    print("    http://localhost:8080/api/orders")
    print("    http://localhost:8080/metrics")
    print()
    print("  Example PromQL queries:")
    print("    rate(http_requests_total[5m])")
    print("    histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))")
    print("    rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100")
    print()

    # Start background traffic simulator in a daemon thread
    traffic_thread = threading.Thread(target=simulate_background_traffic, daemon=True)
    traffic_thread.start()

    # Run Flask (single-threaded for simplicity; use gunicorn in production)
    app.run(host="0.0.0.0", port=8080, debug=False)
