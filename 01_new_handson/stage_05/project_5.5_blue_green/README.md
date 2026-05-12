# Project 5.5 — Blue-Green Deployment

## What This Does
Implements zero-downtime blue-green deployments using ECS + CodeDeploy. Traffic shifts from the current version (blue) to the new version (green) with instant rollback capability.

## How Blue-Green Works
```
Blue (current):  ALB → Target Group Blue  → ECS Tasks v1
Green (new):     ALB → Target Group Green → ECS Tasks v2

Deploy:
  1. Launch green tasks (v2) alongside blue (v1)
  2. Run smoke tests on green
  3. Shift 100% traffic to green instantly
  4. Blue tasks remain for 1 hour (rollback window)
  5. Blue tasks terminated after rollback window

Rollback:
  1. Shift traffic back to blue instantly
  2. No re-deployment needed
```

## vs Rolling Deployment
| Feature | Rolling | Blue-Green |
|---------|---------|-----------|
| Downtime | None | None |
| Rollback speed | Slow (re-deploy) | Instant |
| Cost during deploy | Normal | 2x (both versions running) |
| Traffic shift | Gradual | Instant (or canary) |
| Use case | Low-risk changes | High-risk changes, DB migrations |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- Blue-green requires two target groups — CodeDeploy manages the switch
- The `appspec.yml` file defines hooks (BeforeInstall, AfterInstall, etc.)
- Canary deployment: shift 10% to green first, then 90% after validation
- CodeDeploy rollback is automatic if health checks fail during deployment
- Keep the blue environment for at least 1 hour — gives time to catch issues

## Code

### `code/blue_green_deploy.py` — Control blue-green deployments via CodeDeploy

```bash
pip install boto3

# Deploy using an AppSpec stored in S3
python code/blue_green_deploy.py \
  --app MyApp \
  --group prod-bg-group \
  --revision s3://my-bucket/appspec.yaml

# Deploy with automatic rollback on failure
python code/blue_green_deploy.py \
  --app MyApp \
  --group prod-bg-group \
  --revision s3://my-bucket/appspec.yaml \
  --rollback

# Use a specific region
python code/blue_green_deploy.py \
  --app MyApp \
  --group prod-bg-group \
  --revision s3://my-bucket/appspec.yaml \
  --region us-east-1
```

What it does:
- Creates a CodeDeploy deployment
- Monitors traffic shift progress (BeforeAllowTraffic → AllowTraffic → AfterAllowTraffic)
- Prints instance counts (pending/in-progress/succeeded/failed) at each poll
- Triggers rollback on failure if `--rollback` is set
