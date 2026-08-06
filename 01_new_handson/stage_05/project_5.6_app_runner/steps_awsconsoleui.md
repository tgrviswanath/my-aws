# Project 5.6 — AWS Console UI Steps: AWS App Runner

## Prerequisites Check

- [ ] AWS Console access with App Runner, IAM, and ECR permissions
- [ ] Flask image pushed to ECR (`flask-app:1.0.0`) — from project 5.1
- [ ] `AppRunnerECRAccessRole` IAM role created (GUIDE.md Step 1)
- [ ] Region supports App Runner (us-east-1, us-east-2, us-west-2, eu-west-1, and more)

---

## Step 1: Navigate to App Runner

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. In the search bar, type **App Runner** → click **AWS App Runner**
3. You land on the App Runner dashboard
4. If no services exist yet, you see "Get started with AWS App Runner" with a **Create service** button

📸 Screenshot checkpoint: App Runner dashboard showing "Create service" button and empty services list

---

## Step 2: Create an App Runner Service — Source Configuration

1. Click **Create service**
2. **Source and deployment** section:
   - Repository type: **Container registry**
   - Provider: **Amazon ECR**
3. Under **Container image URI**, click **Browse**:
   - Select repository: `flask-app`
   - Select image tag: `1.0.0`
   - Click **Continue**
4. Under **Deployment settings**:
   - Deployment trigger: **Manual** (you control when to deploy new versions)
   - Alternative: **Automatic** — App Runner watches ECR and deploys on new push
5. ECR access role: select **AppRunnerECRAccessRole** (created in GUIDE.md Step 1)
6. Click **Next**

📸 Screenshot checkpoint: Source configuration page showing ECR repository `flask-app:1.0.0` selected with AppRunnerECRAccessRole

---

## Step 3: Configure Service Settings

1. **Service settings:**
   - Service name: `flask-app-runner`
   - Virtual CPU: **0.25 vCPU**
   - Memory: **0.5 GB**

2. **Environment variables (optional):**
   - Click **Add environment variable**
   - Key: `APP_VERSION` | Value: `1.0.0`
   - Key: `APP_ENV` | Value: `production`

3. **Port:**
   - Port: **8080**

4. **Health check:**
   - Protocol: **HTTP**
   - Path: `/health`
   - Healthy threshold: 1
   - Unhealthy threshold: 5
   - Timeout: 5 seconds
   - Interval: 10 seconds

📸 Screenshot checkpoint: Service configuration showing 0.25 vCPU, 0.5 GB, port 8080, and health check path /health

---

## Step 4: Configure Auto Scaling

1. Scroll down to **Auto scaling**
2. Click **Create configuration**:
   - Configuration name: `flask-app-scaling`
   - Max concurrency: **25** (requests per instance before scaling out)
   - Min size: **1** (always keep 1 warm instance)
   - Max size: **10** (cap at 10 instances)
3. Click **Add**
4. Confirm `flask-app-scaling` is selected

**Understanding concurrency-based scaling:**
- App Runner scales based on concurrent requests, not CPU/memory
- With `maxConcurrency: 25`, a second instance starts when there are 26+ simultaneous requests

📸 Screenshot checkpoint: Auto scaling configuration showing Min: 1, Max: 10, Max concurrency: 25

---

## Decision Point: Automatic vs Manual Deployment Trigger

| Trigger | Behavior | Best for |
|---------|----------|----------|
| Automatic | Deploys when ECR image tag is updated | CI/CD pipeline with mutable tags (e.g., `latest`) |
| Manual | Only deploys when you click "Deploy" | Immutable tags, production gates |

For this project, **Manual** is recommended when using immutable ECR tags.

---

## Step 5: Review and Create

1. Scroll through the review page to verify:
   - Source: `flask-app:1.0.0` from ECR
   - Port: 8080
   - CPU/Memory: 0.25 vCPU / 0.5 GB
   - Health check: HTTP `/health`
   - Auto scaling: Min 1, Max 10
2. Click **Create & deploy**

📸 Screenshot checkpoint: Review page summary with all configuration visible before clicking Create

---

## Step 6: Monitor Service Creation

1. You're redirected to the service detail page
2. Status shows: `Operation in progress` → `Creating` → `Running`
3. This typically takes 1-3 minutes
4. The **Events** log at the bottom shows deployment steps:
   ```
   Service status is set to OPERATION_IN_PROGRESS.
   Deploying new service.
   Health check is passing.
   Service status is set to RUNNING.
   ```

📸 Screenshot checkpoint: Service detail page showing status transitioning to RUNNING with event log

---

## Step 7: Access the Running Service

1. Once status is **Running**, find the **Default domain** at the top:
   ```
   https://abc123def456.us-east-1.awsapprunner.com
   ```
2. Click the URL or copy it to your browser/terminal:
   ```
   https://abc123def456.us-east-1.awsapprunner.com/health
   ```
3. Expected response:
   ```json
   {"healthy": true}
   ```

Note: App Runner automatically provides **HTTPS** with a managed TLS certificate. You get HTTPS out of the box.

📸 Screenshot checkpoint: Browser showing JSON response from the App Runner HTTPS URL

---

## Step 8: Deploy a New Version

1. In the App Runner service page, click **Deploy** (top right)
2. A dialog confirms: "Are you sure you want to trigger a manual deployment?"
3. Click **Deploy**
4. Watch the deployment in the Events log
5. The service updates with zero downtime (rolling replacement)

Alternatively, update to a new image:
1. Click **Configuration** tab → **Source and deployment**
2. Edit the Container image URI to `flask-app:2.0.0`
3. Click **Save changes** → this triggers a deployment

📸 Screenshot checkpoint: Service detail showing new deployment in progress after clicking Deploy

---

## Step 9: Configure Custom Domain (Optional)

1. Click the **Custom domains** tab
2. Click **Link domain**
3. Enter your domain: `app.yourdomain.com`
4. Click **Add**
5. App Runner provides DNS records:
   - A CNAME: `app.yourdomain.com → <service-url>`
   - Certificate validation CNAMEs (for HTTPS)
6. Add these records in your DNS provider (Route 53, Cloudflare, etc.)
7. After DNS propagation, the domain shows **Active** status

📸 Screenshot checkpoint: Custom domains tab showing domain in "Pending certificate DNS validation" status

---

## Step 10: Cleanup via Console

1. In the App Runner service page, click **Actions** → **Delete service**
2. A confirmation dialog appears — type the service name to confirm
3. Click **Delete**
4. Service moves to **Deleting** state then disappears

⚠️ After deletion, all access logs and metrics are retained in CloudWatch but the service stops billing.

📸 Screenshot checkpoint: Delete confirmation dialog with service name typed

---

## Troubleshooting

**Service creation fails (CREATE_FAILED):**
- Click into the Events log to see the exact failure reason
- Common: ECR access role doesn't have correct permissions
- Common: Container port mismatch (app runs on 8080 but 80 was configured)

**Health check failing during deployment:**
- App Runner retries health checks 5 times before failing
- Ensure `/health` returns HTTP 200 (not 404 or redirect)
- Check the app starts within 30 seconds (increase startPeriod if needed)

**"Unable to pull image" error:**
- Go to IAM → `AppRunnerECRAccessRole` → verify `AWSAppRunnerServicePolicyForECRAccess` is attached
- Ensure ECR repository is in the same region as App Runner

**Auto-scaling not triggering:**
- App Runner scales based on concurrent requests — not CPU
- Simulate concurrency: `ab -n 1000 -c 50 https://<url>/` (Apache Bench)
- Check Current count in the service metrics tab

**HTTPS certificate errors:**
- App Runner manages its own certificates — wait 2-3 minutes for HTTPS to fully initialize after creation
- Custom domain TLS requires DNS validation CNAMEs to be added

---

## Console Navigation Summary

```
App Runner Console
├── Services
│   └── flask-app-runner
│       ├── Overview (status, URL, deployment trigger)
│       ├── Events (deployment log)
│       ├── Metrics (requests, latency, concurrency)
│       ├── Logs → Application logs / Event logs
│       ├── Configuration
│       │   ├── Source and deployment
│       │   ├── Configure service (CPU, memory, env vars)
│       │   └── Auto scaling
│       └── Custom domains
└── Connections (ECR access connections)
```
