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

## Screenshots to Take
- [ ] CodeDeploy deployment group with blue/green config
- [ ] Two target groups (blue and green) in ALB
- [ ] Deployment in progress — both versions running
- [ ] Traffic shifted to green (v2 responding)
- [ ] Rollback triggered — traffic back to blue (v1)
- [ ] CodeDeploy deployment history
