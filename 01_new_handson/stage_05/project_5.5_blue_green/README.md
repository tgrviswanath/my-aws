# Project 5.5 — Blue/Green Deployment on ECS

**Stage:** 05 | **Level:** Intermediate | **Est. Time:** 60–90 min | **Cost:** ~$0 extra over Project 5.4 ECS costs

Deploy a new ECS task revision with zero downtime using AWS CodeDeploy's blue/green strategy. CodeDeploy manages two target groups on the same ALB — the blue target group holds the current running tasks, and the green target group receives the new revision. Traffic shifts from blue to green via ALB listener rule update, with a 10-minute bake window where both environments are live. If a CloudWatch alarm fires during the bake period, CodeDeploy automatically rolls back to blue within seconds, making this the safest deployment strategy for production ECS workloads.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Amazon ECS (Fargate) | Runs both blue and green task sets during deployment | Pay-per-vCPU/memory-second |
| AWS CodeDeploy | Orchestrates traffic shift between blue-tg and green-tg | Free for ECS deployments |
| Application Load Balancer | Routes traffic via listener rules to blue or green target group | ~$0.008/LCU-hour (existing) |
| CloudWatch Alarms | Triggers automatic rollback if error rate threshold breached | ~$0.10/alarm/month |

## Input / Output

### Input

| Parameter | Value | Source |
|---|---|---|
| ECS Service | `my-fargate-service` running on cluster `my-cluster` | Project 5.4 output |
| New Task Definition | Revised revision with updated container image tag | `aws ecs register-task-definition` |
| Blue Target Group | `blue-tg` — currently receiving 100% of ALB traffic | Project 5.4 ALB setup |
| Green Target Group | `green-tg` — empty, receives traffic after CodeDeploy shift | Pre-created in Project 5.4 |
| Deployment Group | `my-ecs-dg` configured for blue/green with 10-min bake time | CodeDeploy console / CLI |
| CloudWatch Alarm | `ecs-5xx-error-alarm` on ALB 5XX count > 10 per minute | Project 5.4 monitoring |

### Output

| Result | Detail |
|---|---|
| Zero-downtime cutover | ALB listener rule updated atomically — no dropped requests |
| Green tasks active | New task revision running and passing health checks on `green-tg` |
| Bake period | Both blue and green tasks run simultaneously for 10 minutes |
| Traffic fully shifted | 100% traffic on `green-tg` after bake window with no alarm |
| Blue tasks terminated | Original task set drained and stopped after successful bake |
| Rollback (if alarm fires) | CodeDeploy re-routes listener back to `blue-tg`, green tasks stopped |

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │         Application Load Balancer        │
                        │   Listener :80  /  Listener :8080 (test)│
                        └───────────┬────────────────┬────────────┘
                                    │                │
                          (prod rule)│                │(test rule)
                                    ▼                ▼
                            ┌──────────────┐  ┌──────────────┐
                            │   blue-tg    │  │   green-tg   │
                            │  (current)   │  │  (new rev.)  │
                            └──────┬───────┘  └──────┬───────┘
                                   │                 │
                            ┌──────▼───────┐  ┌──────▼───────┐
                            │  ECS Tasks   │  │  ECS Tasks   │
                            │  (old image) │  │  (new image) │
                            │  Fargate     │  │  Fargate     │
                            └──────────────┘  └──────────────┘

                        ┌─────────────────────────────────────────┐
                        │              AWS CodeDeploy              │
                        │  1. Start deployment → spin up green     │
                        │  2. Health check green-tg                │
                        │  3. Shift prod listener to green-tg      │
                        │  4. Bake 10 min — watch CloudWatch alarm │
                        │  5a. No alarm → terminate blue tasks     │
                        │  5b. Alarm fires → shift back to blue-tg │
                        └─────────────────────────────────────────┘
```

## Quick Start

```cmd
REM ── Step 1: Register a new task definition revision (bump image tag) ──
aws ecs register-task-definition ^
  --cli-input-json file://task-def-v2.json ^
  --region us-east-1

REM ── Step 2: Note the new revision number from the output ──
REM   "taskDefinitionArn": "arn:aws:ecs:us-east-1:111122223333:task-definition/my-task:3"

REM ── Step 3: Create the appspec.json referencing the new revision ──
REM   Edit appspec.json: set TaskDefinition to the ARN from Step 2

REM ── Step 4: Create a CodeDeploy deployment ──
aws deploy create-deployment ^
  --application-name my-ecs-app ^
  --deployment-group-name my-ecs-dg ^
  --revision revisionType=AppSpecContent,appSpecContent={content="{\"version\":0.0,\"Resources\":[{\"TargetService\":{\"Type\":\"AWS::ECS::Service\",\"Properties\":{\"TaskDefinition\":\"arn:aws:ecs:us-east-1:111122223333:task-definition/my-task:3\",\"LoadBalancerInfo\":{\"ContainerName\":\"my-container\",\"ContainerPort\":80}}}}]}"} ^
  --region us-east-1

REM ── Step 5: Watch deployment progress ──
aws deploy get-deployment ^
  --deployment-id d-XXXXXXXXX ^
  --query "deploymentInfo.status" ^
  --region us-east-1

REM ── Step 6: Check both target group health during bake period ──
aws elbv2 describe-target-health ^
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/green-tg/abc123 ^
  --region us-east-1

REM ── Step 7: (Optional) Force rollback during bake window ──
aws deploy stop-deployment ^
  --deployment-id d-XXXXXXXXX ^
  --auto-rollback-enabled ^
  --region us-east-1
```

## Data Flow

1. Developer pushes a new container image to ECR and registers a new ECS task definition revision (`:3`).
2. `aws deploy create-deployment` is called with an `appspec.json` referencing the new task definition ARN.
3. CodeDeploy creates a replacement (green) task set in the ECS service — new Fargate tasks start with the new image.
4. ECS registers green tasks with `green-tg`; ALB runs health checks on the test listener (`:8080`) against `green-tg`.
5. Once green tasks pass health checks, CodeDeploy updates the production ALB listener rule to forward to `green-tg`.
6. Both blue (old) and green (new) task sets run simultaneously for the 10-minute bake window.
7. CodeDeploy monitors `ecs-5xx-error-alarm` throughout the bake period.
8. If the alarm stays green: CodeDeploy terminates the original blue task set — deployment complete.
9. If the alarm fires: CodeDeploy shifts the production listener rule back to `blue-tg` and stops green tasks within seconds.

## Project Files

| File | Description |
|---|---|
| `appspec.json` | CodeDeploy AppSpec defining ECS service, task definition ARN, and container port mapping |
| `task-def-v2.json` | Updated ECS task definition with new image tag for the green deployment |
| `deployment-group.json` | CodeDeploy deployment group config: blue/green type, bake time 10 min, alarm ARN |
| `cloudwatch-alarm.json` | ALB 5XX alarm definition — threshold 10 errors/min triggers auto-rollback |
| `README.md` | This file |

## Lessons Learned

- **Blue/green doubles task count during bake** — for the full 10-minute bake window you pay for both blue and green Fargate tasks simultaneously; rolling deployments keep the same task count by replacing in-place.
- **Two target groups are mandatory** — CodeDeploy's ECS blue/green integration requires a dedicated `blue-tg` and `green-tg` pre-registered on the ALB; you cannot use a single target group.
- **Rollback is listener-level, not task-level** — when an alarm fires, CodeDeploy changes the ALB listener rule back to `blue-tg` in seconds; the blue tasks were never stopped, so traffic restoration is near-instant.
- **Deployment configurations control the shift shape** — `CodeDeployDefault.ECSAllAtOnce` shifts 100% immediately; `ECSCanary10Percent5Minutes` sends 10% to green for 5 min then 100%; `ECSLinear10PercentEvery1Minutes` ramps 10% per minute over 10 steps.
- **The bake window is not a canary** — once CodeDeploy shifts the production listener to green, 100% of production traffic goes to green during the bake; canary (partial traffic split) is a separate deployment configuration.
- **Test listener on port 8080 enables smoke testing** — you can hit `green-tg` directly on `:8080` before the production shift happens, without exposing green to real users.
- **CodeDeploy deployment group must reference the ECS service by ARN**, not by name — mismatched cluster/service ARNs are the most common setup error when configuring the deployment group.
