# Project 5.6 — AWS App Runner Deployment

## What This Does
Deploys the Flask API to AWS App Runner — the simplest way to run containers on AWS. No VPC, no ECS clusters, no ALB to configure. Just point at your ECR image and App Runner handles everything.

## App Runner vs ECS Fargate

| Feature | App Runner | ECS Fargate |
|---------|-----------|-------------|
| Setup complexity | Minimal | Moderate |
| VPC required | Optional | Yes |
| Load balancer | Built-in | Manual (ALB) |
| Auto-scaling | Built-in | Manual (ASG policy) |
| Custom networking | Limited | Full control |
| Price | Higher per vCPU | Lower |
| Use case | Simple web apps, APIs | Complex architectures |
| Best for | Prototypes, small teams | Production microservices |

## Architecture
```
Internet → App Runner (managed HTTPS endpoint)
              └── Pull from ECR automatically
              └── Scale 0 → N instances on demand
              └── Built-in health checks
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output app_runner_url
```

## Lessons Learned
- App Runner auto-scales to zero when idle — great for dev/staging environments
- Automatic deployments: App Runner watches ECR and redeploys on new image push
- No cold start penalty like Lambda — containers stay warm
- HTTPS is automatic — no ACM certificate management needed
- App Runner is more expensive per compute unit than Fargate but saves engineering time

## Code

### `code/app_runner_deploy.py` — Deploy or update AWS App Runner service

```bash
pip install boto3

# Create a new App Runner service (or update if it already exists)
python code/app_runner_deploy.py \
  --service my-api \
  --image 123456789.dkr.ecr.us-east-1.amazonaws.com/my-api:v2

# Custom port and resources
python code/app_runner_deploy.py \
  --service my-api \
  --image 123456789.dkr.ecr.us-east-1.amazonaws.com/my-api:v2 \
  --port 8080 \
  --cpu "1 vCPU" \
  --memory "2 GB"

# With ECR access role (required for private ECR images)
python code/app_runner_deploy.py \
  --service my-api \
  --image 123456789.dkr.ecr.us-east-1.amazonaws.com/my-api:v2 \
  --access-role-arn arn:aws:iam::123456789:role/AppRunnerECRAccessRole
```

What it does:
- Checks if the service exists — creates it if not, updates it if yes
- Waits for the service to reach `RUNNING` state (polls every 20s, up to 15 min)
- Prints the public HTTPS service URL on success
