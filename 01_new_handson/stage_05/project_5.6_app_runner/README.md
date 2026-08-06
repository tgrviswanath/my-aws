# Project 5.6 — AWS App Runner Deployment

**Stage:** 05 | **Level:** Beginner–Intermediate | **Est. Time:** 30–45 min | **Cost:** ~$5–15/month

Deploy the containerized application from Project 5.3's ECR image directly to AWS App Runner — a fully managed service that provisions compute, load balancing, TLS termination, and auto-scaling without any cluster, VPC, or ALB configuration. App Runner polls ECR for new image digests and triggers an automatic redeployment whenever a new image is pushed to the configured tag. Concurrency-based scaling adds instances when requests per instance exceed the configured threshold (default 100), and the service can scale to zero during idle periods to minimize cost. This project demonstrates how much operational overhead App Runner eliminates compared to the ECS Fargate setup in Project 5.4.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS App Runner | Managed compute runtime — handles load balancing, TLS, and auto-scaling | $0.064/vCPU-hour + $0.007/GB-hour (active); $0.005/GB-hour (paused) |
| Amazon ECR | Stores the container image; App Runner pulls from it on deploy and on new digest | ~$0.10/GB/month storage + $0.09/GB data transfer |
| IAM Access Role | Grants App Runner permission to pull images from ECR on your behalf | Free |

## Input / Output

### Input

| Parameter | Value | Source |
|---|---|---|
| ECR Image URI | `111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:latest` | Project 5.3 ECR push |
| Access Role ARN | `arn:aws:iam::111122223333:role/AppRunnerECRAccessRole` | IAM role with `AmazonEC2ContainerRegistryReadOnly` policy |
| Port | `80` | Application container listen port |
| CPU / Memory | `1 vCPU / 2 GB` | App Runner service configuration |
| Concurrency | `100` requests per instance | Default — increase for CPU-bound workloads |
| Auto-deploy | `AUTOMATIC` | Triggers on any new image digest pushed to `my-app:latest` |

### Output

| Result | Detail |
|---|---|
| Service URL | `https://xxxxxxxxxxxx.us-east-1.awsapprunner.com` — HTTPS, no setup required |
| Auto-scaling | App Runner adds instances when concurrent requests exceed 100 per instance |
| Scale-to-zero | Service pauses to 0 active instances after idle period; cold start ~5–15 sec |
| Auto-redeploy | Any `docker push` to `my-app:latest` in ECR triggers a new deployment automatically |
| Health status | App Runner health checks on `/` every 5 seconds; unhealthy instances replaced |

## Architecture

```
  Developer
     │
     │  docker push my-app:latest
     ▼
┌─────────────────────────────────────┐
│          Amazon ECR                 │
│  111122223333.dkr.ecr.us-east-1...  │
│  Repository: my-app                 │
│  Tag: latest  ◄── new digest?       │
└──────────────┬──────────────────────┘
               │  ECR polling (auto-deploy)
               ▼
┌─────────────────────────────────────────────────────┐
│                 AWS App Runner                       │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Managed Load Balancer  (HTTPS + TLS)        │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│         ┌───────────▼────────────┐                  │
│         │  Auto-scaling group    │                  │
│         │  Instance 1  (active)  │                  │
│         │  Instance 2  (active)  │  ← scales up     │
│         │  ...         (paused)  │    when load↑    │
│         └────────────────────────┘                  │
│                                                      │
│  Access Role → pulls image from ECR                 │
└─────────────────────────────────────────────────────┘
               │
               ▼
   https://xxxxxxxxxxxx.us-east-1.awsapprunner.com
```

## Quick Start

```cmd
REM ── Step 1: Create the IAM access role for App Runner to pull from ECR ──
aws iam create-role ^
  --role-name AppRunnerECRAccessRole ^
  --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"build.apprunner.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}" ^
  --region us-east-1

aws iam attach-role-policy ^
  --role-name AppRunnerECRAccessRole ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

REM ── Step 2: Create the App Runner service from the ECR image ──
aws apprunner create-service ^
  --service-name my-app-runner-service ^
  --source-configuration "{\"ImageRepository\":{\"ImageIdentifier\":\"111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:latest\",\"ImageRepositoryType\":\"ECR\",\"ImageConfiguration\":{\"Port\":\"80\"}},\"AutoDeploymentsEnabled\":true,\"AuthenticationConfiguration\":{\"AccessRoleArn\":\"arn:aws:iam::111122223333:role/AppRunnerECRAccessRole\"}}" ^
  --instance-configuration "{\"Cpu\":\"1 vCPU\",\"Memory\":\"2 GB\"}" ^
  --region us-east-1

REM ── Step 3: Wait for the service to reach RUNNING status ──
aws apprunner describe-service ^
  --service-arn arn:aws:apprunner:us-east-1:111122223333:service/my-app-runner-service/XXXXXXXX ^
  --query "Service.Status" ^
  --region us-east-1

REM ── Step 4: Get the service URL ──
aws apprunner describe-service ^
  --service-arn arn:aws:apprunner:us-east-1:111122223333:service/my-app-runner-service/XXXXXXXX ^
  --query "Service.ServiceUrl" ^
  --region us-east-1

REM ── Step 5: Test the endpoint ──
curl https://xxxxxxxxxxxx.us-east-1.awsapprunner.com/health

REM ── Step 6: Trigger a manual redeployment (optional) ──
aws apprunner start-deployment ^
  --service-arn arn:aws:apprunner:us-east-1:111122223333:service/my-app-runner-service/XXXXXXXX ^
  --region us-east-1

REM ── Step 7: Delete service when done to stop billing ──
aws apprunner delete-service ^
  --service-arn arn:aws:apprunner:us-east-1:111122223333:service/my-app-runner-service/XXXXXXXX ^
  --region us-east-1
```

## Data Flow

1. Developer builds a new Docker image locally and runs `docker push` to ECR repository `my-app:latest`.
2. App Runner's ECR poller detects a new image digest on the `latest` tag (polling interval ~1 minute).
3. App Runner pulls the new image using the `AppRunnerECRAccessRole` IAM role — no credentials are stored in the service config.
4. App Runner starts a new deployment: new instances boot with the updated image while old instances continue serving traffic.
5. Health checks on `/` confirm new instances are healthy; App Runner drains and replaces old instances.
6. Incoming HTTPS requests hit App Runner's managed load balancer, which routes to active instances.
7. When concurrent requests per instance exceed 100, App Runner adds more instances automatically — no scaling policy to configure.
8. During idle periods with no requests, App Runner scales active instances to zero and enters paused billing state.
9. First request after idle triggers a cold start (~5–15 seconds) to restore a warm instance.

## Project Files

| File | Description |
|---|---|
| `create-service.json` | Full App Runner `create-service` CLI input including source config, instance config, and auto-deploy flag |
| `iam-trust-policy.json` | IAM trust policy document scoped to `build.apprunner.amazonaws.com` for the access role |
| `README.md` | This file |

## Lessons Learned

- **App Runner abstracts the entire networking stack** — no VPC subnets, no security groups, no ALB listeners, no target groups; compared to Project 5.4, the setup is ~80% fewer AWS resources to manage.
- **The access role is required for private ECR** — without `AWSAppRunnerServicePolicyForECRAccess` attached to the role, the service creation succeeds but the first deployment fails silently at the image pull step.
- **Scale-to-zero is a dev/staging feature, not production** — the cold start latency (5–15 sec) on first request after idle is unacceptable for production SLAs; set minimum instances to 1 (`--instance-configuration MinSize=1`) for live traffic.
- **Concurrency per instance drives horizontal scale, not CPU** — App Runner adds instances when active requests per instance exceed the concurrency setting (default 100), regardless of CPU utilization; CPU-bound workloads should lower concurrency to 10–20 to scale earlier.
- **App Runner vs ECS Fargate** — App Runner wins on simplicity and time-to-deploy; Fargate wins on VPC integration, custom IAM task roles, sidecar containers, and GPU workloads; App Runner in basic mode has no VPC egress for private RDS or ElastiCache.
- **Auto-deploy watches image digest, not tag name** — pushing a new image to `:latest` changes the digest and triggers redeployment; pushing the exact same image layers (same digest) to `:latest` does not trigger a redeploy.
