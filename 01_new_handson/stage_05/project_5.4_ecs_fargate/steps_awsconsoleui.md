# Project 5.4 — AWS Console UI Steps: ECS Fargate

## Prerequisites Check

- [ ] AWS Console access with ECS, EC2, IAM, and CloudWatch permissions
- [ ] Docker image pushed to ECR (from project 5.1 or 5.3)
- [ ] `ecsTaskExecutionRole` IAM role exists (created in GUIDE.md Step 1)
- [ ] Default VPC with at least 2 public subnets in different AZs
- [ ] Region selected in Console (e.g., us-east-1)

---

## Step 1: Create an ECS Cluster

1. In the AWS Console search bar, type **ECS** → click **Elastic Container Service**
2. In the left sidebar, click **Clusters**
3. Click **Create cluster** (orange button, top right)
4. Configure:
   - **Cluster name**: `my-fargate-cluster`
   - **Infrastructure**: check **AWS Fargate (serverless)** ✅
   - Uncheck EC2 instances (not needed for Fargate)
5. Expand **Monitoring**:
   - Enable **Container Insights** ✅ (sends metrics to CloudWatch)
6. Click **Create**
7. Wait for "Cluster created" confirmation (a few seconds)

📸 Screenshot checkpoint: ECS Clusters list showing `my-fargate-cluster` with status ACTIVE

---

## Step 2: Create a Task Definition

1. In ECS left sidebar, click **Task definitions**
2. Click **Create new task definition** → **Create new task definition with JSON** OR use the wizard:

**Using the wizard:**
1. Click **Create new task definition**
2. Configure:
   - **Task definition family**: `my-fargate-app`
   - **Launch type**: AWS Fargate
   - **Operating system**: Linux/X86_64
   - **CPU**: 0.25 vCPU
   - **Memory**: 0.5 GB
   - **Task role**: (leave empty for now)
   - **Task execution role**: `ecsTaskExecutionRole`

3. Under **Container - 1**:
   - **Name**: `app`
   - **Image URI**: paste your ECR URI (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/flask-app:1.0.0`)
   - **Container port**: `8080`
   - **Protocol**: TCP
   - **App protocol**: HTTP

4. Expand **Logging**:
   - Log collection: **Use log collection** ✅
   - **awslogs** settings auto-populate:
     - Log group: `/ecs/my-fargate-app`
     - Region: your current region
     - Stream prefix: `ecs`

5. Click **Create**

📸 Screenshot checkpoint: Task definition `my-fargate-app:1` showing CPU 0.25 vCPU, Memory 512 MB

---

## Step 3: Review Task Definition JSON (Optional)

1. In the task definition, click the **JSON** tab
2. Review the full configuration including:
   - `requiresCompatibilities: ["FARGATE"]`
   - `networkMode: "awsvpc"`
   - `cpu: "256"`, `memory: "512"`
   - Container definition with image URI and log configuration
3. This JSON can be version-controlled for infrastructure-as-code workflows

📸 Screenshot checkpoint: Task definition JSON tab showing full configuration

---

## Decision Point: Configure Container Health Check

| Health Check Location | Scope | Behavior |
|----------------------|-------|----------|
| Task definition (Docker health check) | Container-level | ECS marks task unhealthy and replaces it |
| ALB target group | ALB-level | ALB stops routing to unhealthy target |

Best practice: configure both. The task definition health check catches application crashes; the ALB health check controls traffic routing.

---

## Step 4: Create an Application Load Balancer

1. Go to **EC2** (search bar) → **Load Balancers** (left sidebar)
2. Click **Create load balancer**
3. Select **Application Load Balancer** → **Create**
4. Configure:
   - **Name**: `my-fargate-alb`
   - **Scheme**: Internet-facing
   - **IP address type**: IPv4
5. **Network mapping**:
   - VPC: select your default VPC
   - Mappings: check 2 availability zones (each with a public subnet)
6. **Security groups**:
   - Create new: `my-fargate-alb-sg`
   - Inbound: HTTP port 80 from `0.0.0.0/0`
7. **Listeners and routing**:
   - Protocol: HTTP, Port: 80
   - Default action: **Create target group** (opens new tab)

### Create Target Group (in the new tab):
- Target type: **IP addresses**
- Name: `my-fargate-tg`
- Protocol: HTTP, Port: 8080
- Health check path: `/health`
- Click **Next** → no manual registrations (ECS registers automatically)
- Click **Create target group**

8. Back in the ALB creation, select `my-fargate-tg` as the target group
9. Click **Create load balancer**

📸 Screenshot checkpoint: Load balancers list showing `my-fargate-alb` in Active state

---

## Step 5: Create the ECS Service

1. Go to ECS → Clusters → `my-fargate-cluster`
2. Click the **Services** tab
3. Click **Create**
4. Configure:

**Environment:**
- Compute options: **Launch type** → **FARGATE**
- Platform version: **LATEST**

**Deployment configuration:**
- Application type: **Service**
- Family: `my-fargate-app`
- Revision: `1 (LATEST)`
- Service name: `my-fargate-service`
- Desired tasks: **2**

**Networking:**
- VPC: default VPC
- Subnets: select 2+ public subnets
- Security group:
  - Create new: `my-fargate-ecs-sg`
  - Inbound: custom TCP port 8080, source: `my-fargate-alb-sg`
- Public IP: **Turned on** (needed for public subnets without NAT)

**Load balancing:**
- Load balancer type: **Application Load Balancer**
- Select: **Use an existing load balancer**
- Load balancer: `my-fargate-alb`
- Listener: port 80 (existing)
- Target group: `my-fargate-tg`

**Service auto scaling (optional):**
- Skip for now (manual scaling with desired count 2)

5. Click **Create**

📸 Screenshot checkpoint: Service creation confirmation showing service name, desired count 2, Fargate launch type

---

## Step 6: Monitor Service Deployment

1. After creation, you're on the service detail page
2. Click the **Deployments** tab — see the rollout in progress
3. Watch **Running count** increase from 0 to 2
4. Click **Events** tab — shows health check passing, tasks registering

📸 Screenshot checkpoint: Service detail showing Running: 2, Pending: 0, Desired: 2

---

## Step 7: Test the Application via ALB

1. Go to EC2 → Load Balancers → `my-fargate-alb`
2. Copy the **DNS name** (e.g., `my-fargate-alb-123456.us-east-1.elb.amazonaws.com`)
3. Open a browser or terminal:
   ```
   http://my-fargate-alb-123456.us-east-1.elb.amazonaws.com/health
   ```
4. Expected response:
   ```json
   {"healthy": true}
   ```

📸 Screenshot checkpoint: Browser showing JSON health response from ALB DNS URL

---

## Step 8: View Container Logs

1. Go to **CloudWatch** → **Log groups**
2. Find `/ecs/my-fargate-app`
3. Click it → see log streams named `ecs/app/<task-id>`
4. Click a stream to view application output

📸 Screenshot checkpoint: CloudWatch log stream showing application startup logs

---

## Step 9: View Tasks and Networking

1. In ECS → `my-fargate-cluster` → `my-fargate-service`
2. Click the **Tasks** tab
3. Click on a task ARN
4. Review:
   - **Platform**: FARGATE
   - **CPU/Memory**: 0.25 vCPU / 512 MiB
   - **Network**: Private IP assigned (within VPC)
   - **Containers**: app — health: HEALTHY

📸 Screenshot checkpoint: Task detail showing Fargate platform, private IP, and container health

---

## Step 10: Cleanup via Console

1. ECS → `my-fargate-cluster` → `my-fargate-service`
2. Click **Update** → set Desired tasks to **0** → confirm
3. Wait for Running count = 0
4. Click **Delete service** → confirm
5. Go to EC2 → Load Balancers → select `my-fargate-alb` → Actions → **Delete**
6. EC2 → Target Groups → select `my-fargate-tg` → Actions → **Delete**
7. EC2 → Security Groups → delete `my-fargate-alb-sg` and `my-fargate-ecs-sg`
8. ECS → Clusters → select `my-fargate-cluster` → **Delete cluster**

📸 Screenshot checkpoint: ECS Clusters list showing empty or cluster deleted

---

## Troubleshooting

**Tasks keep stopping with "essential container exited":**
- Go to CloudWatch → `/ecs/my-fargate-app` → find recent log stream
- Container startup error will be visible in logs

**Service shows 0 running tasks (health checks failing):**
- Target group health check path `/health` must return HTTP 200
- Security group for ECS must allow port 8080 from ALB security group

**ALB returns 503 Service Unavailable:**
- Target group has no healthy targets yet — tasks still starting (wait 60-90 seconds)
- Check target group health in EC2 → Target Groups → Targets tab
