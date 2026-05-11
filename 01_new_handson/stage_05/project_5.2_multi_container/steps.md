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

## Screenshots to Take
- [ ] `docker compose ps` showing all 4 services healthy
- [ ] First API call showing `"source": "database"`
- [ ] Second API call showing `"source": "cache"`
- [ ] Redis CLI showing cached key with TTL
- [ ] MySQL showing seeded data
- [ ] Data persisting after container restart
