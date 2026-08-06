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

## Phase 7 — Verification & Validation

### 7.1 AWS Console Verification
- **ECR** (if pushed): Repository → Images tab → confirm image tag and size
- **CloudWatch** (if running on ECS): Log groups → `/ecs/flask-api` → confirm log output

### 7.2 CLI Verification Commands
```bash
# Confirm image exists and check size
docker images flask-api --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
# Expected: flask-api  latest  ~120MB (multi-stage build)

# Confirm container is running and healthy
docker ps --filter "name=flask-api" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# Expected: flask-api  Up X seconds (healthy)  0.0.0.0:5000->5000/tcp

# Confirm non-root user inside container
docker exec flask-api whoami
# Expected: appuser

# Confirm health check passes
docker inspect flask-api --format "{{.State.Health.Status}}"
# Expected: healthy
```

### 7.3 Functional Tests
```bash
# Test 1: Health endpoint returns 200
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
echo "Health check HTTP status: $HTTP_STATUS"
# Expected: 200

# Test 2: Health response body is valid JSON with status ok
curl -s http://localhost:5000/health | python3 -m json.tool
# Expected: {"status": "ok", ...}

# Test 3: Info endpoint returns container metadata
curl -s http://localhost:5000/info | python3 -m json.tool
# Expected: hostname, version, environment fields present

# Test 4: CRUD — create an item
ITEM_ID=$(curl -s -X POST http://localhost:5000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "Verification test"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created item ID: $ITEM_ID"
# Expected: a UUID string

# Test 5: Retrieve the created item
curl -s http://localhost:5000/items/$ITEM_ID | python3 -m json.tool
# Expected: item with name "Test Item"

# Test 6: List all items
curl -s http://localhost:5000/items | python3 -m json.tool
# Expected: array containing the created item
```

### 7.4 Logs & Monitoring Checks
```bash
# Check container logs for errors
docker logs flask-api 2>&1 | grep -i "error\|exception\|traceback"
# Expected: no output (no errors)

# Check gunicorn started correctly
docker logs flask-api 2>&1 | grep "Listening at"
# Expected: [INFO] Listening at: http://0.0.0.0:5000

# Check health check log
docker inspect flask-api \
  --format "{{range .State.Health.Log}}{{.Output}}{{end}}"
# Expected: healthy response JSON
```

### 7.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| `docker images flask-api` | Size < 200MB (multi-stage) |
| `docker ps` status | `Up X (healthy)` |
| `curl /health` HTTP status | `200` |
| `docker exec whoami` | `appuser` (not root) |
| `curl /items` | Valid JSON array |
| Container logs | No ERROR lines |

### 7.6 Verification Checklist
- [ ] Image built successfully with multi-stage (size < 200MB)
- [ ] Container starts and reaches `healthy` status
- [ ] `/health` returns HTTP 200 with `{"status": "ok"}`
- [ ] `/info` returns hostname, version, environment
- [ ] POST `/items` creates item and returns UUID
- [ ] GET `/items` returns array with created item
- [ ] `whoami` inside container returns `appuser` (not root)
- [ ] No ERROR lines in container logs
- [ ] Layer caching works (second build uses cached layers)

---

## Screenshots to Take
- [ ] `docker build` output showing multi-stage build
- [ ] `docker images` showing small image size
- [ ] `docker ps` showing running container with health status
- [ ] API responses from curl
- [ ] `docker exec` showing non-root user
- [ ] Layer caching demo (second build much faster)

# AWS CLI Quick Reference

`ash
# Verify setup
aws sts get-caller-identity
aws configure list

# Common commands
aws ec2 describe-instances --output table
aws s3 ls
aws lambda list-functions --output table
`
