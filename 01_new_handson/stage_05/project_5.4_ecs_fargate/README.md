# Project 5.4 — ECS Fargate Deployment

## What This Does
Deploys the containerized Flask API to ECS Fargate — AWS's serverless container platform. No EC2 instances to manage. Containers run on demand, scale automatically, and you pay only for what runs.

## Architecture
```
Internet → ALB (port 80/443) → ECS Fargate Tasks (port 5000)
                                    └── Pull image from ECR
                                    └── Write logs to CloudWatch
```

## Services Used
| Service | Role |
|---------|------|
| ECS Cluster | Logical grouping of tasks |
| ECS Service | Maintains desired task count, handles rolling deploys |
| Task Definition | Blueprint: image, CPU, memory, env vars, ports |
| Fargate | Serverless compute — no EC2 to manage |
| ALB | Load balancer across tasks |
| ECR | Source of container images |
| CloudWatch Logs | Container stdout/stderr |
| IAM | Task execution role + task role |

## Key Concepts
| Concept | Description |
|---------|-------------|
| Task Definition | Like a Dockerfile for ECS — defines the container config |
| Task | A running instance of a task definition |
| Service | Keeps N tasks running, handles health checks and rolling deploys |
| Task Execution Role | Allows ECS to pull from ECR and write to CloudWatch |
| Task Role | Permissions the application code has (e.g. S3 access) |
| Fargate | Serverless — AWS manages the underlying EC2 |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
terraform output alb_url
```

## Lessons Learned
- Task Execution Role ≠ Task Role: execution role is for ECS infrastructure; task role is for your app
- Fargate requires `awsvpc` network mode — each task gets its own ENI and private IP
- Rolling deployment: ECS replaces tasks one at a time — zero downtime by default
- `minimum_healthy_percent=50` + `maximum_percent=200` allows rolling deploy with 2 tasks
- Always set CPU and memory limits — Fargate bills by vCPU-hour and GB-hour
- Container logs go to CloudWatch automatically with `awslogs` log driver
