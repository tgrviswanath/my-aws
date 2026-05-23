# Steps — Project 5.5 Blue-Green Deployment

## Phase 1 — Deploy Infrastructure

```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"

ALB_URL=$(terraform output -raw alb_url)
DEPLOY_GROUP=$(terraform output -raw deployment_group_name)
APP_NAME=$(terraform output -raw codedeploy_app_name)
```

---

## Phase 2 — Initial Deployment (Blue)

```bash
# Create appspec.yml for CodeDeploy
cat > appspec.yml << 'EOF'
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: "flask-api"
          ContainerPort: 5000
EOF

# Start deployment
aws deploy create-deployment \
  --application-name $APP_NAME \
  --deployment-group-name $DEPLOY_GROUP \
  --revision revisionType=AppSpecContent,appSpecContent={content="$(cat appspec.yml)"}

# Monitor deployment
DEPLOYMENT_ID=$(aws deploy list-deployments \
  --application-name $APP_NAME \
  --query "deployments[0]" --output text)

aws deploy get-deployment --deployment-id $DEPLOYMENT_ID \
  --query "deploymentInfo.{Status:status,Overview:deploymentOverview}"
```

---

## Phase 3 — Deploy New Version (Green)

```bash
# Build and push v2 image
cd ../../project_5.1_single_docker_app
# Make a visible change to app.py (e.g. change version to 2.0.0)
sed -i 's/APP_VERSION = "1.0.0"/APP_VERSION = "2.0.0"/' app/app.py

docker build -t flask-api:2.0.0 .
docker tag flask-api:2.0.0 $ECR_URL:2.0.0
docker push $ECR_URL:2.0.0

# Register new task definition with v2 image
# Then trigger CodeDeploy deployment with new task definition ARN
```

---

## Phase 4 — Monitor Traffic Shift

```bash
# During deployment — watch traffic shift
watch -n 2 "curl -s $ALB_URL/info | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Version:', d['version'])\""

# Should show:
# Version: 1.0.0  (blue)
# Version: 1.0.0  (blue)
# ... traffic shifts ...
# Version: 2.0.0  (green)
# Version: 2.0.0  (green)
```

---

## Phase 5 — Test Rollback

```bash
# Stop the deployment (triggers rollback to blue)
aws deploy stop-deployment \
  --deployment-id $DEPLOYMENT_ID \
  --auto-rollback-enabled

# Traffic immediately returns to blue (v1)
curl $ALB_URL/info | python3 -m json.tool
# Version should be back to 1.0.0
```

---

## Phase 6 — Verification & Validation

### 6.1 AWS Console Verification
1. **CodeDeploy** → **Applications** → confirm app exists
2. **CodeDeploy** → **Deployment groups** → confirm blue/green config
3. **EC2** → **Target Groups** → confirm TWO target groups (blue + green)
4. **EC2** → **Load Balancers** → ALB → Listeners → confirm test listener on port 8080
5. **ECS** → **Services** → confirm service uses CODE_DEPLOY deployment controller

### 6.2 CLI Verification Commands
```bash
# Confirm CodeDeploy app and deployment group exist
aws deploy get-application --application-name $APP_NAME \
  --query "application.{Name:applicationName,Platform:computePlatform}"
# Expected: Name=..., Platform=ECS

aws deploy get-deployment-group \
  --application-name $APP_NAME \
  --deployment-group-name $DEPLOY_GROUP \
  --query "deploymentGroupInfo.{Name:deploymentGroupName,Style:deploymentStyle,BlueGreen:blueGreenDeploymentConfiguration}"
# Expected: deploymentType=BLUE_GREEN

# Confirm two target groups exist
aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName,'handson')].{Name:TargetGroupName,Port:Port}" \
  --output table
# Expected: two target groups (blue and green)

# Check latest deployment status
DEPLOYMENT_ID=$(aws deploy list-deployments \
  --application-name $APP_NAME \
  --query "deployments[0]" --output text)
aws deploy get-deployment --deployment-id $DEPLOYMENT_ID \
  --query "deploymentInfo.{Status:status,Overview:deploymentOverview}"
# Expected: status=Succeeded
```

### 6.3 Functional Tests
```bash
# Test 1: Current version is serving traffic
curl -s $ALB_URL/info | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('Version:', d['version'])"
# Expected: Version: 1.0.0 (blue)

# Test 2: Deploy v2 and watch traffic shift
# (trigger new deployment with v2 task definition)
# During deployment — poll every 2 seconds:
for i in $(seq 1 30); do
  VERSION=$(curl -s $ALB_URL/info 2>/dev/null | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('version','error'))" 2>/dev/null)
  echo "$(date +%H:%M:%S) - Version: $VERSION"
  sleep 2
done
# Expected: transitions from 1.0.0 → 2.0.0 with no errors

# Test 3: Rollback — stop deployment and verify traffic returns to blue
aws deploy stop-deployment \
  --deployment-id $DEPLOYMENT_ID \
  --auto-rollback-enabled
sleep 30
curl -s $ALB_URL/info | python3 -c \
  "import sys,json; print('After rollback:', json.load(sys.stdin)['version'])"
# Expected: Version: 1.0.0 (back to blue)

# Test 4: Test listener (port 8080) serves green during deployment
curl -s http://$ALB_DNS:8080/info | python3 -c \
  "import sys,json; print('Test listener version:', json.load(sys.stdin)['version'])"
# Expected: 2.0.0 (green) while production still serves 1.0.0
```

### 6.4 Logs & Monitoring Checks
```bash
# Check CodeDeploy deployment events
aws deploy list-deployment-instances \
  --deployment-id $DEPLOYMENT_ID \
  --query "instancesList"

# Check ECS events during deployment
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].events[:5].{Time:createdAt,Message:message}"
```

### 6.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| CodeDeploy deployment | status=Succeeded |
| Traffic during shift | No HTTP errors |
| After full shift | Version 2.0.0 serving |
| After rollback | Version 1.0.0 restored |
| Test listener (8080) | Shows green version |

### 6.6 Verification Checklist
- [ ] CodeDeploy app and deployment group created
- [ ] Two target groups exist (blue + green)
- [ ] ALB has test listener on port 8080
- [ ] ECS service uses CODE_DEPLOY deployment controller
- [ ] Blue deployment (v1) serving traffic initially
- [ ] Green deployment (v2) deployed successfully
- [ ] Traffic shifts from blue to green with no HTTP errors
- [ ] Rollback restores v1 traffic immediately
- [ ] Test listener shows green version during deployment

---

## Screenshots to Take
- [ ] CodeDeploy deployment group with blue/green config
- [ ] Two target groups (blue and green) in ALB
- [ ] Deployment in progress — both versions running
- [ ] Traffic shifted to green (v2 responding)
- [ ] Rollback triggered — traffic back to blue (v1)
- [ ] CodeDeploy deployment history
