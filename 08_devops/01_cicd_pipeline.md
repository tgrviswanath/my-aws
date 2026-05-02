# CI/CD on AWS — CodePipeline, CodeBuild, CodeDeploy

## CI/CD Overview

```
Developer pushes code
        ↓
CodePipeline (orchestrator)
        ↓
CodeBuild (build + test)
        ↓
CodeDeploy (deploy to EC2/ECS/Lambda)
        ↓
Production
```

---

## AWS CodePipeline

CodePipeline orchestrates the CI/CD workflow. It connects source, build, test, and deploy stages.

### Pipeline Stages

```
Source Stage    → CodeCommit, GitHub, S3, ECR
Build Stage     → CodeBuild
Test Stage      → CodeBuild, Lambda, Device Farm
Deploy Stage    → CodeDeploy, ECS, CloudFormation, Elastic Beanstalk
Approval Stage  → Manual approval (SNS notification)
```

### Create Pipeline (CLI)

```bash
aws codepipeline create-pipeline \
  --pipeline '{
    "name": "my-app-pipeline",
    "roleArn": "arn:aws:iam::123456789:role/CodePipelineRole",
    "artifactStore": {
      "type": "S3",
      "location": "my-pipeline-artifacts"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [{
          "name": "Source",
          "actionTypeId": {
            "category": "Source",
            "owner": "ThirdParty",
            "provider": "GitHub",
            "version": "1"
          },
          "configuration": {
            "Owner": "my-org",
            "Repo": "my-app",
            "Branch": "main",
            "OAuthToken": "{{resolve:secretsmanager:github-token}}"
          },
          "outputArtifacts": [{"name": "SourceOutput"}]
        }]
      },
      {
        "name": "Build",
        "actions": [{
          "name": "Build",
          "actionTypeId": {
            "category": "Build",
            "owner": "AWS",
            "provider": "CodeBuild",
            "version": "1"
          },
          "configuration": {
            "ProjectName": "my-app-build"
          },
          "inputArtifacts": [{"name": "SourceOutput"}],
          "outputArtifacts": [{"name": "BuildOutput"}]
        }]
      },
      {
        "name": "Deploy",
        "actions": [{
          "name": "Deploy",
          "actionTypeId": {
            "category": "Deploy",
            "owner": "AWS",
            "provider": "CodeDeployToECS",
            "version": "1"
          },
          "configuration": {
            "ApplicationName": "my-app",
            "DeploymentGroupName": "production"
          },
          "inputArtifacts": [{"name": "BuildOutput"}]
        }]
      }
    ]
  }'
```

---

## AWS CodeBuild

CodeBuild compiles code, runs tests, and produces artifacts.

### buildspec.yml

```yaml
version: 0.2

env:
  variables:
    AWS_DEFAULT_REGION: us-east-1
  secrets-manager:
    SONAR_TOKEN: prod/sonar/token
  parameter-store:
    ECR_REPO: /myapp/ecr-repo

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install -r requirements.txt
      - pip install pytest pytest-cov

  pre_build:
    commands:
      - echo "Running tests..."
      - pytest tests/ --cov=src --cov-report=xml --cov-fail-under=80
      - echo "Logging in to ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | 
          docker login --username AWS --password-stdin $ECR_REPO

  build:
    commands:
      - echo "Building Docker image..."
      - IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c1-8)
      - docker build -t $ECR_REPO:$IMAGE_TAG -t $ECR_REPO:latest .
      - docker push $ECR_REPO:$IMAGE_TAG
      - docker push $ECR_REPO:latest
      - echo "Writing image definitions..."
      - printf '[{"name":"web","imageUri":"%s"}]' $ECR_REPO:$IMAGE_TAG > imagedefinitions.json

  post_build:
    commands:
      - echo "Build completed on $(date)"

artifacts:
  files:
    - imagedefinitions.json
    - appspec.yaml
    - taskdef.json

reports:
  pytest-reports:
    files:
      - coverage.xml
    file-format: COBERTURAXML

cache:
  paths:
    - '/root/.cache/pip/**/*'
```

### Create CodeBuild Project

```bash
aws codebuild create-project \
  --name my-app-build \
  --source '{
    "type": "CODEPIPELINE",
    "buildspec": "buildspec.yml"
  }' \
  --artifacts '{"type": "CODEPIPELINE"}' \
  --environment '{
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_MEDIUM",
    "privilegedMode": true,
    "environmentVariables": [
      {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
    ]
  }' \
  --service-role arn:aws:iam::123456789:role/CodeBuildRole \
  --vpc-config '{
    "vpcId": "vpc-12345678",
    "subnets": ["subnet-private-aaa"],
    "securityGroupIds": ["sg-codebuild-12345678"]
  }' \
  --logs-config '{
    "cloudWatchLogs": {
      "status": "ENABLED",
      "groupName": "/codebuild/my-app",
      "streamName": "build"
    }
  }'
```

---

## AWS CodeDeploy

CodeDeploy automates application deployments to EC2, ECS, Lambda, and on-premises.

### Deployment Strategies

#### Blue/Green (ECS)

```
Blue (current): 100% traffic
Green (new):    0% traffic

Deploy:
1. Launch new task set (green)
2. Health checks pass
3. Shift traffic: 10% → 50% → 100% (configurable)
4. Terminate blue after stabilization
```

#### Canary (Lambda)

```
v1: 90% traffic
v2: 10% traffic (canary)

Monitor for errors/alarms
→ Success: shift 100% to v2
→ Failure: rollback to v1
```

#### Linear (Lambda)

```
v1: 100% → 90% → 80% → ... → 0%
v2:   0% → 10% → 20% → ... → 100%
(shift 10% every 10 minutes)
```

### appspec.yaml (ECS)

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

### appspec.yaml (Lambda)

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

### Create Deployment Group

```bash
aws deploy create-deployment-group \
  --application-name my-app \
  --deployment-group-name production \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
  --service-role-arn arn:aws:iam::123456789:role/CodeDeployRole \
  --ecs-services '[{
    "serviceName": "web-service",
    "clusterName": "production"
  }]' \
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
```

---

## Complete CloudFormation Pipeline

```yaml
AWSTemplateFormatVersion: '2010-09-09'

Resources:
  ArtifactBucket:
    Type: AWS::S3::Bucket
    Properties:
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms

  CodeBuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: my-app-build
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Source:
        Type: CODEPIPELINE
        BuildSpec: buildspec.yml
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        Type: LINUX_CONTAINER
        Image: aws/codebuild/standard:7.0
        ComputeType: BUILD_GENERAL1_MEDIUM
        PrivilegedMode: true

  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: my-app-pipeline
      RoleArn: !GetAtt PipelineRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactBucket
      Stages:
        - Name: Source
          Actions:
            - Name: Source
              ActionTypeId:
                Category: Source
                Owner: ThirdParty
                Provider: GitHub
                Version: '1'
              Configuration:
                Owner: my-org
                Repo: my-app
                Branch: main
                OAuthToken: !Sub "{{resolve:secretsmanager:github-token}}"
              OutputArtifacts:
                - Name: SourceOutput
        - Name: Build
          Actions:
            - Name: Build
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              Configuration:
                ProjectName: !Ref CodeBuildProject
              InputArtifacts:
                - Name: SourceOutput
              OutputArtifacts:
                - Name: BuildOutput
        - Name: Approve
          Actions:
            - Name: ManualApproval
              ActionTypeId:
                Category: Approval
                Owner: AWS
                Provider: Manual
                Version: '1'
              Configuration:
                NotificationArn: !Ref ApprovalTopic
                CustomData: "Review build artifacts before deploying to production"
        - Name: Deploy
          Actions:
            - Name: Deploy
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CodeDeployToECS
                Version: '1'
              Configuration:
                ApplicationName: my-app
                DeploymentGroupName: production
                TaskDefinitionTemplateArtifact: BuildOutput
                AppSpecTemplateArtifact: BuildOutput
              InputArtifacts:
                - Name: BuildOutput
```

---

## Interview Q&A

### Q1: What is the difference between CodePipeline, CodeBuild, and CodeDeploy?
**CodePipeline**: Orchestrator. Defines the workflow stages (source → build → test → deploy). Triggers and coordinates the other services.
**CodeBuild**: Build server. Compiles code, runs tests, creates artifacts (Docker images, zip files). Fully managed, no servers to maintain.
**CodeDeploy**: Deployment automation. Deploys artifacts to EC2, ECS, Lambda, or on-premises. Handles deployment strategies (blue/green, canary, rolling).

### Q2: What is the difference between blue/green and canary deployments?
**Blue/Green**: Two identical environments. Switch all traffic at once (or gradually). Easy rollback — just switch back. Higher cost (double infrastructure temporarily).
**Canary**: Route small percentage (e.g., 10%) to new version. Monitor for errors. Gradually increase traffic. Rollback by routing 100% back to old version. Lower risk than full deployment, lower cost than full blue/green.

### Q3: How do you implement automatic rollback in CodeDeploy?
Configure `autoRollbackConfiguration` with events: `DEPLOYMENT_FAILURE` (rollback if deployment fails), `DEPLOYMENT_STOP_ON_ALARM` (rollback if CloudWatch alarm triggers). Set up CloudWatch alarms on error rate and latency. CodeDeploy monitors these alarms during deployment and automatically rolls back if they breach thresholds.

### Q4: How do you handle database migrations in a CI/CD pipeline?
1. Run migrations as a CodeBuild step before deployment
2. Use backward-compatible migrations (add columns, don't rename/delete)
3. Deploy in phases: (1) deploy code that works with old AND new schema, (2) run migration, (3) deploy code that uses new schema only
4. Use tools like Flyway or Liquibase for versioned migrations
5. Test migrations on a copy of production data in staging
6. Have a rollback migration script ready

### Q5: How do you secure a CI/CD pipeline?
1. Least privilege IAM roles for CodePipeline, CodeBuild, CodeDeploy
2. Secrets in Secrets Manager, not environment variables
3. VPC for CodeBuild (access private resources, no internet)
4. Artifact bucket encryption + versioning
5. Manual approval gate before production deployment
6. Code signing for Lambda deployments
7. SAST/DAST tools in build stage (SonarQube, OWASP ZAP)
8. Container image scanning (ECR scan on push)
9. Audit trail via CloudTrail
