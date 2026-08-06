# Project 5.2 — Verification Guide: Multi-Container Stack

---

## Section 1: Infrastructure Verification

Verify all containers are running with correct configuration.

### 1.1 All Containers Running

```bash
docker compose ps
```

Expected output:
```
NAME       IMAGE                              COMMAND                  SERVICE    CREATED         STATUS                   PORTS
backend    project_5.2_multi_container-backend  "node src/index.js"    backend    2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:3000->3000/tcp
postgres   postgres:16-alpine                  "docker-entrypoint.s…" postgres   2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:5432->5432/tcp
redis      redis:7-alpine                      "docker-entrypoint.s…" redis      2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:6379->6379/tcp
```

All containers must show `(healthy)` status.

### 1.2 Named Volumes Exist

```bash
docker volume ls | grep -E "postgres_data|redis_data"
```

Expected:
```
local     project_5.2_multi_container_postgres_data
local     project_5.2_multi_container_redis_data
```

### 1.3 Network Exists

```bash
docker network ls | grep project_5.2
```

Expected: `project_5.2_multi_container_app_net` network present.

### 1.4 DNS Resolution Between Containers

```bash
# Backend can resolve postgres by service name
docker compose exec backend sh -c "nslookup postgres" 2>/dev/null || \
  docker compose exec backend sh -c "getent hosts postgres"

# Backend can resolve redis by service name
docker compose exec backend sh -c "getent hosts redis"
```

Expected: Both return IP addresses within the Docker network (172.x.x.x).

### 1.5 Port Bindings

```bash
# Verify host ports are bound
ss -tlnp | grep -E "3000|5432|6379" 2>/dev/null || \
  netstat -tlnp | grep -E "3000|5432|6379"
```

Expected: All three ports open on 0.0.0.0.

---

## Section 2: Functionality Verification

### 2.1 Backend API Responds

```bash
curl -s http://localhost:3000/ | python3 -m json.tool
```

Expected:
```json
{
  "status": "ok",
  "service": "backend",
  "version": "1.0.0"
}
```

### 2.2 Health Check — All Services OK

```bash
curl -s http://localhost:3000/health | python3 -m json.tool
```

Expected:
```json
{
  "api": "ok",
  "postgres": "ok",
  "redis": "ok"
}
```

### 2.3 PostgreSQL Connection

```bash
# Direct connection from host
docker compose exec postgres pg_isready -U appuser -d appdb
# Expected: /var/run/postgresql:5432 - accepting connections

# Query from inside container
docker compose exec postgres psql -U appuser -d appdb -c "\dt"
# After running /db/init: shows items table
```

### 2.4 Redis Ping

```bash
docker compose exec redis redis-cli ping
# Expected: PONG

# Check Redis is configured with maxmemory
docker compose exec redis redis-cli config get maxmemory
# Expected: 134217728 (128MB in bytes)
```

### 2.5 Cache-Aside Pattern Working

```bash
# Initialize DB
curl -s http://localhost:3000/db/init

# Create a test item
curl -s -X POST http://localhost:3000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"verify-item"}'

# First request — should come from DB
RESULT1=$(curl -s http://localhost:3000/items)
echo "First call source: $(echo $RESULT1 | python3 -c "import sys,json; print(json.load(sys.stdin)['source'])")"
# Expected: db

# Second request — should come from cache
RESULT2=$(curl -s http://localhost:3000/items)
echo "Second call source: $(echo $RESULT2 | python3 -c "import sys,json; print(json.load(sys.stdin)['source'])")"
# Expected: cache
```

### 2.6 Data Persists Across Restart

```bash
# Stop containers (not down — keeps volumes)
docker compose stop

# Restart
docker compose start

# Wait for health
sleep 10
docker compose ps

# Items should still exist
curl -s http://localhost:3000/items | python3 -m json.tool
# Expected: same items as before restart
```

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Backend exits at startup | `docker compose ps` shows backend as "Exited (1)" | Run `docker compose logs backend` — likely can't connect to postgres; ensure `depends_on.condition: service_healthy` is set |
| `ECONNREFUSED redis:6379` | Health shows `redis: error: ...` | Check `docker compose logs redis`; ensure Redis is healthy before backend starts |
| Port 5432 already in use | postgres fails to start | Stop local PostgreSQL: `sudo systemctl stop postgresql` or change host port to 5433 |
| Items table not found | `relation "items" does not exist` from API | Hit `GET /db/init` first to create schema |
| Docker Compose v1 syntax error | `yaml: line X: found character that cannot start any token` | Ensure `docker compose` (v2, with space) not `docker-compose` (v1) is used |
