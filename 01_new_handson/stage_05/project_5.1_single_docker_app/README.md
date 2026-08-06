# Project 5.1 — Single-service Docker Application

**Stage:** 05 | **Level:** Beginner | **Est. Time:** 1-2 hours | **Cost:** $0 (local only)

## Description

Containerize a Python Flask REST API using a Docker multi-stage build. The first stage installs dependencies in a full Python image; the second stage copies only the compiled artifacts into a slim runtime image, cutting the final size from ~350MB down to ~120MB. The container runs as a non-root user (`appuser`), declares a `/health` health check, and uses `.dockerignore` to keep secrets and bytecode out of the image. This project establishes the image-building habits — layer ordering, port binding, tagging — that feed directly into the ECR push workflow in Project 5.3.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Docker Engine | Build and run the container image locally | Free |
| Python 3.11-slim | Runtime base image for the Flask app | Free |
| Flask | Lightweight HTTP framework serving `GET /health` | Free |
| Amazon ECR | Tag target for the final image (preview, no push yet) | $0 (no push) |

---

## Input / Output

### Input

| File | Description |
|---|---|
| `app/app.py` | Flask application with `GET /health` route, bound to `0.0.0.0:8000` |
| `app/requirements.txt` | Pinned dependencies: `flask==3.0.3`, `gunicorn==22.0.0` |
| `Dockerfile` | Multi-stage build: `builder` stage + `runtime` stage |
| `.dockerignore` | Excludes `.env`, `__pycache__`, `*.pyc`, `.git`, `tests/` |

### Output

| Artifact | Description |
|---|---|
| `myapp:latest` | Docker image, ~120MB, built from slim runtime stage |
| Running container | Accessible at `http://localhost:8000` |
| `GET /health` response | `{"status": "healthy", "version": "1.0.0"}` with HTTP 200 |
| ECR-ready tag | `myapp:latest` re-tagged as `ACCOUNT.dkr.ecr.REGION.amazonaws.com/myapp:latest` |

---

## Architecture

```
  Local Machine
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │   Dockerfile (multi-stage)                           │
  │   ┌────────────────┐     ┌─────────────────────┐    │
  │   │  builder stage │     │   runtime stage     │    │
  │   │  python:3.11   │────▶│  python:3.11-slim   │    │
  │   │  pip install   │     │  USER appuser       │    │
  │   │  requirements  │     │  COPY --from=builder│    │
  │   └────────────────┘     └─────────┬───────────┘    │
  │                                    │                 │
  │                          docker build                │
  │                                    ▼                 │
  │                          myapp:latest (~120MB)        │
  │                                    │                 │
  │                          docker run -p 8000:8000     │
  │                                    ▼                 │
  │                     ┌──────────────────────────┐    │
  │                     │  Container (appuser)      │    │
  │                     │  gunicorn :8000           │    │
  │                     │  GET /health → 200 JSON   │    │
  │                     └──────────────────────────┘    │
  │                                    │                 │
  │                     curl localhost:8000/health       │
  │                                                      │
  │   (Preview) docker tag → ECR URI  ─────────────────▶ ECR
  └──────────────────────────────────────────────────────┘
```

---

## Quick Start

```cmd
REM 1. Build the image using multi-stage Dockerfile
docker build -t myapp:latest .

REM 2. Confirm image size is ~120MB (not 350MB+)
docker images myapp

REM 3. Run the container, map host port 8000 to container port 8000
docker run -d --name myapp-container -p 8000:8000 myapp:latest

REM 4. Test the health endpoint
curl http://localhost:8000/health

REM 5. Inspect the health check status Docker tracks automatically
docker inspect --format "{{.State.Health.Status}}" myapp-container

REM 6. View container logs (stdout from gunicorn)
docker logs myapp-container

REM 7. Confirm the process runs as non-root user
docker exec myapp-container whoami

REM 8. Stop and remove the container
docker stop myapp-container
docker rm myapp-container

REM 9. (Preview) Tag image for ECR — replace ACCOUNT and REGION
docker tag myapp:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest

REM 10. Verify the ECR-format tag exists locally
docker images 123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp
```

---

## Data Flow

1. `docker build` reads the `Dockerfile` and executes the **builder** stage: pulls `python:3.11`, runs `pip install -r requirements.txt`, caching the layer if `requirements.txt` is unchanged.
2. The **runtime** stage starts from `python:3.11-slim`, copies only the installed packages from the builder stage via `COPY --from=builder`.
3. `RUN adduser --disabled-password appuser` creates the non-root user; `USER appuser` switches context before `CMD`.
4. `.dockerignore` is read before any `COPY` instruction — `.env`, `__pycache__`, and `.git` never enter the build context.
5. `docker run -p 8000:8000` starts gunicorn inside the container, which binds to `0.0.0.0:8000` and becomes visible on the host.
6. Docker's built-in health check (`HEALTHCHECK CMD curl -f http://localhost:8000/health`) polls every 30 seconds and transitions the container to `healthy` after the first successful response.
7. `curl http://localhost:8000/health` on the host traverses the port mapping and reaches gunicorn, which returns `{"status": "healthy", "version": "1.0.0"}`.
8. `docker tag` creates an alias pointing the same image layer SHA to the ECR URI format, ready for `docker push` in Project 5.3.

---

## Project Files

| File | Description |
|---|---|
| `Dockerfile` | Multi-stage build: builder + slim runtime, non-root user, HEALTHCHECK |
| `app/app.py` | Flask app with `GET /health` route bound to `0.0.0.0:8000` |
| `app/requirements.txt` | `flask==3.0.3`, `gunicorn==22.0.0` with pinned versions |
| `.dockerignore` | Excludes `.env`, `*.pyc`, `__pycache__`, `.git`, `tests/` |
| `README.md` | This file |

---

## Lessons Learned

- **Multi-stage build cuts image size ~3x** — copying only the installed site-packages from a full builder into `python:3.11-slim` drops the image from ~350MB to ~120MB without any manual cleanup.
- **Flask must bind to `0.0.0.0`, not `127.0.0.1`** — inside a container, `127.0.0.1` is the container's own loopback; Docker's `-p` mapping only forwards traffic that reaches the container's network interface at `0.0.0.0`.
- **`USER appuser` must come after all `RUN` install steps** — switching user too early means `pip install` fails on permission errors because it can't write to `/usr/local/lib`.
- **`.dockerignore` is your first security layer** — without it, `COPY . .` pulls your `.env` file (with secrets) directly into the image layer, which persists even after a subsequent `RUN rm .env`.
- **Layer cache order matters: `COPY requirements.txt` before `COPY app/`** — if you copy the whole app first, any single-line code change busts the cache for `pip install`, adding 30-60 seconds to every rebuild.
- **`EXPOSE` is documentation, not a firewall rule** — it does not publish the port; only `docker run -p 8000:8000` actually maps it to the host. Omitting `EXPOSE` has no effect on reachability.
