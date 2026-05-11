# Project 5.1 — Single-service Docker Application

## What This Does
Builds and runs a single containerized Python/Flask API locally using Docker. Covers Dockerfile best practices, container networking, environment variables, and health checks.

## Architecture
```
Docker Host
  └── Container: flask-api (port 5000)
        └── Flask app serving REST API
```

## Skills Covered
| Skill | Description |
|-------|-------------|
| Dockerfile | Build instructions for the image |
| Multi-stage build | Separate build and runtime stages — smaller image |
| .dockerignore | Exclude files from build context |
| Health check | Docker monitors container health |
| Environment variables | Config without hardcoding |
| Non-root user | Security best practice |

## How to Run
```bash
docker build -t flask-api .
docker run -p 5000:5000 flask-api
curl http://localhost:5000/health
```

## Lessons Learned
- Multi-stage builds reduce image size dramatically (e.g. 800MB → 120MB)
- Never run containers as root — create a dedicated app user
- Use `.dockerignore` to exclude `__pycache__`, `.env`, `*.pyc`, `node_modules`
- `COPY requirements.txt` before `COPY .` — Docker layer caching speeds up rebuilds
- `CMD` vs `ENTRYPOINT`: use `ENTRYPOINT` for the executable, `CMD` for default args
- Health checks let Docker (and ECS/EKS) know when a container is ready
