# Project 5.5 — Blue-Green Deployment on ECS with CodeDeploy

## Overview

Implement blue-green deployments for an ECS Fargate service using AWS CodeDeploy. Deploy a v2 image as a new task definition revision, switch traffic from the blue (v1) to green (v2) target group, and configure automatic rollback triggered by a CloudWatch alarm.

---

## Prerequisites Check

```bash
# Verify AWS CLI
aws --version

# Verify credentials
aws sts get-caller-identity

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# This project builds on project_5.4 resources
# Verify the ECS cluster exists
aws ecs describe-clusters \
  --clusters my-fargate-cluster \
  --region $AWS_REGION \
  --query 'clusters[0].status' \
  --output text
# Expected: ACTIVE

# Verify ALB exists
aws elbv2 describe-load-balancers \
  --names my-fargate-alb \
  --region $AWS_REGION \
  --query 'LoadBalancers[0].State.Code' \
  --output text 2>/dev/null || echo "Need to create ALB first (see project_5.4)"
```

**Required IAM permissions:**
- `ecs:UpdateService`, `ecs:RegisterTaskDefinition`
- `codedeploy:CreateApplication`, `codedeploy:CreateDeploymentGroup`
- `codedeploy:CreateDeployment`, `codedeploy:GetDeployment`
- `elasticloadbalancing:*`
- `cloudwatch:PutMetricAlarm`
- `iam:CreateRole`, `iam:AttachRolePolicy`

---

## Decision Point 1: Blue-Green vs Rolling Update

| Factor | Blue-Green | Rolling Update |
|--------|-----------|---------------|
| Zero downtime | ✅ Yes — instant traffic switch | ✅ Yes — gradual |
| Rollback speed | ✅ Instant (re-route to blue) | ❌ Slow (re-deploy old version) |
| Rollback trigger | CloudWatch alarm (automatic) | Manual intervention |
| Resource cost during deploy | 2× tasks (blue + green running) | Configurable (up to 200%) |
| Complexity | Higher (CodeDeploy integration) | Lower |
| Traffic control | Fine-grained % shifting | Binary — old or new |
| Best for | Production, ✅ zero-downtime critical | Dev/staging, gradual rollouts |

**Decision:** Use **blue-green** for production ECS services where rollback speed and traffic control matter.

---

## 1. Set Up Variables

```bash
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_NAME="my-fargate-cluster"
SERVICE_NAME="my-fargate-service"
ECR_REPO="flask-app"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"

# Get existing ALB and target group info from project_5.4
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names my-fargate-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text --region $AWS_REGION)

LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query 'Listeners[0].ListenerArn' \
  --output text --region $AWS_REGION)

TG_BLUE_ARN=$(aws elbv2 describe-target-groups \
  --names my-fargate-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text --region $AWS_REGION)

VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text --region $AWS_REGION)

echo "ALB: $ALB_ARN"
echo "Listener: $LISTENER_ARN"
echo "Blue TG: $TG_BLUE_ARN"
```

---

## 2. Create the Green Target Group

```bash
# Create the "green" target group for CodeDeploy to shift traffic to
TG_GREEN_ARN=$(aws elbv2 create-target-group \
  --name "my-fargate-tg-green" \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --region $AWS_REGION \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "Green TG: $TG_GREEN_ARN"

# Add test listener on port 8080 for testing green before traffic shift
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 8080 \
  --default-actions Type=forward,TargetGroupArn=$TG_GREEN_ARN \
  --region $AWS_REGION
```

---

## 3. Create CodeDeploy IAM Role

```bash
# Create role for CodeDeploy
aws iam create-role \
  --role-name CodeDeployECSRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "codedeploy.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "Role may already exist"

# Attach the required policy
aws iam attach-role-policy \
  --role-name CodeDeployECSRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS

CODEDEPLOY_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/CodeDeployECSRole"
echo "CodeDeploy Role: $CODEDEPLOY_ROLE_ARN"
```

---

## 4. Create CodeDeploy Application and Deployment Group

```bash
# Create CodeDeploy application for ECS
aws deploy create-application \
  --application-name "my-fargate-app" \
  --compute-platform ECS \
  --region $AWS_REGION

# Create deployment group
aws deploy create-deployment-group \
  --application-name "my-fargate-app" \
  --deployment-group-name "my-fargate-dg" \
  --deployment-config-name CodeDeployDefault.ECSAllAtOnce \
  --service-role-arn $CODEDEPLOY_ROLE_ARN \
  --ecs-services clusterName=$CLUSTER_NAME,serviceName=$SERVICE_NAME \
  --load-balancer-info "targetGroupPairInfoList=[{
    targetGroups=[{name=my-fargate-tg},{name=my-fargate-tg-green}],
    prodTrafficRoute={listenerArns=[\"$LISTENER_ARN\"]}
  }]" \
  --deployment-style deploymentType=BLUE_GREEN,deploymentOption=WITH_TRAFFIC_CONTROL \
  --blue-green-deployment-configuration "{
    \"terminateBlueInstancesOnDeploymentSuccess\": {
      \"action\": \"TERMINATE\",
      \"terminationWaitTimeInMinutes\": 5
    },
    \"deploymentReadyOption\": {
      \"actionOnTimeout\": \"CONTINUE_DEPLOYMENT\",
      \"waitTimeInMinutes\": 0
    }
  }" \
  --region $AWS_REGION

echo "CodeDeploy deployment group created"
```

---

## 5. Update ECS Service for Blue-Green

### 5A. AWS Console: ECS Console → Update Service to Use CodeDeploy Blue/Green

1. Go to ECS → Clusters → `my-fargate-cluster` → Services
2. Click on `my-fargate-service` → **Update service**
3. Under **Deployment options**:
   - Deployment type: change to **Blue/green deployment (powered by AWS CodeDeploy)**
4. Select the CodeDeploy application and deployment group created above
5. Click **Update**

### 5B. AWS CLI: Update Service

```bash
# Update the ECS service to use CODE_DEPLOY deployment controller
# Note: This requires recreating the service — update in place isn't always supported for controller change
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --deployment-controller type=CODE_DEPLOY \
  --region $AWS_REGION 2>/dev/null || echo "May need to delete and recreate service for controller change"

# If recreating service, use:
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition "my-fargate-app:1" \
  --desired-count 2 \
  --launch-type FARGATE \
  --deployment-controller type=CODE_DEPLOY \
  --network-configuration "awsvpcConfiguration={
    subnets=[$(aws ec2 describe-subnets \
      --filters "Name=defaultForAz,Values=true" \
      --query 'Subnets[0:2].SubnetId' \
      --output text --region $AWS_REGION | tr '\t' ',')],
    securityGroups=[$(aws ec2 describe-security-groups \
      --filters "Name=group-name,Values=my-fargate-ecs-sg" \
      --query 'SecurityGroups[0].GroupId' \
      --output text --region $AWS_REGION)],
    assignPublicIp=ENABLED
  }" \
  --load-balancers "targetGroupArn=$TG_BLUE_ARN,containerName=app,containerPort=8080" \
  --region $AWS_REGION
```

---

## 6. Register v2 Task Definition

```bash
# Push v2 image to ECR (tag existing image as 2.0.0 for demo)
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Tag and push v2 (using same image for demo, in real scenario rebuild with changes)
docker pull $ECR_URI:1.0.0
docker tag $ECR_URI:1.0.0 $ECR_URI:2.0.0
docker push $ECR_URI:2.0.0

# Register new task definition revision (v2)
aws ecs register-task-definition \
  --family "my-fargate-app" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "256" \
  --memory "512" \
  --execution-role-arn "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole" \
  --container-definitions "[
    {
      \"name\": \"app\",
      \"image\": \"$ECR_URI:2.0.0\",
      \"portMappings\": [{\"containerPort\": 8080, \"protocol\": \"tcp\"}],
      \"essential\": true,
      \"environment\": [{\"name\": \"APP_VERSION\", \"value\": \"2.0.0\"}],
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/my-fargate-app\",
          \"awslogs-region\": \"$AWS_REGION\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"healthCheck\": {
        \"command\": [\"CMD-SHELL\", \"curl -f http://localhost:8080/health || exit 1\"],
        \"interval\": 30,
        \"timeout\": 5,
        \"retries\": 3,
        \"startPeriod\": 15
      }
    }
  ]" \
  --region $AWS_REGION

TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition my-fargate-app \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text --region $AWS_REGION)

echo "New task definition: $TASK_DEF_ARN"
```

---

## 7. Create a CloudWatch Alarm for Auto-Rollback

```bash
# Alarm triggers rollback if error rate exceeds 5%
aws cloudwatch put-metric-alarm \
  --alarm-name "fargate-app-5xx-alarm" \
  --alarm-description "Triggers CodeDeploy rollback on 5xx errors" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --dimensions \
    Name=LoadBalancer,Value=$(echo $ALB_ARN | awk -F':loadbalancer/' '{print $2}') \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --region $AWS_REGION

echo "CloudWatch alarm created: fargate-app-5xx-alarm"
```

---

## 8. Trigger the Blue-Green Deployment

```bash
# Create appspec.json
cat > /tmp/appspec.json << EOF
{
  "version": 0.0,
  "Resources": [
    {
      "TargetService": {
        "Type": "AWS::ECS::Service",
        "Properties": {
          "TaskDefinition": "$TASK_DEF_ARN",
          "LoadBalancerInfo": {
            "ContainerName": "app",
            "ContainerPort": 8080
          }
        }
      }
    }
  ]
}
EOF

# Upload appspec to S3 (CodeDeploy needs it there)
S3_BUCKET="$AWS_ACCOUNT_ID-codedeploy-artifacts"
aws s3 mb s3://$S3_BUCKET --region $AWS_REGION 2>/dev/null || true
aws s3 cp /tmp/appspec.json s3://$S3_BUCKET/appspec.json

# Trigger deployment
DEPLOYMENT_ID=$(aws deploy create-deployment \
  --application-name "my-fargate-app" \
  --deployment-group-name "my-fargate-dg" \
  --revision revisionType=S3,s3Location="{bucket=$S3_BUCKET,key=appspec.json,bundleType=JSON}" \
  --description "Deploy v2.0.0" \
  --region $AWS_REGION \
  --query 'deploymentId' \
  --output text)

echo "Deployment started: $DEPLOYMENT_ID"

# Monitor deployment
aws deploy get-deployment \
  --deployment-id $DEPLOYMENT_ID \
  --region $AWS_REGION \
  --query 'deploymentInfo.{Status:status,Created:createTime}' \
  --output table
```

---

## 9. Monitor Traffic Shift and Verify

```bash
# Watch deployment status
watch -n 5 "aws deploy get-deployment \
  --deployment-id $DEPLOYMENT_ID \
  --region $AWS_REGION \
  --query 'deploymentInfo.{Status:status,Overview:deploymentOverview}'"

# Check both task definition revisions are running
aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $AWS_REGION

# After traffic shifts to green, verify ALB is routing to v2
curl -s http://$ALB_DNS/ | grep version
# Expected: "version": "2.0.0"

# Test green environment on port 8080 (test listener) before full shift
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text --region $AWS_REGION)

curl -s http://$ALB_DNS:8080/
```

---

## 10. Cleanup

```bash
# Delete CodeDeploy resources
aws deploy delete-deployment-group \
  --application-name my-fargate-app \
  --deployment-group-name my-fargate-dg \
  --region $AWS_REGION

aws deploy delete-application \
  --application-name my-fargate-app \
  --region $AWS_REGION

# Delete CloudWatch alarm
aws cloudwatch delete-alarms \
  --alarm-names fargate-app-5xx-alarm \
  --region $AWS_REGION

# Delete green target group and test listener
TEST_LISTENER=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query "Listeners[?Port==\`8080\`].ListenerArn" \
  --output text --region $AWS_REGION)
aws elbv2 delete-listener --listener-arn $TEST_LISTENER --region $AWS_REGION
aws elbv2 delete-target-group --target-group-arn $TG_GREEN_ARN --region $AWS_REGION

# Delete S3 artifacts bucket
aws s3 rm s3://$S3_BUCKET --recursive
aws s3 rb s3://$S3_BUCKET

# ECS service and cluster cleanup (see project_5.4 cleanup)
```

---

## Troubleshooting

**Deployment stuck at "Waiting for tasks to start":**
```bash
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME \
  --query 'services[0].events[0:3]' --region $AWS_REGION
```

**CodeDeploy shows "FAILED: The deployment group does not have a valid service role":**
- Verify `CodeDeployECSRole` has `AWSCodeDeployRoleForECS` policy attached
- Check the role trust policy allows `codedeploy.amazonaws.com`

**Rollback not triggering despite 5xx errors:**
- Ensure the alarm is linked to the deployment group's auto-rollback config
- Add alarm to deployment group:
```bash
aws deploy update-deployment-group \
  --application-name my-fargate-app \
  --current-deployment-group-name my-fargate-dg \
  --alarm-configuration enabled=true,alarms=[{name=fargate-app-5xx-alarm}] \
  --auto-rollback-configuration enabled=true,events=[DEPLOYMENT_FAILURE,ALARM_STATE] \
  --region $AWS_REGION
```

---

## Expected Outcome

After completing this guide:

- ✅ Both blue (v1) and green (v2) task definitions registered
- ✅ CodeDeploy application and deployment group configured for ECS blue-green
- ✅ Traffic shifted from blue to green without downtime
- ✅ CloudWatch alarm configured for automatic rollback on 5xx errors
- ✅ Old (blue) tasks drain and terminate after `terminationWaitTimeInMinutes`
- ✅ ALB serving traffic from v2 tasks post-deployment
