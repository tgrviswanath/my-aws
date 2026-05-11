# Steps — Project 5.1 Single-service Docker Application

## Phase 1 — Build the Image

```bash
# Build with tag
docker build -t flask-api:1.0.0 .
docker build -t flask-api:latest .

# View image size (multi-stage should be ~120MB vs ~800MB without)
docker images flask-api

# Inspect layers
docker history flask-api:latest
```

---

## Phase 2 — Run the Container

```bash
# Basic run
docker run -p 5000:5000 flask-api:latest

# Run in background (detached)
docker run -d \
  --name flask-api \
  -p 5000:5000 \
  -e APP_ENV=development \
  -e APP_VERSION=1.0.0 \
  flask-api:latest

# Verify it's running
docker ps
docker logs flask-api
docker logs -f flask-api   # follow logs
```

---

## Phase 3 — Test the API

```bash
# Health check
curl http://localhost:5000/health | python3 -m json.tool

# Container info
curl http://localhost:5000/info | python3 -m json.tool

# CRUD operations
curl -s -X POST http://localhost:5000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "description": "A test item"}' | python3 -m json.tool

curl http://localhost:5000/items | python3 -m json.tool
```

---

## Phase 4 — Inspect the Container

```bash
# Execute a shell inside the running container
docker exec -it flask-api /bin/bash

# Inside container:
whoami          # should be: appuser (not root)
ps aux          # see gunicorn processes
env             # see environment variables
ls -la /app     # see app files

exit
```

---

## Phase 5 — Docker Layer Caching Demo

```bash
# First build (all layers built)
time docker build -t flask-api:cache-test .

# Change only app.py (not requirements.txt)
echo "# comment" >> app/app.py

# Second build — requirements layer is CACHED, only app layer rebuilds
time docker build -t flask-api:cache-test .
# Notice: "Using cache" for the pip install step
```

---

## Phase 6 — Health Check Verification

```bash
# Check health status
docker inspect flask-api | python3 -c "
import sys, json
data = json.load(sys.stdin)
health = data[0]['State']['Health']
print('Status:', health['Status'])
print('Last check:', health['Log'][-1]['Output'])
"

# Force unhealthy (stop the app inside container)
docker exec flask-api kill 1
docker ps  # should show: (unhealthy)
```

---

## Phase 7 — Cleanup

```bash
docker stop flask-api
docker rm flask-api
docker rmi flask-api:latest flask-api:1.0.0
```

---

## Screenshots to Take
- [ ] `docker build` output showing multi-stage build
- [ ] `docker images` showing small image size
- [ ] `docker ps` showing running container with health status
- [ ] API responses from curl
- [ ] `docker exec` showing non-root user
- [ ] Layer caching demo (second build much faster)
