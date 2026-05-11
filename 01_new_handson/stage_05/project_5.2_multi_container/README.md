# Project 5.2 — Multi-container Application

## What This Does
Runs a full-stack application locally using Docker Compose: React frontend, Node.js backend API, MySQL database, and Redis cache — all wired together with Docker networking.

## Stack
| Service | Image | Port | Role |
|---------|-------|------|------|
| frontend | node:20-alpine | 3000 | React app (Nginx in prod) |
| backend | node:20-alpine | 4000 | Express REST API |
| db | mysql:8.0 | 3306 | Persistent data store |
| redis | redis:7-alpine | 6379 | Session cache + rate limiting |

## Architecture
```
Browser → Frontend (3000) → Backend API (4000) → MySQL (3306)
                                                 → Redis (6379)
```

## How to Run
```bash
docker compose up -d
docker compose logs -f
curl http://localhost:4000/health
```

## Lessons Learned
- `depends_on` with `condition: service_healthy` waits for DB to be ready before starting backend
- Named volumes persist data across container restarts — bind mounts are for development
- Docker networks isolate services — frontend can't directly reach MySQL (only backend can)
- Environment variables in `docker-compose.yml` should reference `.env` file — never hardcode passwords
- `docker compose down -v` removes volumes too — use carefully (deletes DB data)
- Health checks on MySQL/Redis prevent "connection refused" errors on startup
