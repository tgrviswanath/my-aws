# AWS Deployment Strategies — Blue/Green, Canary & Rolling

## Strategy Comparison

| Strategy | Downtime | Risk | Rollback | Cost |
|----------|----------|------|----------|------|
| In-place (Recreate) | Yes | High | Redeploy | Low |
| Rolling Update | No | Medium | Slow | Low |
| Blue/Green | No | Low | Instant | High (2x infra) |
| Canary | No | Low | Fast | Medium |
| A/B Testing | No | Low | Fast | Medium |

---

## Blue/Green — CodeDeploy + ECS

```
Blue (current):  ECS Service v1 → Target Group Blue  → ALB (100% traffic)
Green (new):     ECS Service v2 → Target Group Green → ALB (0% traffic)

Deploy:
1. Launch new task set (green) with v2
2. Health checks pass on green
3. Shift traffic: 10% → 50% → 100% (configurable)
4. Terminate blue after stabilization
Rollback: shift 100% back to blue (seconds)
```

### CodeDeploy Blue/Green for ECS

```bash
# Create CodeDeploy application
aws deploy create-application \
  --application-name myapp \
  --compute-platform ECS

# Create deployment group
aws deploy create-deployment-group \
  --application-name myapp \
  --deployment-group-name production \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
  --service-role-arn arn:aws:iam::123456789:role/CodeDeployRole \
  --ecs-services clusterName=production,serviceName=web-service \
  --load-balancer-info '{
    "targetGroupPairInfoList": [{
      "targetGroups": [
        {"name": "blue-tg"},
        {"name": "green-tg"}
      ],
      "prodTrafficRoute": {
        "listenerArns": ["arn:aws:elasticloadbalancing:..."]
      },
      "testTrafficRoute": {
        "listenerArns": ["arn:aws:elasticloadbalancing:...:listener/test"]
      }
    }]
  }' \
  --auto-rollback-configuration '{
    "enabled": true,
    "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }' \
  --alarm-configuration '{
    "enabled": true,
    "alarms": [{"name": "high-error-rate"}, {"name": "high-latency"}]
  }'

# Trigger deployment
aws deploy create-deployment \
  --application-name myapp \
  --deployment-group-name production \
  --revision '{
    "revisionType": "AppSpecContent",
    "appSpecContent": {
      "content": "{\"version\":0,\"Resources\":[{\"TargetService\":{\"Type\":\"AWS::ECS::Service\",\"Properties\":{\"TaskDefinition\":\"arn:aws:ecs:...\",\"LoadBalancerInfo\":{\"ContainerName\":\"web\",\"ContainerPort\":8080}}}}]}"
    }
  }'

# Manual rollback
aws deploy stop-deployment \
  --deployment-id d-ABC123 \
  --auto-rollback-enabled
```

### appspec.yaml (ECS Blue/Green)

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: web
          ContainerPort: 8080
        PlatformVersion: LATEST

Hooks:
  - BeforeInstall: "arn:aws:lambda:us-east-1:123456789:function:pre-deploy-check"
  - AfterInstall: "arn:aws:lambda:us-east-1:123456789:function:smoke-test"
  - AfterAllowTestTraffic: "arn:aws:lambda:us-east-1:123456789:function:integration-test"
  - BeforeAllowTraffic: "arn:aws:lambda:us-east-1:123456789:function:final-check"
  - AfterAllowTraffic: "arn:aws:lambda:us-east-1:123456789:function:post-deploy-verify"
```

---

## Canary — Lambda Traffic Shifting

```
Lambda Alias: prod
  → v5 (90% traffic)
  → v6 (10% canary)

Monitor CloudWatch alarms
→ Success: shift 100% to v6
→ Failure: rollback to v5 automatically
```

### appspec.yaml (Lambda Canary)

```yaml
version: 0.0
Resources:
  - MyLambdaFunction:
      Type: AWS::Lambda::Function
      Properties:
        Name: my-function
        Alias: prod
        CurrentVersion: 5
        TargetVersion: 6

Hooks:
  - BeforeAllowTraffic: "arn:aws:lambda:us-east-1:123456789:function:pre-traffic-check"
  - AfterAllowTraffic: "arn:aws:lambda:us-east-1:123456789:function:post-traffic-check"
```

```bash
# Deployment configs for Lambda
# CodeDeployDefault.LambdaCanary10Percent5Minutes  → 10% for 5 min, then 100%
# CodeDeployDefault.LambdaCanary10Percent30Minutes → 10% for 30 min, then 100%
# CodeDeployDefault.LambdaLinear10PercentEvery1Minute → +10% every minute
# CodeDeployDefault.LambdaAllAtOnce               → all at once (no canary)

aws deploy create-deployment-group \
  --application-name my-lambda-app \
  --deployment-group-name production \
  --deployment-config-name CodeDeployDefault.LambdaCanary10Percent5Minutes \
  --service-role-arn arn:aws:iam::123456789:role/CodeDeployRole \
  --alarm-configuration '{
    "enabled": true,
    "alarms": [{"name": "lambda-error-rate"}, {"name": "lambda-throttles"}]
  }' \
  --auto-rollback-configuration '{
    "enabled": true,
    "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }'
```

---

## Rolling Update — ECS

```bash
# ECS rolling update (built-in, no CodeDeploy needed)
aws ecs update-service \
  --cluster production \
  --service web-service \
  --task-definition web-app:NEW_VERSION \
  --deployment-configuration '{
    "maximumPercent": 200,
    "minimumHealthyPercent": 100,
    "deploymentCircuitBreaker": {
      "enable": true,
      "rollback": true
    }
  }' \
  --force-new-deployment

# Watch rollout
aws ecs describe-services \
  --cluster production \
  --services web-service \
  --query 'services[0].deployments'
```

---

## Rolling Update — Kubernetes (EKS)

```yaml
# deployment.yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Allow 1 extra pod during update
      maxUnavailable: 0  # Never go below desired count
```

```bash
# Trigger rolling update
kubectl set image deployment/web-app \
  web=123456789.dkr.ecr.us-east-1.amazonaws.com/web-app:v2.0 \
  --namespace production

# Watch progress
kubectl rollout status deployment/web-app --namespace production

# Rollback
kubectl rollout undo deployment/web-app --namespace production

# Rollback to specific revision
kubectl rollout history deployment/web-app --namespace production
kubectl rollout undo deployment/web-app --to-revision=3 --namespace production
```

---

## Feature Flags with AWS AppConfig

```bash
# Create AppConfig application
aws appconfig create-application \
  --name myapp \
  --description "Feature flags for myapp"

# Create environment
aws appconfig create-environment \
  --application-id $APP_ID \
  --name production

# Create feature flag configuration
aws appconfig create-configuration-profile \
  --application-id $APP_ID \
  --name feature-flags \
  --location-uri hosted \
  --type AWS.AppConfig.FeatureFlags

# Create hosted configuration version
aws appconfig create-hosted-configuration-version \
  --application-id $APP_ID \
  --configuration-profile-id $PROFILE_ID \
  --content-type application/json \
  --content '{
    "flags": {
      "new-checkout-ui": {
        "name": "New Checkout UI",
        "attributes": {
          "rollout_percentage": {"constraints": {"type": "number", "minimum": 0, "maximum": 100}}
        }
      }
    },
    "values": {
      "new-checkout-ui": {
        "enabled": true,
        "rollout_percentage": 10
      }
    },
    "version": "1"
  }'

# Deploy configuration
aws appconfig start-deployment \
  --application-id $APP_ID \
  --environment-id $ENV_ID \
  --deployment-strategy-id $STRATEGY_ID \
  --configuration-profile-id $PROFILE_ID \
  --configuration-version 1
```

```python
# Python — check feature flag
import boto3
import json

appconfig = boto3.client('appconfigdata')

# Start session
session = appconfig.start_configuration_session(
    ApplicationIdentifier='myapp',
    EnvironmentIdentifier='production',
    ConfigurationProfileIdentifier='feature-flags',
    RequiredMinimumPollIntervalInSeconds=30
)

# Get configuration
response = appconfig.get_latest_configuration(
    ConfigurationToken=session['InitialConfigurationToken']
)
flags = json.loads(response['Configuration'].read())

def is_feature_enabled(flag_name: str, user_id: str = None) -> bool:
    flag = flags.get('values', {}).get(flag_name, {})
    if not flag.get('enabled'):
        return False
    rollout = flag.get('rollout_percentage', 100)
    if user_id:
        # Deterministic rollout based on user ID
        import hashlib
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
        return hash_val < rollout
    return True
```

---

## CI/CD Pipeline with Blue/Green

```yaml
# buildspec.yml — CodeBuild
version: 0.2
phases:
  pre_build:
    commands:
      - aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
      - IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c1-8)
  build:
    commands:
      - docker build -t $ECR_REPO:$IMAGE_TAG .
      - docker push $ECR_REPO:$IMAGE_TAG
      - sed -i "s|IMAGE_URI|$ECR_REPO:$IMAGE_TAG|g" taskdef.json
      - printf '[{"name":"web","imageUri":"%s"}]' $ECR_REPO:$IMAGE_TAG > imagedefinitions.json
artifacts:
  files: [imagedefinitions.json, taskdef.json, appspec.yaml]
```

---

## Interview Q&A

### Q1: What is the difference between blue/green and canary deployments?
**Blue/Green**: Two identical environments. Switch all traffic at once (or gradually). Easy instant rollback — just switch back. Higher cost (double infrastructure temporarily). Best for: major releases, database schema changes, when you need instant rollback.
**Canary**: Route small percentage (5-10%) to new version. Monitor metrics. Gradually increase. Rollback by routing 100% back. Lower risk, lower cost than full blue/green. Best for: gradual rollouts, risk-averse releases, A/B testing.

### Q2: How does CodeDeploy automatic rollback work?
Configure `autoRollbackConfiguration` with events: `DEPLOYMENT_FAILURE` (rollback if deployment fails health checks), `DEPLOYMENT_STOP_ON_ALARM` (rollback if CloudWatch alarm triggers during deployment). Set up alarms on error rate and latency. CodeDeploy monitors these during the deployment window and automatically rolls back if they breach thresholds. For Lambda canary, the pre/post traffic hooks can also trigger rollback by returning a non-zero exit code.

### Q3: How do you implement zero-downtime deployments for ECS?
Use CodeDeploy blue/green: (1) Launch new task set (green), (2) Register with test listener, (3) Run smoke tests via AfterInstall hook, (4) Shift traffic gradually (canary config), (5) Monitor alarms, (6) Terminate old task set after stabilization. Key settings: `maximumPercent=200, minimumHealthyPercent=100` ensures new tasks launch before old ones terminate. Connection draining (deregistration delay) handles in-flight requests.

### Q4: What is a deployment circuit breaker in ECS?
ECS deployment circuit breaker monitors the health of new tasks during a rolling deployment. If a configurable number of tasks fail to reach a steady state (pass health checks), the circuit breaker triggers and rolls back to the previous task definition automatically. Enable with `deploymentCircuitBreaker: {enable: true, rollback: true}`. Prevents a bad deployment from taking down your entire service.
