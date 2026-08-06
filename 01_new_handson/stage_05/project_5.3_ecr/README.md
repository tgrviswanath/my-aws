# Project 5.3 — Amazon ECR — Container Registry

**Stage:** 05 | **Level:** Beginner-Intermediate | **Est. Time:** 1-2 hours | **Cost:** ~$0.10/GB stored

## Description

Create a private Amazon ECR repository, authenticate the local Docker daemon, push the `myapp:latest` image built in Project 5.1, and configure a lifecycle policy that keeps only the 10 most recent tagged images while deleting untagged layers daily. Enable image scanning on push so ECR runs a Clair-based vulnerability check automatically after each `docker push`. The final section previews pulling the same image URI from a different machine or from an ECS task — the same workflow ECS Fargate uses in Project 5.4.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Amazon ECR | Private container registry — stores `myapp` image layers | $0.10/GB-month after 500MB free |
| IAM | Policy granting `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, push/pull actions | Free |
| Docker CLI | Authenticates to ECR, tags and pushes the image | Free |
| ECR Image Scanning | Clair-based CVE scan triggered automatically on push | Free (basic scanning) |

---

## Input / Output

### Input

| Item | Description |
|---|---|
| `myapp:latest` | Local Docker image built in Project 5.1 (~120MB) |
| AWS credentials | IAM user or role with ECR push permissions in `us-east-1` |
| Lifecycle policy JSON | Rule to retain last 10 tagged images and delete untagged after 1 day |

### Output

| Result | Description |
|---|---|
| ECR repository | `myapp` private repo at `123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp` |
| Pushed image | `myapp:latest` available in ECR with a digest SHA |
| Lifecycle policy | Keeps last 10 tagged images; purges untagged images after 1 day |
| Scan report | `GET /findings` returns severity counts — 0 CRITICAL expected for a slim Python image |

---

## Architecture

```
  Local Machine                          AWS us-east-1
  ┌──────────────────────────┐           ┌──────────────────────────────────────┐
  │                          │           │                                      │
  │  myapp:latest            │           │  ECR Private Repository              │
  │  (from Project 5.1)      │           │  myapp                               │
  │                          │           │                                      │
  │  1. aws ecr              │           │  ┌────────────────────────────────┐  │
  │     get-login-password   │──────────▶│  │  myapp:latest                  │  │
  │  2. docker login ECR     │  push     │  │  myapp:v1.0.0                  │  │
  │  3. docker tag           │           │  │  (untagged layers → deleted)   │  │
  │  4. docker push          │           │  └────────────────────────────────┘  │
  │                          │           │           │                          │
  └──────────────────────────┘           │  Lifecycle Policy                   │
                                         │  Keep last 10 tagged                │
  Other machine / ECS Task               │  Delete untagged after 1 day        │
  ┌──────────────────────────┐           │           │                          │
  │  aws ecr                 │           │  Image Scanning (Clair)              │
  │     get-login-password   │◀──────────│  Triggered on push                  │
  │  docker pull ECR URI     │  pull     │  Severity: CRITICAL / HIGH / MEDIUM │
  └──────────────────────────┘           │                                      │
                                         └──────────────────────────────────────┘
```

---

## Quick Start

```cmd
REM 1. Set your account ID and region as variables for reuse
set AWS_ACCOUNT=123456789012
set AWS_REGION=us-east-1

REM 2. Create the private ECR repository with image scanning enabled on push
aws ecr create-repository --repository-name myapp --region %AWS_REGION% --image-scanning-configuration scanOnPush=true

REM 3. Authenticate Docker to ECR (token valid for 12 hours)
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %AWS_ACCOUNT%.dkr.ecr.%AWS_REGION%.amazonaws.com

REM 4. Tag the local image with the full ECR URI
docker tag myapp:latest %AWS_ACCOUNT%.dkr.ecr.%AWS_REGION%.amazonaws.com/myapp:latest

REM 5. Push the image to ECR (layers are deduplicated — only new layers upload)
docker push %AWS_ACCOUNT%.dkr.ecr.%AWS_REGION%.amazonaws.com/myapp:latest

REM 6. List images in the repository to confirm push succeeded
aws ecr list-images --repository-name myapp --region %AWS_REGION%

REM 7. Check scan findings (wait ~30s after push for scan to complete)
aws ecr describe-image-scan-findings --repository-name myapp --image-id imageTag=latest --region %AWS_REGION%

REM 8. Apply lifecycle policy — keep last 10 tagged, purge untagged after 1 day
aws ecr put-lifecycle-policy --repository-name myapp --region %AWS_REGION% --lifecycle-policy-text file://lifecycle-policy.json

REM 9. Verify the lifecycle policy was saved
aws ecr get-lifecycle-policy --repository-name myapp --region %AWS_REGION%

REM 10. Pull the image from ECR on any authenticated machine
docker pull %AWS_ACCOUNT%.dkr.ecr.%AWS_REGION%.amazonaws.com/myapp:latest
```

---

## Data Flow

1. `aws ecr create-repository` registers the `myapp` namespace in ECR and enables `scanOnPush` so every future push triggers an automatic vulnerability scan.
2. `aws ecr get-login-password` calls STS to generate a 12-hour Base64 token; the output is piped directly into `docker login` — the password never appears in shell history.
3. `docker tag` creates a local alias pointing the existing `myapp:latest` layer SHA to the ECR URI — no new image is built.
4. `docker push` uploads only the layers that ECR does not already have (based on layer digest comparison); shared base layers like `python:3.11-slim` are skipped if they were pushed previously.
5. ECR triggers the Clair scanner immediately after the push completes; results are stored per image digest and queryable via `describe-image-scan-findings`.
6. The lifecycle policy engine runs once daily; it counts tagged images in descending push-date order and deletes any beyond position 10, and immediately flags untagged images older than 1 day for deletion.
7. A second machine runs steps 2 and `docker pull` with the full ECR URI; IAM evaluates the principal's permissions before serving the layer presigned URLs.

---

## Project Files

| File | Description |
|---|---|
| `lifecycle-policy.json` | ECR lifecycle rules: keep last 10 tagged, delete untagged after 1 day |
| `iam-policy.json` | Minimum IAM policy for push: `GetAuthorizationToken`, push/pull actions |
| `README.md` | This file |

---

## Lessons Learned

- **ECR login tokens expire after 12 hours** — automating `aws ecr get-login-password | docker login` in CI/CD pipelines (or re-running it in a new terminal session) is mandatory; a stale token causes `401 Unauthorized` on push even with correct IAM permissions.
- **Image URI format is fixed: `ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPO:TAG`** — getting the region wrong in the URI causes a `repository does not exist` error that looks like a permissions problem.
- **Lifecycle policies run daily and are not retroactive on creation** — a policy set today won't clean up yesterday's untagged images until the next nightly execution cycle.
- **Basic scanning (Clair) vs enhanced scanning (Inspector) serve different needs** — basic scanning checks OS package CVEs; enhanced scanning also finds vulnerabilities in Python packages, Node modules, and other language ecosystems declared in `requirements.txt` or `package.json`.
- **ECR cross-account access requires a repository policy, not just IAM** — granting an IAM role in account B permission on account A's repository requires both an IAM policy in account B and a repository resource policy in account A allowing account B's principal.
- **Layer deduplication makes re-pushes fast** — only changed layers are uploaded; pushing a new `myapp:v1.0.1` that shares the `python:3.11-slim` base with `myapp:latest` uploads only the application layer diff, not the full 120MB.
