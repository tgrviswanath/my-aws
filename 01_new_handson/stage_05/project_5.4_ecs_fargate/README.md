# Project 5.4 — ECS Fargate Deployment

**Stage:** 05 | **Level:** Intermediate | **Est. Time:** 3-4 hours | **Cost:** ~$25-40/month

## Description

Deploy the containerized application from ECR onto ECS Fargate — AWS's serverless container runtime where you manage tasks, not EC2 instances. A task definition declares 0.5 vCPU and 1GB RAM, references the ECR image URI, and injects a database password by pulling it from Secrets Manager at launch time via the task execution role. An ECS service maintains a desired count of 2 running tasks and uses a rolling update strategy (minimum healthy 50%, maximum 200%) so deployments replace containers without downtime. An Application Load Balancer distributes traffic across both tasks; container stdout and stderr flow to CloudWatch Logs automatically via the `awslogs` driver — no agent required.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Amazon ECS (Fargate) | Runs 2 containerized tasks without managing EC2 instances | ~$0.04048/vCPU-hour + $0.004445/GB-hour |
| Application Load Balancer | Distributes HTTP/HTTPS traffic to the 2 Fargate tasks | ~$16/month base + LCU charges |
| Amazon ECR | Source of the `myapp:latest` container image | ~$0.10/GB stored |
| AWS Secrets Manager | Stores DB password; injected into container as env variable at task launch | $0.40/secret/month |
| CloudWatch Logs | Receives container stdout/stderr via `awslogs` log driver | ~$0.50/GB ingested |
| IAM | Task role (app permissions) + execution role (ECR pull, Secrets Manager read, CW write) | Free |

---

## Input / Output

### Input

| Item | Description |
|---|---|
| ECR image URI | `123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest` from Project 5.3 |
| VPC + subnets | At least 2 public or private subnets in different AZs for ALB and tasks |
| Secrets Manager secret | `prod/myapp/db-password` — referenced in task definition by ARN |
| ALB + target group | HTTP:8000 target group with `/health` as the health check path |

### Output

| Result | Description |
|---|---|
| ECS cluster | `myapp-cluster` with 2 running Fargate tasks in `RUNNING` state |
| ALB DNS | `myapp-alb-xxxx.us-east-1.elb.amazonaws.com` serving `GET /health` with HTTP 200 |
| CloudWatch log group | `/ecs/myapp` receiving gunicorn access logs from both tasks |
| Rolling deployment | New task definition revision triggers replacement of both tasks without downtime |

---

## Architecture

```
  Internet
      │
      ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  Application Load Balancer                                      │
  │  myapp-alb  (port 443 → HTTP:8000)                              │
  │  Health check: GET /health every 30s                            │
  └───────────────┬─────────────────────────┬───────────────────────┘
                  │                         │
          AZ us-east-1a              AZ us-east-1b
                  │                         │
  ┌───────────────▼──────┐     ┌────────────▼─────────┐
  │  Fargate Task 1      │     │  Fargate Task 2       │
  │  0.5 vCPU / 1GB RAM  │     │  0.5 vCPU / 1GB RAM   │
  │  myapp:latest        │     │  myapp:latest         │
  │  port 8000           │     │  port 8000            │
  │  USER appuser        │     │  USER appuser         │
  └───────────┬──────────┘     └────────────┬──────────┘
              │                             │
              └──────────┬──────────────────┘
                         │
           ┌─────────────▼──────────────────┐
           │  ECS Task Role (app perms)      │
           │  ECS Execution Role             │
           │  ├─ ECR: pull myapp:latest      │
           │  ├─ Secrets Manager: read       │
           │  │    prod/myapp/db-password    │
           │  └─ CloudWatch Logs: write      │
           │       /ecs/myapp                │
           └────────────────────────────────┘
```

---

## Quick Start

```cmd
REM 1. Create the ECS cluster (Fargate — no EC2 instances)
aws ecs create-cluster --cluster-name myapp-cluster --region us-east-1

REM 2. Create CloudWatch log group before registering the task definition
aws logs create-log-group --log-group-name /ecs/myapp --region us-east-1

REM 3. Register the task definition (reads from task-definition.json)
aws ecs register-task-definition --cli-input-json file://task-definition.json --region us-east-1

REM 4. Confirm the task definition revision was created
aws ecs describe-task-definition --task-definition myapp --region us-east-1

REM 5. Create the ECS service with 2 desired tasks and ALB integration
aws ecs create-service --cluster myapp-cluster --service-name myapp-service --task-definition myapp --desired-count 2 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/myapp-tg/abc123,containerName=myapp,containerPort=8000" --region us-east-1

REM 6. Wait until both tasks reach RUNNING state
aws ecs wait services-stable --cluster myapp-cluster --services myapp-service --region us-east-1

REM 7. Test the ALB endpoint (replace with your actual ALB DNS)
curl http://myapp-alb-xxxx.us-east-1.elb.amazonaws.com/health

REM 8. Trigger a rolling deployment by registering a new task definition revision
aws ecs update-service --cluster myapp-cluster --service myapp-service --task-definition myapp:2 --region us-east-1

REM 9. Monitor rolling update — watch OldTasksCount drain to 0
aws ecs describe-services --cluster myapp-cluster --services myapp-service --region us-east-1 --query "services[0].{Running:runningCount,Pending:pendingCount,Desired:desiredCount}"

REM 10. Tail CloudWatch logs from both tasks
aws logs tail /ecs/myapp --follow --region us-east-1
```

---

## Data Flow

1. A client request hits the ALB listener on port 443; the listener forwards to the `myapp-tg` target group on port 8000.
2. The ALB health check (`GET /health` every 30 seconds) must return HTTP 200 before a task is added to the target group rotation.
3. ECS launches each Fargate task in its assigned subnet; the task execution role contacts Secrets Manager to retrieve `prod/myapp/db-password` and injects it as the `DB_PASSWORD` environment variable before the container process starts.
4. The same execution role pulls `myapp:latest` from ECR using a temporary credential scoped to the task launch.
5. The container starts gunicorn on `0.0.0.0:8000`; all stdout and stderr are captured by the `awslogs` log driver and streamed to `/ecs/myapp` in CloudWatch Logs — no sidecar or agent is involved.
6. The ECS task role (separate from the execution role) is attached to the running container process and governs what AWS APIs the application code itself can call (e.g., S3, DynamoDB).
7. When a new task definition revision is deployed, ECS applies the rolling update policy: with minimum healthy 50% and maximum 200%, it starts 2 new tasks before stopping the 2 old ones, keeping the service live throughout.
8. CloudWatch Logs receives a log stream per task; the stream name includes the container name, task definition name, and task ID for easy filtering across multiple running tasks.

---

## Project Files

| File | Description |
|---|---|
| `task-definition.json` | ECS task definition: 0.5 vCPU, 1GB RAM, ECR image URI, `awslogs` config, secret reference |
| `iam-execution-role.json` | Trust policy + inline policy for ECS execution role (ECR, Secrets Manager, CloudWatch) |
| `iam-task-role.json` | Trust policy for ECS task role (application-level AWS permissions) |
| `README.md` | This file |

---

## Lessons Learned

- **Task definition vs Task vs Service are three distinct concepts** — the task definition is the blueprint (image, CPU, memory, env vars); a task is one running instance of that blueprint; the service is the controller that maintains the desired number of tasks and handles rolling updates.
- **The execution role and task role are separate IAM roles with different scopes** — the execution role is used by the ECS control plane to pull images and write logs; the task role is used by the application code running inside the container. Conflating them leads to over-privileged application code.
- **Fargate tasks cannot reach ECR or Secrets Manager without a NAT gateway or VPC endpoints** — tasks in private subnets need either a NAT gateway or interface VPC endpoints for `ecr.api`, `ecr.dkr`, `secretsmanager`, and `logs`, otherwise the task fails to start with a `CannotPullContainerError`.
- **Rolling update math: minimum healthy 50% + maximum 200% = zero-downtime deploys** — ECS starts 2 new tasks (reaching 4 total = 200%) before stopping the 2 old ones (returning to 2 = 100%), ensuring the ALB always has healthy targets registered.
- **`awslogs` log driver sends container stdout directly to CloudWatch** — there is no need to install CloudWatch Agent or a Fluentd sidecar; anything the process writes to stdout/stderr appears in the log stream within seconds.
- **Secrets Manager injection happens at task launch, not image build** — the secret value is fetched fresh each time a task starts, so rotating the secret in Secrets Manager takes effect on the next task replacement without rebuilding the image.
- **ALB health checks gate target group registration** — if the container starts but `/health` returns non-200 (e.g., the app is still warming up), the task stays `draining` and never receives production traffic, protecting users from a broken deployment.
