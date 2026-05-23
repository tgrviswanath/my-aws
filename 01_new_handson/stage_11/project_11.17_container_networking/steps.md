# Steps — Project 11.17 Container Networking (ECS/EKS)

## Phase 1 — Console

### 1.1 Create VPC
- VPC: `vpc-11-17`, CIDR: `10.0.0.0/16`
- Public subnets: `10.0.1.0/24` (AZ-a), `10.0.2.0/24` (AZ-b)
- Private subnets: `10.0.3.0/24` (AZ-a), `10.0.4.0/24` (AZ-b)
- IGW, NAT Gateway (one per AZ), route tables

### 1.2 Create ECS Cluster
1. **ECS** → **Clusters** → **Create cluster**
2. Name: `cluster-11-17`
3. Infrastructure: AWS Fargate
4. Create

### 1.3 Create Cloud Map Namespace
1. **Cloud Map** → **Namespaces** → **Create**
2. Name: `local`
3. Type: Private DNS namespace
4. VPC: `vpc-11-17`
5. Create

### 1.4 Create Task Definitions

**Web Task** (`td-web-11-17`):
- Launch type: Fargate
- Network mode: awsvpc (required for Fargate)
- CPU: 256, Memory: 512
- Container: `nginx:latest`, port 80

**API Task** (`td-api-11-17`):
- Same settings
- Container: `nginx:latest`, port 8080

### 1.5 Create Security Groups
- `sg-alb-11-17`: HTTP 80 from 0.0.0.0/0
- `sg-web-11-17`: HTTP 80 from `sg-alb-11-17`
- `sg-api-11-17`: TCP 8080 from `sg-web-11-17`

### 1.6 Create ALB and Target Group
- ALB: `alb-11-17` in public subnets, `sg-alb-11-17`
- Target group: `tg-web-11-17`, IP type (not instance), port 80
- Listener: HTTP 80 → `tg-web-11-17`

### 1.7 Create ECS Services

**Web Service** (`svc-web-11-17`):
- Cluster: `cluster-11-17`
- Task definition: `td-web-11-17`
- Launch type: Fargate
- Subnets: private subnets
- SG: `sg-web-11-17`
- Load balancer: `alb-11-17`, target group `tg-web-11-17`
- Service discovery: Cloud Map, service name `web`, namespace `local`

**API Service** (`svc-api-11-17`):
- Same cluster, `td-api-11-17`
- Subnets: private subnets
- SG: `sg-api-11-17`
- Service discovery: Cloud Map, service name `api`, namespace `local`

---

## Phase 2 — AWS CLI

```bash
CLUSTER=cluster-11-17
VPC_ID=<vpc-id>
PRIV_SUBNET_A=<private-subnet-a>
PRIV_SUBNET_B=<private-subnet-b>

# Create ECS cluster
aws ecs create-cluster --cluster-name $CLUSTER \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1

# Create Cloud Map namespace
NS_ID=$(aws servicediscovery create-private-dns-namespace \
  --name local \
  --vpc $VPC_ID \
  --query "OperationId" --output text)
# Wait for operation to complete
sleep 30
NS_ARN=$(aws servicediscovery list-namespaces \
  --query "Namespaces[?Name=='local'].Arn" --output text)

# Register task definition
aws ecs register-task-definition \
  --family td-web-11-17 \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 256 --memory 512 \
  --container-definitions '[{
    "name": "web",
    "image": "nginx:latest",
    "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
    "essential": true
  }]'

# Create service with service discovery
SVC_ARN=$(aws servicediscovery create-service \
  --name web \
  --dns-config "NamespaceId=$NS_ID,DnsRecords=[{Type=A,TTL=10}]" \
  --health-check-custom-config FailureThreshold=1 \
  --query "Service.Arn" --output text)

aws ecs create-service \
  --cluster $CLUSTER \
  --service-name svc-web-11-17 \
  --task-definition td-web-11-17 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIV_SUBNET_A,$PRIV_SUBNET_B],
    securityGroups=[<sg-web-id>],
    assignPublicIp=DISABLED}" \
  --service-registries "registryArn=$SVC_ARN"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check ECS cluster is active
aws ecs describe-clusters --clusters cluster-11-17 \
  --query "clusters[*].{Name:clusterName,Status:status,ActiveServices:activeServicesCount}"

# 2. Check services are running
aws ecs describe-services \
  --cluster cluster-11-17 \
  --services svc-web-11-17 svc-api-11-17 \
  --query "services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}"

# 3. Check tasks have ENIs with VPC IPs
aws ecs list-tasks --cluster cluster-11-17 --service-name svc-web-11-17
TASK_ARN=$(aws ecs list-tasks --cluster cluster-11-17 \
  --service-name svc-web-11-17 --query "taskArns[0]" --output text)
aws ecs describe-tasks --cluster cluster-11-17 --tasks $TASK_ARN \
  --query "tasks[0].attachments[?type=='ElasticNetworkInterface'].details"
# Should show privateIPv4Address in 10.0.x.x range

# 4. Check Cloud Map service discovery
aws servicediscovery list-services \
  --query "Services[*].{Name:Name,ID:Id}"
aws servicediscovery discover-instances \
  --namespace-name local \
  --service-name web \
  --query "Instances[*].Attributes"
# Should return task IPs

# 5. Check ALB target health
TG_ARN=$(aws elbv2 describe-target-groups --names tg-web-11-17 \
  --query "TargetGroups[0].TargetGroupArn" --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{IP:Target.Id,Port:Target.Port,Health:TargetHealth.State}"
```

---

## Phase 5 — Test

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers --names alb-11-17 \
  --query "LoadBalancers[0].DNSName" --output text)

# Test 1: ALB reaches web service
curl http://$ALB_DNS
# Expected: nginx welcome page

# Test 2: Service discovery — web task resolves api.local
# Get a shell in a running web task
TASK_ARN=$(aws ecs list-tasks --cluster cluster-11-17 \
  --service-name svc-web-11-17 --query "taskArns[0]" --output text)
aws ecs execute-command \
  --cluster cluster-11-17 \
  --task $TASK_ARN \
  --container web \
  --interactive \
  --command "/bin/sh"

# Inside the container:
nslookup api.local
# Expected: returns task IPs of api service (10.0.x.x)

curl http://api.local:8080
# Expected: nginx response from api task

# Test 3: Scale web service and verify new tasks register in Cloud Map
aws ecs update-service --cluster cluster-11-17 \
  --service svc-web-11-17 --desired-count 4
sleep 60
aws servicediscovery discover-instances \
  --namespace-name local --service-name web \
  --query "Instances[*].Attributes.AWS_INSTANCE_IPV4"
# Should now show 4 IPs

# Test 4: Verify task-level SG — web cannot reach api on port 80
# Inside web task:
nc -zv <api-task-ip> 80    # should FAIL (api SG only allows 8080 from web SG)
nc -zv <api-task-ip> 8080  # should SUCCEED

# Test 5: Verify private subnet — tasks have no public IPs
aws ecs describe-tasks --cluster cluster-11-17 --tasks $TASK_ARN \
  --query "tasks[0].attachments[0].details[?name=='publicIPv4Address']"
# Expected: empty (no public IP)

# Run automated checker
python code/ecs_checker.py --cluster cluster-11-17
```

### Verification Checklist
- [ ] ECS cluster active with Fargate capacity provider
- [ ] Web service: 2 running tasks, desired = running
- [ ] API service: 2 running tasks, desired = running
- [ ] Each task has a VPC IP (awsvpc mode confirmed)
- [ ] Cloud Map shows task IPs for `web.local` and `api.local`
- [ ] ALB target group: all targets healthy
- [ ] `curl http://<ALB_DNS>` returns nginx response
- [ ] `nslookup api.local` from web task returns api task IPs
- [ ] `curl http://api.local:8080` from web task succeeds
- [ ] Tasks have no public IPs (private subnet confirmed)
- [ ] SG enforcement: web cannot reach api on port 80

---

## Teardown
```bash
terraform destroy
# Scale services to 0 first, then delete services, then cluster
```
