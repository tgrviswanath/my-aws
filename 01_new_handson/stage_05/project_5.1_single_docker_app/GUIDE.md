# Project 5.1 — Single Docker App: Python Flask with Multi-Stage Build & ECR

## Overview

Build a production-ready Python Flask application using a multi-stage Dockerfile with a non-root user, run it locally to verify, then push the image to Amazon ECR.

---

## Prerequisites Check

Before starting, confirm the following are installed and configured:

```bash
# Check Docker
docker --version
# Expected: Docker version 24.x or later

# Check AWS CLI
aws --version
# Expected: aws-cli/2.x

# Check AWS credentials
aws sts get-caller-identity
# Expected: JSON with Account, UserId, Arn

# Check Python (for local dev reference)
python3 --version
# Expected: Python 3.11+

# Verify Docker daemon is running
docker info | grep "Server Version"
```

**Required AWS permissions:**
- `ecr:CreateRepository`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:PutImage`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`
- `ecr:DescribeRepositories`
- `ecr:DescribeImages`

---

## Decision Point 1: Single-Stage vs Multi-Stage Build

| Factor | Single-Stage | Multi-Stage |
|--------|-------------|-------------|
| Image size | Large (includes build tools) | Small (only runtime artifacts) |
| Security surface | Higher (dev tools in prod image) | Lower (minimal final image) |
| Build time | Faster | Slightly longer |
| Production use | ❌ Not recommended | ✅ Recommended |
| Complexity | Low | Medium |

**Decision:** Use **multi-stage build** for this project. The builder stage installs dependencies and compiles any assets; the final stage copies only the necessary files into a slim Python image, running as a non-root user.

---

## 1. Project Structure Setup

Create the Flask application structure:

```bash
mkdir -p project_5.1_single_docker_app/app
cd project_5.1_single_docker_app

# Create Flask app
cat > app/main.py << 'EOF'
from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "hostname": socket.gethostname(),
        "version": os.getenv("APP_VERSION", "1.0.0")
    })

@app.route("/health")
def health():
    return jsonify({"healthy": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
EOF

# Create requirements
cat > requirements.txt << 'EOF'
flask==3.0.0
gunicorn==21.2.0
EOF
```

---

## 2. Write the Multi-Stage Dockerfile

```bash
cat > Dockerfile << 'EOF'
# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a target directory
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/packages -r requirements.txt

# ─── Stage 2: Final Runtime Image ────────────────────────────────────────────
FROM python:3.11-slim AS final

# Security: create non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /build/packages /app/packages

# Copy application source
COPY app/ /app/

# Set PYTHONPATH to include our packages
ENV PYTHONPATH=/app/packages
ENV APP_VERSION=1.0.0
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

EXPOSE 8080

# Use gunicorn for production
CMD ["python", "-m", "gunicorn", "--pythonpath", "/app/packages", \
     "--bind", "0.0.0.0:8080", "--workers", "2", "main:app"]
EOF
```

---

## 3. Add a .dockerignore File

```bash
cat > .dockerignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.env
.venv
venv/
*.egg-info/
.git/
.gitignore
README.md
tests/
*.md
EOF
```

---

## 4. Build and Test Locally

```bash
# Build the image
docker build -t flask-app:1.0.0 .

# Verify image was created and check size
docker images flask-app

# Run the container locally
docker run -d \
  --name flask-app-test \
  -p 8080:8080 \
  -e APP_VERSION=1.0.0 \
  flask-app:1.0.0

# Wait for startup
sleep 3

# Test the endpoints
curl http://localhost:8080/
curl http://localhost:8080/health

# Check container is running as non-root
docker exec flask-app-test whoami
# Expected: appuser

# Check running processes inside container
docker exec flask-app-test ps aux

# View logs
docker logs flask-app-test

# Stop and remove test container
docker stop flask-app-test && docker rm flask-app-test
```

---

## 5. Configure AWS and Create ECR Repository

### 5A. AWS Console: ECR → Create Repository → Get Push Commands

1. Open the AWS Console → **Amazon ECR** → **Repositories**
2. Click **Create repository**
3. Set:
   - Visibility: **Private**
   - Repository name: `flask-app`
   - Tag immutability: **Enabled** (recommended)
   - Image scan on push: **Enabled**
4. Click **Create repository**
5. Select the newly created repo → click **View push commands**
6. Copy the 4 push commands shown (authenticate, tag, push)

### 5B. AWS CLI: Create ECR Repository and Push Image

```bash
# Set variables
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="flask-app"
IMAGE_TAG="1.0.0"

echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"

# Create ECR repository
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability IMMUTABLE \
  --query 'repository.repositoryUri' \
  --output text

# Store the URI
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"
echo "ECR URI: $ECR_URI"

# Authenticate Docker to ECR
aws ecr get-login-password \
  --region $AWS_REGION | \
  docker login \
  --username AWS \
  --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Tag the local image
docker tag flask-app:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
docker tag flask-app:$IMAGE_TAG $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:latest

echo "Push complete!"
```

---

## 6. Verify the Push

```bash
# List images in ECR repository
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'imageDetails[*].{Tag:imageTags[0],Size:imageSizeInBytes,PushedAt:imagePushedAt}' \
  --output table

# Check image scan results (give it ~30 seconds after push)
aws ecr describe-image-scan-findings \
  --repository-name $ECR_REPO \
  --image-id imageTag=$IMAGE_TAG \
  --region $AWS_REGION \
  --query 'imageScanFindings.findingSeverityCounts'
```

---

## 7. Add a Lifecycle Policy (Optional Best Practice)

```bash
# Keep only the last 5 tagged images, delete untagged after 1 day
aws ecr put-lifecycle-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 5 tagged images",
        "selection": {
          "tagStatus": "tagged",
          "tagPrefixList": ["v", "1", "2"],
          "countType": "imageCountMoreThan",
          "countNumber": 5
        },
        "action": { "type": "expire" }
      },
      {
        "rulePriority": 2,
        "description": "Delete untagged images after 1 day",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 1
        },
        "action": { "type": "expire" }
      }
    ]
  }'
```

---

## 8. Pull and Run from ECR (Validation)

```bash
# Remove local image to simulate fresh pull
docker rmi flask-app:$IMAGE_TAG $ECR_URI:$IMAGE_TAG 2>/dev/null || true

# Pull from ECR
docker pull $ECR_URI:$IMAGE_TAG

# Run from ECR image
docker run -d \
  --name flask-ecr-test \
  -p 8080:8080 \
  $ECR_URI:$IMAGE_TAG

sleep 3
curl http://localhost:8080/health

# Clean up
docker stop flask-ecr-test && docker rm flask-ecr-test
```

---

## 9. Security Hardening Checklist

```bash
# Confirm image runs as non-root
docker run --rm $ECR_URI:$IMAGE_TAG whoami
# Expected: appuser (NOT root)

# Check no secrets in image layers
docker history flask-app:$IMAGE_TAG

# Scan for known vulnerabilities with Docker Scout (if available)
docker scout cves flask-app:$IMAGE_TAG

# Confirm final image size is reasonable (should be < 200MB)
docker images flask-app:$IMAGE_TAG --format "{{.Size}}"
```

---

## 10. Cleanup

```bash
# Delete ECR repository (WARNING: deletes all images)
aws ecr delete-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --force

# Remove local images
docker rmi flask-app:1.0.0 flask-app:latest 2>/dev/null || true
docker rmi $ECR_URI:1.0.0 $ECR_URI:latest 2>/dev/null || true

# Prune dangling images
docker image prune -f
```

---

## Troubleshooting

**`no basic auth credentials` when pushing:**
```bash
# Re-authenticate
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

**`RepositoryAlreadyExistsException`:**
```bash
# Repository already exists — just get the URI
aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --query 'repositories[0].repositoryUri' \
  --output text
```

**Permission denied running as non-root:**
- Ensure the app files are readable by UID 1001
- Add `RUN chown -R appuser:appgroup /app` before the USER directive

**Image size is unexpectedly large:**
- Verify multi-stage build is working: builder stage shouldn't appear in `docker images`
- Check `.dockerignore` is present and correct
- Use `docker history <image>` to find large layers

---

## Expected Outcome

After completing this guide:

- ✅ Multi-stage Dockerfile produces a slim Python image (< 200MB)
- ✅ Container runs as `appuser` (non-root, UID 1001)
- ✅ Flask app responds on port 8080 (`/` and `/health` endpoints)
- ✅ Image is pushed to ECR with tag `1.0.0` and `latest`
- ✅ ECR scan shows no CRITICAL vulnerabilities
- ✅ Lifecycle policy is in place to manage image retention
