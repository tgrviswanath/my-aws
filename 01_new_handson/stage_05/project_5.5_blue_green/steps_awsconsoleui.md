# Project 5.5 — AWS Console UI Steps: Blue-Green Deployment

## Prerequisites Check

- [ ] ECS cluster `my-fargate-cluster` exists and is ACTIVE
- [ ] ECS service `my-fargate-service` running with CodeDeploy controller
- [ ] ALB `my-fargate-alb` in Active state
- [ ] Two target groups exist: `my-fargate-tg` (blue) and `my-fargate-tg-green` (green)
- [ ] Task definition `my-fargate-app` revision 1 running (v1.0.0 image)
- [ ] Task definition revision 2 registered (v2.0.0 image)

---

## Step 1: Verify ECS Service Deployment Controller

1. Go to AWS Console → **ECS** → Clusters → `my-fargate-cluster`
2. Click **Services** tab → click on `my-fargate-service`
3. Under **Deployment configuration**, verify:
   - Deployment type: **Blue/green deployment (powered by AWS CodeDeploy)**
4. If it shows "Rolling update" instead:
   - You must delete and recreate the service with `CODE_DEPLOY` controller
   - The deployment controller cannot be changed on an existing service

📸 Screenshot checkpoint: Service detail showing "Blue/green deployment (powered by AWS CodeDeploy)" in Deployment configuration

---

## Step 2: Open CodeDeploy Console

1. In the search bar, type **CodeDeploy** → click **AWS CodeDeploy**
2. In the left sidebar, click **Applications**
3. Find and click `my-fargate-app`
4. You see 1 deployment group: `my-fargate-dg`

📸 Screenshot checkpoint: CodeDeploy Applications page showing `my-fargate-app` with ECS compute platform

---

## Step 3: Review Deployment Group Configuration

1. Click on `my-fargate-dg`
2. Review the configuration:
   - **Deployment type**: Blue/green
   - **ECS service**: `my-fargate-cluster` / `my-fargate-service`
   - **Load balancer**: `my-fargate-alb`
   - **Production listener**: Port 80
   - **Blue target group**: `my-fargate-tg`
   - **Green target group**: `my-fargate-tg-green`
   - **Traffic rerouting**: Reroute traffic immediately OR specify wait time

📸 Screenshot checkpoint: Deployment group configuration showing blue/green settings, target groups, and listener

---

## Decision Point: Traffic Shifting Strategy

| Strategy | How it works | Best for |
|----------|-------------|----------|
| `ECSAllAtOnce` | 100% traffic shifted at once | Dev, fast deploys |
| `ECSCanary10Percent5Minutes` | 10% → 5min wait → 100% | Production, gradual exposure |
| `ECSLinear10PercentEvery1Minute` | 10% more every minute | High-confidence gradual rollout |
| Custom | Define your own percentages | Specific business requirements |

For learning, `ECSAllAtOnce` is simplest. For production, use canary or linear.

---

## Step 4: Create a New Deployment via Console

1. In the `my-fargate-dg` deployment group, click **Create deployment**
2. Configure:
   - **Deployment group**: `my-fargate-dg` (pre-selected)
   - **Revision location**: Amazon S3
   - **S3 URL**: `s3://<your-account-id>-codedeploy-artifacts/appspec.json`
   - **Revision file type**: JSON (appspec)
3. (Optional) Add deployment description: `Deploy v2.0.0`
4. Under **Rollback configuration**:
   - ☑ Roll back when a deployment fails
   - ☑ Roll back when alarm thresholds are met
   - Add alarm: `fargate-app-5xx-alarm`
5. Click **Create deployment**

📸 Screenshot checkpoint: Create deployment form with S3 revision location and rollback configuration

---

## Step 5: Monitor the Deployment

1. After creation, you're on the deployment detail page
2. Watch the deployment lifecycle steps:

```
Step 1: Create replacement task set          [ In Progress ]
Step 2: Install replacement task set         [ Pending ]
Step 3: Reroute production traffic           [ Pending ]
Step 4: Terminate original task set          [ Pending ]
```

3. Green tasks start spinning up in the green target group
4. Once green tasks are healthy, traffic shifts

📸 Screenshot checkpoint: Deployment lifecycle showing all 4 steps, Step 1 or 2 In Progress

---

## Step 6: Verify Traffic Shift in Target Groups

While deployment is running:

1. Go to EC2 → Target Groups
2. Open `my-fargate-tg` (blue):
   - Targets tab: count should start decreasing (or stay at 2 during canary)
3. Open `my-fargate-tg-green` (green):
   - Targets tab: count should show new task IPs registering as Healthy

📸 Screenshot checkpoint: Target groups side by side showing blue targets draining and green targets healthy

---

## Step 7: Test Green Deployment Before Traffic Shift

If using a deployment configuration that waits before full traffic shift:

1. While still in the "Wait for approval" state, test via the test listener port:
   - `http://<ALB-DNS>:8080/` → this routes to the green task group
   - Verify version shows `2.0.0`
2. Once satisfied, click **Continue deployment** in the CodeDeploy console

📸 Screenshot checkpoint: CodeDeploy deployment page with "Continue deployment" button visible during traffic hold

---

## Step 8: Confirm Deployment Success

After all steps complete:

1. Deployment shows **Succeeded** status
2. Green tasks are now serving 100% of production traffic on port 80
3. Blue tasks are draining (5 minute wait)
4. After 5 minutes: blue tasks are terminated

📸 Screenshot checkpoint: Deployment detail page showing all steps with green checkmarks and "Succeeded" status

---

## Step 9: Verify via CloudWatch Alarms

1. Go to **CloudWatch** → **Alarms**
2. Find `fargate-app-5xx-alarm`
3. State should be **OK** (green) — no 5xx errors during deployment
4. If it shows **ALARM**: CodeDeploy would have auto-rolled back

📸 Screenshot checkpoint: CloudWatch alarm `fargate-app-5xx-alarm` in OK state after deployment

---

## Step 10: Test Manual Rollback

To simulate a rollback (optional, destructive test):

1. In CodeDeploy → Deployments → latest deployment
2. Click **Stop and roll back deployment**
3. Confirm: this re-routes traffic back to the original (blue) task set
4. Blue tasks are restored, green tasks are stopped

📸 Screenshot checkpoint: Manual rollback confirmation dialog in CodeDeploy

---

## Troubleshooting

**Deployment stays in "Create replacement task set" forever:**
- Check ECS service events for task startup failures
- Check CloudWatch logs for the new task definition
- Ensure the new image exists in ECR with the correct tag

**Green target group never becomes healthy:**
- Check security group allows ALB → ECS SG on port 8080
- Check the task definition health check command is correct
- Green tasks may be failing to start — check CloudWatch logs

**Traffic not shifting after green is healthy:**
- Check the deployment configuration: `ECSAllAtOnce` should shift immediately
- If using `ECSCanary`, wait for the configured time window
- Check if there's a manual approval gate configured

**Rollback not working:**
- Original (blue) task set may have been terminated already (only kept for `terminationWaitTimeInMinutes`)
- For rapid rollback, keep blue tasks alive longer by increasing `terminationWaitTimeInMinutes`

---

## Step 11: View Deployment History

1. In CodeDeploy → Applications → `my-fargate-app` → Deployments tab
2. Each deployment row shows:
   - Deployment ID (e.g., `d-ABCDEF123`)
   - Status: Succeeded / Failed / Stopped
   - Start time and duration
   - Deployment configuration used (e.g., `ECSAllAtOnce`)
3. Click a deployment ID to see step-by-step lifecycle

📸 Screenshot checkpoint: Deployments list showing deployment history with status, ID, and timestamps

---

## Step 12: Configure Automatic Deployment Trigger (Optional)

To make CodeDeploy trigger automatically when a new task definition is registered:

1. In CodeDeploy → `my-fargate-dg` → Edit
2. Under **Rollback configuration**:
   - ☑ Roll back when a deployment fails
   - ☑ Roll back when alarm thresholds are met
   - Alarm: `fargate-app-5xx-alarm`
3. Under **Advanced — optional**:
   - Deployment style: Blue/green (already set)
   - Traffic rerouting: **Automatically reroute traffic at the end of wait time**
   - Wait time: 0 minutes (immediate) or set a value for manual approval gate
4. Save changes

For fully automated CI/CD:
- Integrate with CodePipeline → CodeBuild builds image → pushes to ECR → registers new task definition → triggers CodeDeploy

📸 Screenshot checkpoint: Deployment group edit page showing rollback alarm configuration
