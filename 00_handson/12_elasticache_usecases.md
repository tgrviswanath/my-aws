# ElastiCache (Redis) — Real-World Use Cases

## Use Case 1: API Response Caching

**Business Problem**: Product catalog API hits the database on every request. 80% of requests are for the same 100 products. Database is overwhelmed.

```python
import boto3
import redis
import json
import hashlib
import time
from functools import wraps

# Connect to ElastiCache Redis
r = redis.Redis(
    host=os.environ['REDIS_HOST'],  # cluster endpoint
    port=6379,
    ssl=True,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)

def cache(ttl: int = 300, key_prefix: str = ''):
    """Decorator to cache function results in Redis."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            key_data = f"{key_prefix}{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try cache first
            try:
                cached = r.get(cache_key)
                if cached:
                    return json.loads(cached)
            except redis.RedisError as e:
                print(f"Cache read error: {e}")  # Fail open — don't break the app

            # Cache miss — call function
            result = func(*args, **kwargs)

            # Store in cache
            try:
                r.setex(cache_key, ttl, json.dumps(result, default=str))
            except redis.RedisError as e:
                print(f"Cache write error: {e}")

            return result
        return wrapper
    return decorator

# Usage
@cache(ttl=300, key_prefix='product:')
def get_product(product_id: str) -> dict:
    """Expensive DB query — cached for 5 minutes."""
    return db.execute("SELECT * FROM products WHERE id = %s", product_id).fetchone()

@cache(ttl=60, key_prefix='search:')
def search_products(query: str, page: int = 1) -> list:
    """Search results cached for 1 minute."""
    return db.execute("SELECT * FROM products WHERE name ILIKE %s LIMIT 20 OFFSET %s",
                      f"%{query}%", (page-1)*20).fetchall()

# Cache invalidation on update
def update_product(product_id: str, data: dict):
    db.execute("UPDATE products SET ... WHERE id = %s", product_id)
    # Invalidate all cache keys for this product
    pattern = f"product:*{product_id}*"
    keys = r.keys(pattern)
    if keys:
        r.delete(*keys)
    print(f"Invalidated {len(keys)} cache keys for product {product_id}")
```

**What you learn**: Cache-aside pattern, TTL strategy, fail-open on cache errors, cache invalidation.

---

## Use Case 2: Session Store (Distributed Sessions)

**Business Problem**: Web app runs on 10 EC2 instances. User logs in on instance 1, next request goes to instance 2 — session lost. Need shared session store.

```python
from flask import Flask, session, request
from flask_session import Session
import redis

app = Flask(__name__)

# Configure Redis as session backend
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(
    host=os.environ['REDIS_HOST'],
    port=6379,
    ssl=True
)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
Session(app)

@app.route('/login', methods=['POST'])
def login():
    user = authenticate(request.json['email'], request.json['password'])
    if not user:
        return {'error': 'Invalid credentials'}, 401

    session['user_id'] = user['id']
    session['email'] = user['email']
    session['role'] = user['role']
    session.permanent = True  # 30-day session
    return {'message': 'Logged in'}

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}, 401
    return {'userId': session['user_id'], 'email': session['email']}

@app.route('/logout')
def logout():
    session.clear()  # Deletes from Redis immediately
    return {'message': 'Logged out'}
```

```bash
# Create ElastiCache Redis for sessions
aws elasticache create-replication-group \
  --replication-group-id "sessions-cache" \
  --description "Session store" \
  --engine redis \
  --engine-version "7.1" \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name "prod-cache-subnet" \
  --security-group-ids $SG_CACHE \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --snapshot-retention-limit 1
```

**What you learn**: Distributed sessions, Redis as session backend, session security settings.

---

## Use Case 3: Rate Limiter

**Business Problem**: API is being abused — one IP is making 10,000 requests/minute. Need to rate limit to 100 req/min per IP.

```python
import redis
import time
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
r = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, ssl=True, decode_responses=True)

class RateLimiter:
    def __init__(self, limit: int = 100, window: int = 60):
        self.limit = limit
        self.window = window

    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """Sliding window rate limiter using Redis sorted sets."""
        now = time.time()
        window_start = now - self.window
        key = f"rate_limit:{identifier}"

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
        pipe.zcard(key)                               # Count current requests
        pipe.zadd(key, {str(now): now})               # Add current request
        pipe.expire(key, self.window)
        results = pipe.execute()

        current_count = results[1]
        allowed = current_count < self.limit
        remaining = max(0, self.limit - current_count - 1)
        reset_at = int(now + self.window)

        return allowed, {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_at),
            'Retry-After': str(self.window) if not allowed else None
        }

limiter = RateLimiter(limit=100, window=60)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Use IP + user ID for rate limiting
    client_ip = request.client.host
    user_id = request.headers.get('X-User-ID', 'anonymous')
    identifier = f"{client_ip}:{user_id}"

    allowed, headers = limiter.is_allowed(identifier)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={k: v for k, v in headers.items() if v}
        )

    response = await call_next(request)
    for key, value in headers.items():
        if value:
            response.headers[key] = value
    return response
```

**What you learn**: Sliding window rate limiter, Redis sorted sets, pipeline for atomic operations.

---

## Use Case 4: Pub/Sub for Real-Time Notifications

**Business Problem**: When an order ships, notify all browser tabs the user has open in real-time.

```python
# Publisher (order service)
import redis
import json

r_pub = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, ssl=True)

def notify_order_shipped(user_id: str, order_id: str, tracking: str):
    """Publish shipping notification to all user's connected clients."""
    message = json.dumps({
        'type': 'ORDER_SHIPPED',
        'orderId': order_id,
        'trackingNumber': tracking,
        'timestamp': time.time()
    })
    # Publish to user-specific channel
    subscribers = r_pub.publish(f"user:{user_id}:notifications", message)
    print(f"Notified {subscribers} connected clients for user {user_id}")

# Subscriber (WebSocket server)
import asyncio
import redis.asyncio as aioredis
from fastapi import WebSocket

async def subscribe_to_notifications(user_id: str, websocket: WebSocket):
    """Subscribe to user's notification channel and forward to WebSocket."""
    r_sub = aioredis.Redis(host=os.environ['REDIS_HOST'], port=6379, ssl=True)
    pubsub = r_sub.pubsub()
    await pubsub.subscribe(f"user:{user_id}:notifications")

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send_text(message['data'].decode())
    except Exception:
        await pubsub.unsubscribe()
        await r_sub.aclose()
```

**What you learn**: Redis Pub/Sub, real-time notifications, WebSocket + Redis integration.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No TTL on cached data | Memory fills up, evictions | Always set TTL appropriate to data freshness |
| Caching mutable data without invalidation | Stale data served | Invalidate on write |
| Not handling Redis connection errors | App crashes when Redis is down | Wrap in try/except, fail open |
| Using Redis for large objects (> 1MB) | Memory waste, slow | Store large data in S3, cache reference |
| Single Redis node in production | No HA | Use replication group with Multi-AZ |
| Storing sensitive data unencrypted | Data exposure | Enable `--transit-encryption-enabled` and `--at-rest-encryption-enabled` |
