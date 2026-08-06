# Project 5.2 — Multi-Container Application

**Stage:** 05 | **Level:** Beginner-Intermediate | **Est. Time:** 2-3 hours | **Cost:** $0 (local only)

## Description

Orchestrate three containers — a Node.js REST API, a PostgreSQL database, and a Redis cache — using Docker Compose. The Node.js service exposes `GET /users` on port 3000; it first checks Redis for a cached result and falls back to PostgreSQL if the key is absent, then writes the result to Redis with a 60-second TTL. All three services declare health checks and `depends_on: condition: service_healthy` so the API only starts after both the database and cache are confirmed ready. Named volumes keep PostgreSQL data intact across `docker compose down/up` cycles, preventing data loss between development sessions.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Docker Compose | Defines and starts all 3 containers with a single command | Free |
| Node.js 20-alpine | Runtime for the REST API (Express framework) | Free |
| PostgreSQL 16 | Relational database storing the `users` table | Free |
| Redis 7-alpine | In-memory cache with TTL-based key expiry | Free |

---

## Input / Output

### Input

| File | Description |
|---|---|
| `docker-compose.yml` | Declares `api`, `postgres`, and `redis` services, named volumes, health checks |
| `api/app.js` | Express app: cache-aside logic for `GET /users` |
| `api/package.json` | Dependencies: `express`, `pg`, `redis` |
| `.env` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `REDIS_TTL_SECONDS` |
| `db/init.sql` | Creates `users` table and inserts 3 seed rows on first startup |

### Output

| Result | Description |
|---|---|
| 3 running containers | `api` (3000), `postgres` (5432), `redis` (6379) — all `healthy` |
| `GET /users` first call | Queries PostgreSQL, returns JSON array, writes result to Redis |
| `GET /users` second call | Returns same JSON from Redis cache — no PostgreSQL query |
| Named volume `pgdata` | Survives `docker compose down`; data present on next `docker compose up` |

---

## Architecture

```
  Host Machine
  ┌────────────────────────────────────────────────────────────────┐
  │                                                                │
  │  docker-compose.yml                                            │
  │                                                                │
  │  ┌──────────────────────────────────────────────────────────┐  │
  │  │  Docker network: app-net (bridge)                        │  │
  │  │                                                          │  │
  │  │   ┌──────────────┐      ┌──────────────┐                │  │
  │  │   │   postgres    │      │    redis     │                │  │
  │  │   │  port 5432   │      │  port 6379   │                │  │
  │  │   │  healthcheck │      │  healthcheck │                │  │
  │  │   │  named vol   │      │              │                │  │
  │  │   │  pgdata      │      │              │                │  │
  │  │   └──────┬───────┘      └──────┬───────┘               │  │
  │  │          │  depends_on healthy  │                        │  │
  │  │          └──────────┬──────────┘                        │  │
  │  │                     ▼                                    │  │
  │  │            ┌────────────────┐                            │  │
  │  │            │      api       │                            │  │
  │  │            │  Node.js :3000 │                            │  │
  │  │            │  cache-aside   │                            │  │
  │  │            └────────┬───────┘                            │  │
  │  └─────────────────────┼────────────────────────────────────┘  │
  │                        │ -p 3000:3000                          │
  │                        ▼                                        │
  │              curl localhost:3000/users                         │
  │                                                                │
  └────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```cmd
REM 1. Copy the env template and fill in your credentials
copy .env.example .env

REM 2. Start all 3 services in detached mode
docker compose up -d

REM 3. Watch health status until all 3 show "healthy"
docker compose ps

REM 4. First request — hits PostgreSQL, populates Redis cache
curl http://localhost:3000/users

REM 5. Second request — served from Redis (check api logs to confirm)
curl http://localhost:3000/users

REM 6. Inspect api logs to see "CACHE HIT" vs "DB QUERY" messages
docker compose logs api

REM 7. Connect directly to PostgreSQL to verify the users table
docker compose exec postgres psql -U appuser -d appdb -c "SELECT * FROM users;"

REM 8. Connect to Redis and inspect the cached key
docker compose exec redis redis-cli GET users:all

REM 9. Stop containers but KEEP named volume pgdata intact
docker compose down

REM 10. Restart — PostgreSQL data is still there (named volume survived)
docker compose up -d
docker compose exec postgres psql -U appuser -d appdb -c "SELECT count(*) FROM users;"
```

---

## Data Flow

1. `docker compose up` reads `docker-compose.yml` and starts `postgres` and `redis` first; each runs its declared `HEALTHCHECK` (`pg_isready` / `redis-cli ping`).
2. The `api` service has `depends_on: postgres: condition: service_healthy` and `redis: condition: service_healthy` — Docker Compose holds it back until both pass.
3. A client sends `GET /users` to `localhost:3000`; the request reaches the Express handler inside the `api` container.
4. The handler calls `redis.get("users:all")`; on a cache miss it returns `null`.
5. The handler opens a `pg` connection to host `postgres` (resolved via Docker's internal DNS — the service name, not `localhost`) on port 5432 and runs `SELECT id, name, email FROM users ORDER BY id`.
6. The JSON result is written back to Redis with `SET users:all <json> EX 60`, starting a 60-second expiry clock.
7. The JSON array is returned to the client with HTTP 200.
8. On the next request within 60 seconds, step 4 returns the cached string; steps 5-6 are skipped entirely.
9. `docker compose down` stops and removes containers; the named volume `pgdata` is left on the host and re-attached to the `postgres` container on the next `up`.

---

## Project Files

| File | Description |
|---|---|
| `docker-compose.yml` | Defines `api`, `postgres`, `redis` services, `app-net` network, `pgdata` volume |
| `api/app.js` | Express server with cache-aside logic for `GET /users` |
| `api/package.json` | `express`, `pg`, `redis` dependencies |
| `db/init.sql` | Creates `users` table with `id`, `name`, `email`; inserts 3 seed rows |
| `.env` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `REDIS_TTL_SECONDS` |
| `.env.example` | Template with placeholder values safe to commit |
| `README.md` | This file |

---

## Lessons Learned

- **Service names are DNS hostnames inside Docker Compose** — the Node.js app connects to host `postgres` and `redis`, not `localhost`; using `localhost` causes `ECONNREFUSED` because each container has its own loopback.
- **`depends_on` alone is not enough for readiness** — without `condition: service_healthy`, Docker only waits for the container process to start, not for PostgreSQL to finish initializing; the API crashes on its first DB call.
- **Named volumes outlive `docker compose down`; anonymous volumes do not** — declaring `pgdata:` under `volumes:` and referencing it in the postgres service is the only way to keep data between restarts without a bind mount.
- **`.env` is loaded automatically by Docker Compose** — variables defined there are available to all services via `environment:` references (`${POSTGRES_USER}`) with no extra flags needed.
- **Cache-aside is intentionally explicit** — the app code owns the cache logic (check → fallback → write); Redis is never aware of PostgreSQL. This pattern makes the cache easy to invalidate without changing the DB schema.
- **Redis TTL prevents stale data accumulation** — without `EX 60`, the cached key lives forever; a single schema migration or data update would serve stale JSON to every user until a manual `redis-cli DEL` is run.
