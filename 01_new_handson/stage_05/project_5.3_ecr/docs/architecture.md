# Architecture — Project 5.3 Push Containers to ECR

## ECR Registry Structure

```
AWS Account
    └── ECR Registry: ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
          ├── handson-flask-api
          │     ├── :latest          ← mutable, always newest
          │     ├── :1.0.0           ← semantic version
          │     ├── :git-abc1234     ← git SHA (immutable)
          │     └── :2024-01-15      ← date-based
          └── handson-backend
                └── :latest
```

## Push Workflow

```
docker build -t flask-api:latest .
    │
    ▼
docker tag flask-api:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/handson-flask-api:latest
    │
    ▼
aws ecr get-login-password | docker login --username AWS --password-stdin REGISTRY
    │
    ▼
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/handson-flask-api:latest
    │
    ▼
ECR stores image layers (deduplicated)
ECR scans image for CVEs (scan_on_push = true)
Lifecycle policy auto-deletes old images
```

## Lifecycle Policy

```
Rule 1: Keep last 10 tagged images (v*, release*)
Rule 2: Delete untagged images after 1 day

Prevents storage from growing unbounded.
Without lifecycle policy: thousands of images accumulate.
```

## Image Scanning

```
ECR Basic Scanning (free):
  → Scans on push using CVE database
  → Shows CRITICAL, HIGH, MEDIUM, LOW findings
  → Does NOT block push — you must check results

ECR Enhanced Scanning (paid):
  → Continuous scanning (not just on push)
  → Uses Amazon Inspector
```
