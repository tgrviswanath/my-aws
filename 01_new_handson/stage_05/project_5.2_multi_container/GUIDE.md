# Project 5.2 — Multi-Container: Node.js + PostgreSQL + Redis with Docker Compose

## Overview

Run a multi-container application locally using Docker Compose. The stack consists of a Node.js Express backend, a PostgreSQL database, and a Redis cache. Containers communicate via Docker's internal DNS using service names.

---

## Prerequisites Check

```bash
# Check Docker and Docker Compose
docker --version
docker compose version
# Expected: Docker Compose version v2.x or later

# Check available ports
netstat -an | grep -E "3000|5432|6379" 2>/dev/null || ss -tlnp | grep -E "3000|5432|6379"
# Expected: no output (ports are free)

# Check Docker daemon
docker info | grep "Server Version"

# Verify enough disk space
df -h /var/lib/docker 2>/dev/null || df -h /
# Expected: at least 2GB free
```

**No AWS credentials required** — this project runs entirely locally.

---

## Decision Point 1: Docker Compose vs ECS

| Criteria | Docker Compose (Local) | ECS (Production) |
|----------|----------------------|-----------------|
| Setup time | Minutes | 30-60 minutes |
| Cost | $0 | ~$50-200/month for prod workload |
| Networking | Automatic service DNS | VPC, subnets, security groups |
| Scaling | Manual (scale command) | Auto-scaling policies |
| State management | Local volumes | EFS or RDS + ElastiCache |
| Secrets | .env files | AWS Secrets Manager |
| Best for | Local dev ✅ | Production ✅ |

**Decision:** Use Docker Compose for local development and learning. When ready for production, migrate to ECS (covered in Project 5.4).

---

## 1. Project Structure

```bash
mkdir -p project_5.2_multi_container/{backend,nginx}
cd project_5.2_multi_container

# Final structure will be:
# .
# ├── docker-compose.yml
# ├── docker-compose.override.yml  (dev overrides)
# ├── .env
# ├── backend/
# │   ├── Dockerfile
# │   ├── package.json
# │   └── src/
# │       └── index.js
# └── nginx/
#     └── nginx.conf
```

---

## 2. Create the Node.js Backend

```bash
# Create backend directory
mkdir -p backend/src

# package.json
cat > backend/package.json << 'EOF'
{
  "name": "multi-container-backend",
  "version": "1.0.0",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "pg": "^8.11.3",
    "ioredis": "^5.3.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.2"
  }
}
EOF

# Main application
cat > backend/src/index.js << 'EOF'
const express = require("express");
const { Pool } = require("pg");
const Redis = require("ioredis");

const app = express();
const PORT = process.env.PORT || 3000;

// PostgreSQL connection — uses "postgres" service name as DNS host
const pool = new Pool({
  host: process.env.DB_HOST || "postgres",
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || "appdb",
  user: process.env.DB_USER || "appuser",
  password: process.env.DB_PASSWORD || "secret",
});

// Redis connection — uses "redis" service name as DNS host
const redis = new Redis({
  host: process.env.REDIS_HOST || "redis",
  port: process.env.REDIS_PORT || 6379,
});

app.use(express.json());

app.get("/", (req, res) => {
  res.json({ status: "ok", service: "backend", version: "1.0.0" });
});

app.get("/health", async (req, res) => {
  const checks = { api: "ok", postgres: "unknown", redis: "unknown" };

  try {
    await pool.query("SELECT 1");
    checks.postgres = "ok";
  } catch (e) {
    checks.postgres = `error: ${e.message}`;
  }

  try {
    await redis.ping();
    checks.redis = "ok";
  } catch (e) {
    checks.redis = `error: ${e.message}`;
  }

  const allOk = Object.values(checks).every((v) => v === "ok");
  res.status(allOk ? 200 : 503).json(checks);
});

app.get("/db/init", async (req, res) => {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS items (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `);
  res.json({ message: "Table created" });
});

app.post("/items", async (req, res) => {
  const { name } = req.body;
  const result = await pool.query(
    "INSERT INTO items (name) VALUES ($1) RETURNING *",
    [name]
  );
  await redis.del("items:all"); // invalidate cache
  res.status(201).json(result.rows[0]);
});

app.get("/items", async (req, res) => {
  const cached = await redis.get("items:all");
  if (cached) {
    return res.json({ source: "cache", data: JSON.parse(cached) });
  }
  const result = await pool.query("SELECT * FROM items ORDER BY id");
  await redis.setex("items:all", 60, JSON.stringify(result.rows));
  res.json({ source: "db", data: result.rows });
});

app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));
EOF

# Dockerfile for backend
cat > backend/Dockerfile << 'EOF'
FROM node:20-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /build/node_modules ./node_modules
COPY src/ ./src/
COPY package.json .
USER appuser
EXPOSE 3000
CMD ["node", "src/index.js"]
EOF
```

---

## 3. Create the Docker Compose File

```bash
cat > docker-compose.yml << 'EOF'
version: "3.9"

# Named volumes — data persists across container restarts
volumes:
  postgres_data:
  redis_data:

# Default network — all services share it, DNS via service name
networks:
  app_net:
    driver: bridge

services:

  # ── Backend ──────────────────────────────────────────────────────────────
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend
    restart: unless-stopped
    environment:
      PORT: "3000"
      DB_HOST: postgres          # <-- service name used as DNS
      DB_PORT: "5432"
      DB_NAME: appdb
      DB_USER: appuser
      DB_PASSWORD: ${DB_PASSWORD:-secret}
      REDIS_HOST: redis          # <-- service name used as DNS
      REDIS_PORT: "6379"
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - app_net
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

  # ── PostgreSQL ────────────────────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secret}
    volumes:
      - postgres_data:/var/lib/postgresql/data  # named volume for persistence
    ports:
      - "5432:5432"
    networks:
      - app_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ── Redis ─────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data                        # named volume for persistence
    ports:
      - "6379:6379"
    networks:
      - app_net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
EOF
```

---

## 4. Create the .env File

```bash
cat > .env << 'EOF'
DB_PASSWORD=mysecretpassword
EOF
```

---

## 5. Start the Stack

### 5A. Local docker compose up

```bash
# Start all services in detached mode
docker compose up -d

# Watch logs from all services
docker compose logs -f

# Or watch a specific service
docker compose logs -f backend
```

### 5B. Docker Compose Commands Reference

```bash
# Start services
docker compose up -d

# Stop services (keeps containers and volumes)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop, remove containers AND volumes (data loss!)
docker compose down -v

# View running containers in the stack
docker compose ps

# Scale a service (run 3 backend instances)
docker compose up -d --scale backend=3

# Rebuild images after code changes
docker compose up -d --build

# Execute command in running container
docker compose exec backend sh
docker compose exec postgres psql -U appuser -d appdb

# View resource usage
docker compose stats

# View all logs with timestamps
docker compose logs -t

# Restart a specific service
docker compose restart backend
```

---

## 6. Initialize and Test the Application

```bash
# Wait for services to be healthy
docker compose ps
# All services should show "healthy" or "running"

# Initialize the database schema
curl -s http://localhost:3000/db/init | python3 -m json.tool

# Check health endpoint
curl -s http://localhost:3000/health | python3 -m json.tool
# Expected: all three checks = "ok"

# Create an item (POST)
curl -s -X POST http://localhost:3000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "test item"}' | python3 -m json.tool

# List items (first call — from DB)
curl -s http://localhost:3000/items | python3 -m json.tool
# Expected: source = "db"

# List items again (second call — from cache)
curl -s http://localhost:3000/items | python3 -m json.tool
# Expected: source = "cache"
```

---

## 7. Verify Service DNS Resolution

Docker Compose automatically sets up DNS so containers can reach each other by service name:

```bash
# From inside the backend container, verify DNS resolution
docker compose exec backend sh -c "nslookup postgres"
docker compose exec backend sh -c "nslookup redis"

# Test connectivity
docker compose exec backend sh -c "nc -zv postgres 5432 && echo 'PostgreSQL: reachable'"
docker compose exec backend sh -c "nc -zv redis 6379 && echo 'Redis: reachable'"
```

---

## 8. Test Redis Directly

```bash
# Ping Redis
docker compose exec redis redis-cli ping
# Expected: PONG

# Check all keys
docker compose exec redis redis-cli keys "*"

# Check cached items
docker compose exec redis redis-cli get "items:all"

# View Redis info
docker compose exec redis redis-cli info server | head -20
```

---

## 9. Test PostgreSQL Directly

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U appuser -d appdb

# Inside psql:
\dt          -- list tables
SELECT * FROM items;
\q           -- quit
```

---

## 10. Cleanup

```bash
# Stop and remove all containers, networks (keep volumes)
docker compose down

# Full cleanup including volumes (removes all data)
docker compose down -v

# Remove built images
docker rmi project_5.2_multi_container-backend 2>/dev/null || true

# Prune unused Docker resources
docker system prune -f
```

---

## Troubleshooting

**Backend can't connect to PostgreSQL:**
```bash
# Check postgres health
docker compose ps postgres
docker compose logs postgres
# Common cause: backend started before postgres was ready
# Fix: ensure depends_on with condition: service_healthy is in docker-compose.yml
```

**Redis connection refused:**
```bash
docker compose logs redis
# Confirm Redis is running
docker compose ps redis
# If not healthy, restart it
docker compose restart redis
```

**Port conflict (5432 already in use):**
```bash
# Find what's using the port
lsof -i :5432
# Or change the host port in docker-compose.yml:
# ports: ["5433:5432"]  <-- expose on 5433 instead
```

**`depends_on` not waiting long enough:**
- Use `condition: service_healthy` not just `depends_on: [postgres]`
- The `healthcheck` definition on the dependent service must be correct

**Named volume data not persisting:**
```bash
# List volumes
docker volume ls | grep project_5.2
# Inspect volume
docker volume inspect project_5.2_multi_container_postgres_data
```

---

## Expected Outcome

After completing this guide:

- ✅ All 3 containers running (backend, postgres, redis)
- ✅ DNS resolution works: backend reaches postgres and redis by service name
- ✅ `/health` endpoint returns `{"api":"ok","postgres":"ok","redis":"ok"}`
- ✅ Cache-aside pattern working: first request from DB, subsequent from Redis
- ✅ Named volumes preserving data across `docker compose stop/start`
- ✅ `docker compose down` cleanly removes containers and network
