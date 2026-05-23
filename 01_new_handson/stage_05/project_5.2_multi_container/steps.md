# Steps — Project 5.2 Multi-container Application

## Phase 1 — Setup

```bash
# Copy env file
cp .env.example .env
# Edit .env with your passwords

# Build and start all services
docker compose up -d --build

# Watch startup logs
docker compose logs -f
```

---

## Phase 2 — Verify All Services

```bash
# Check all containers are healthy
docker compose ps

# Expected output:
# NAME           STATUS                    PORTS
# app-db         Up (healthy)              3306/tcp
# app-redis      Up (healthy)              6379/tcp
# app-backend    Up (healthy)              0.0.0.0:4000->4000/tcp
# app-frontend   Up                        0.0.0.0:3000->3000/tcp
```

---

## Phase 3 — Test Backend API

```bash
# Health check
curl http://localhost:4000/health | python3 -m json.tool

# List items (first call — from database)
curl http://localhost:4000/items | python3 -m json.tool
# Notice: "source": "database"

# List items again (second call — from Redis cache)
curl http://localhost:4000/items | python3 -m json.tool
# Notice: "source": "cache"

# Create item (invalidates cache)
curl -s -X POST http://localhost:4000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "New Widget", "description": "Created via API"}' \
  | python3 -m json.tool
```

---

## Phase 4 — Verify Redis Caching

```bash
# Connect to Redis directly
docker exec -it app-redis redis-cli -a redispassword

# Inside Redis CLI:
KEYS *           # list all keys
GET items:all    # see cached items JSON
TTL items:all    # see remaining TTL (should be < 60)
exit
```

---

## Phase 5 — Verify MySQL Data

```bash
# Connect to MySQL
docker exec -it app-db mysql -u appuser -papppassword appdb

# Inside MySQL:
SHOW TABLES;
SELECT * FROM items;
exit
```

---

## Phase 6 — Container Networking

```bash
# Verify containers can reach each other by service name
docker exec app-backend ping -c 3 db
docker exec app-backend ping -c 3 redis

# Frontend CANNOT reach db directly (different network segment)
# This is correct — only backend should talk to the database
```

---

## Phase 7 — Data Persistence Test

```bash
# Create an item
curl -s -X POST http://localhost:4000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Persistent Item"}'

# Stop and restart containers (NOT down -v)
docker compose stop
docker compose start

# Data should still be there
curl http://localhost:4000/items | python3 -m json.tool
```

---

## Phase 8 — Cleanup

```bash
# Stop containers (keep volumes)
docker compose down

# Stop AND delete volumes (deletes all data)
docker compose down -v
```

---

## Phase 9 — Verification & Validation

### 9.1 AWS Console Verification
Not applicable for local Docker Compose. All verification is done locally.

### 9.2 CLI Verification Commands
```bash
# Confirm all 4 services are running and healthy
docker compose ps
# Expected: all services show "Up (healthy)" or "Up"

# Confirm inter-service DNS resolution
docker compose exec backend ping -c 2 db
docker compose exec backend ping -c 2 redis
# Expected: both succeed (Docker Compose internal DNS)

# Confirm backend cannot reach db directly from frontend network
docker compose exec frontend ping -c 2 db 2>&1 || echo "BLOCKED as expected"
```

### 9.3 Functional Tests
```bash
# Test 1: Backend health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/health)
echo "Backend health: $HTTP_STATUS"
# Expected: 200

# Test 2: First request hits database (cache miss)
RESPONSE=$(curl -s http://localhost:4000/items)
echo $RESPONSE | python3 -c "import sys,json; d=json.load(sys.stdin); print('Source:', d.get('source','unknown'))"
# Expected: Source: database

# Test 3: Second request hits Redis cache (cache hit)
RESPONSE=$(curl -s http://localhost:4000/items)
echo $RESPONSE | python3 -c "import sys,json; d=json.load(sys.stdin); print('Source:', d.get('source','unknown'))"
# Expected: Source: cache

# Test 4: Create item invalidates cache
curl -s -X POST http://localhost:4000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Verification Item"}' | python3 -m json.tool
# Next GET should show source: database again

# Test 5: Verify Redis key exists with TTL
docker compose exec redis redis-cli -a redispassword TTL items:all
# Expected: positive number (< 60)

# Test 6: Verify MySQL has data
docker compose exec db mysql -u appuser -papppassword appdb \
  -e "SELECT COUNT(*) as item_count FROM items;"
# Expected: count > 0

# Test 7: Data persistence after restart
docker compose stop && docker compose start
sleep 5
curl -s http://localhost:4000/items | python3 -c \
  "import sys,json; items=json.load(sys.stdin).get('items',[]); print(f'Items after restart: {len(items)}')"
# Expected: same count as before restart
```

### 9.4 Logs & Monitoring Checks
```bash
# Check for errors across all services
docker compose logs --tail=20 2>&1 | grep -i "error\|exception\|fatal"
# Expected: no output

# Check backend connected to DB and Redis
docker compose logs backend | grep -i "connected\|ready\|started"
# Expected: connection success messages

# Check MySQL is ready
docker compose logs db | grep "ready for connections"
# Expected: "ready for connections" appears
```

### 9.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| `docker compose ps` | All services Up/healthy |
| First `GET /items` | `"source": "database"` |
| Second `GET /items` | `"source": "cache"` |
| Redis `TTL items:all` | Positive integer |
| MySQL item count | > 0 |
| Data after restart | Same count as before |

### 9.6 Verification Checklist
- [ ] All 4 services running (`docker compose ps`)
- [ ] Backend health check returns 200
- [ ] First items request: `source: database`
- [ ] Second items request: `source: cache`
- [ ] Redis key `items:all` exists with TTL
- [ ] MySQL contains seeded data
- [ ] Backend can ping `db` and `redis` by service name
- [ ] Frontend cannot reach `db` directly (network isolation)
- [ ] Data persists after `docker compose stop && start`

---

## Screenshots to Take
- [ ] `docker compose ps` showing all 4 services healthy
- [ ] First API call showing `"source": "database"`
- [ ] Second API call showing `"source": "cache"`
- [ ] Redis CLI showing cached key with TTL
- [ ] MySQL showing seeded data
- [ ] Data persisting after container restart
