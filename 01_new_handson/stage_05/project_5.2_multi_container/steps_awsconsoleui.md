# Project 5.2 — AWS Console UI Steps: Multi-Container Stack

## Prerequisites Check

This project runs **entirely locally** using Docker Compose. There is no AWS Console interaction required for the core setup. However, if you want to push images to ECR before deploying, follow Step 1 below.

- [ ] Docker Desktop installed and running
- [ ] Docker Compose v2 available: `docker compose version`
- [ ] Ports 3000, 5432, 6379 are free on your machine
- [ ] At least 2GB of free disk space for images and volumes

---

## Step 1: (Optional) Create ECR Repositories via Console

If you want to store your images in ECR before running locally or pushing to ECS later:

1. Go to [AWS Console](https://console.aws.amazon.com) → search **ECR**
2. Click **Create repository**
3. Create the following repositories:
   - `multi-container/backend`
   - (PostgreSQL and Redis use official images from Docker Hub — no ECR needed)
4. For each repo:
   - Visibility: **Private**
   - Tag immutability: **Mutable** (for dev)
   - Scan on push: **Enabled**

📸 Screenshot checkpoint: ECR showing repositories `multi-container/backend`

---

## Step 2: Local Docker Desktop — Monitor Running Containers

After running `docker compose up -d`, you can use Docker Desktop to monitor:

1. Open **Docker Desktop**
2. Click the **Containers** tab in the left sidebar
3. You should see a group named `project_5.2_multi_container` (the project folder name)
4. Expand the group to see 3 containers:
   - `backend` — Node.js app
   - `postgres` — PostgreSQL 16
   - `redis` — Redis 7

📸 Screenshot checkpoint: Docker Desktop showing all 3 containers with green "Running" status

---

## Decision Point: Should I use Docker Desktop or CLI?

| Tool | Best for |
|------|----------|
| Docker Desktop | Visual monitoring, viewing logs with UI, quick inspection |
| Docker Compose CLI | Automation, scripting, CI/CD, reproducible deploys |
| AWS ECS Console | Production multi-container on AWS (see Project 5.4) |

For this project, use **Docker Compose CLI** as primary interface. Docker Desktop is supplementary.

---

## Step 3: Docker Desktop — View Container Logs

1. In Docker Desktop → Containers → `project_5.2_multi_container`
2. Click on the `backend` container
3. You see real-time logs in the **Logs** tab
4. Look for: `Backend running on port 3000`

Alternatively from CLI:
```bash
docker compose logs -f backend
```

📸 Screenshot checkpoint: Docker Desktop logs tab showing "Backend running on port 3000"

---

## Step 4: Docker Desktop — Inspect Container Details

1. Click on the `postgres` container in Docker Desktop
2. Navigate to the **Inspect** tab
3. Review:
   - **Environment variables**: POSTGRES_DB, POSTGRES_USER
   - **Ports**: 5432 → 5432
   - **Volumes**: postgres_data mounted at `/var/lib/postgresql/data`
4. Navigate to the **Stats** tab
5. Monitor CPU and memory usage in real time

📸 Screenshot checkpoint: Docker Desktop Inspect tab showing environment variables and volume mounts for postgres container

---

## Step 5: Verify Health via Docker Desktop

1. In Docker Desktop, healthy containers show a green dot
2. If a container shows a yellow/red indicator:
   - Click the container
   - Check **Logs** for error messages
   - Try restarting: click the ↺ icon

For CLI health check:
```bash
docker compose ps
# All STATUS column values should show "healthy" or "running"
```

📸 Screenshot checkpoint: Docker Desktop containers list showing all three with green health indicators

---

## Step 6: Test Application via Browser or curl

1. Open a browser and navigate to `http://localhost:3000/`
2. You should see:
   ```json
   {"status":"ok","service":"backend","version":"1.0.0"}
   ```
3. Navigate to `http://localhost:3000/health`
4. Expected:
   ```json
   {"api":"ok","postgres":"ok","redis":"ok"}
   ```

📸 Screenshot checkpoint: Browser showing health check JSON with all three services "ok"

---

## Troubleshooting

**Container shows "Exited" in Docker Desktop:**
- Click the container name → Logs tab → read the error
- Common: port already in use — change the port mapping in `docker-compose.yml`

**Backend shows `postgres: error` in health check:**
- Postgres might still be starting up — wait 15 seconds and retry
- Check postgres logs: `docker compose logs postgres`
- Verify healthcheck in `docker-compose.yml` uses `condition: service_healthy`

**"Cannot connect to the Docker daemon" error:**
- Docker Desktop is not running — launch it and wait for the engine to start

**Redis shows yellow in Docker Desktop:**
- Run `docker compose exec redis redis-cli ping` — if it returns PONG, Redis is fine
- Docker Desktop health display can lag by 5-10 seconds

**Volume data not showing after restart:**
- Named volumes persist through `docker compose stop/start`
- Data is lost only with `docker compose down -v`
- List volumes: `docker volume ls | grep project_5.2`

---

## Step 7: Inspect Named Volumes via Docker Desktop

1. In Docker Desktop, click the **Volumes** tab in the left sidebar
2. Find the following volumes created by this project:
   - `project_5.2_multi_container_postgres_data`
   - `project_5.2_multi_container_redis_data`
3. Click on `project_5.2_multi_container_postgres_data`
4. Explore the volume contents:
   - You see PostgreSQL data files (`PG_VERSION`, `base/`, `global/`, etc.)
   - This confirms data persists independently of the container lifecycle

📸 Screenshot checkpoint: Docker Desktop Volumes tab showing the two named volumes with their sizes

---

## Step 8: Export and Import Data for Migration

If you need to migrate or back up your PostgreSQL data:

```bash
# Export database to a SQL file
docker compose exec postgres pg_dump -U appuser appdb > backup.sql

# Verify the dump
head -20 backup.sql

# Import into a fresh database (after recreating volumes)
docker compose exec -T postgres psql -U appuser appdb < backup.sql
```

For Redis snapshot export:

```bash
# Trigger a Redis BGSAVE (background save)
docker compose exec redis redis-cli BGSAVE

# Check save status
docker compose exec redis redis-cli LASTSAVE
# Returns Unix timestamp of last save

# The RDB file is at /data/dump.rdb inside the container
# To copy it out:
docker compose cp redis:/data/dump.rdb ./redis-backup.rdb
```

📸 Screenshot checkpoint: Terminal showing pg_dump completing with SQL output file

---

## Step 9: Scale the Backend Service

Docker Compose allows running multiple instances of a service:

```bash
# Scale backend to 3 instances
docker compose up -d --scale backend=3

# Verify
docker compose ps
# Expected: 3 backend containers running on different host ports

# Note: When scaling, remove the fixed container_name from docker-compose.yml
# and the fixed port mapping "3000:3000" — use a range instead: "3000-3002:3000"
```

📸 Screenshot checkpoint: Docker Desktop showing 3 backend containers listed under the project group

---

## Step 10: View Network Details

Docker Compose creates an isolated bridge network. To inspect it:

```bash
# List Docker networks
docker network ls | grep project_5.2

# Inspect the network
docker network inspect project_5.2_multi_container_app_net

# The output shows all connected containers and their IPs:
# - backend: 172.x.x.2
# - postgres: 172.x.x.3
# - redis: 172.x.x.4

# Containers on this network can reach each other by service name
# Containers on this network are isolated from other Docker networks
```

📸 Screenshot checkpoint: Terminal output of `docker network inspect` showing all 3 containers connected to the bridge network
