# Project 05: Complete CI/CD Pipeline

## Architecture

```
GitHub (source)
    ↓
CodePipeline (orchestrator)
    ↓
CodeBuild (build + test + scan)
    ↓
ECR (container registry)
    ↓
Manual Approval (production gate)
    ↓
CodeDeploy → ECS Blue/Green
    ↓
CloudWatch (monitoring + rollback)
```

## Pipeline Stages

```
1. Source    → GitHub webhook triggers pipeline
2. Build     → CodeBuild: test, lint, build Docker, push to ECR
3. Staging   → Deploy to staging ECS cluster
4. Test      → Integration tests against staging
5. Approve   → Manual approval required for production
6. Production → Blue/green deployment to production ECS
```

## CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Complete CI/CD Pipeline

Parameters:
  GitHubOwner:
    Type: String
  GitHubRepo:
    Type: String
  GitHubBranch:
    Type: String
    Default: main
  ECSCluster:
    Type: String
  ECSService:
    Type: String
  ApprovalEmail:
    Type: String

Resources:
  # ── Artifact Store ────────────────────────────────────────────────────────
  ArtifactBucket:
    Type: AWS::S3::Bucket
    Properties:
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
      LifecycleConfiguration:
        Rules:
          - Id: cleanup-old-artifacts
            Status: Enabled
            ExpirationInDays: 30

  # ── ECR Repository ────────────────────────────────────────────────────────
  ECRRepository:
    Type: AWS::ECR::Repository
    Properties:
      RepositoryName: !Sub "${AWS::StackName}-app"
      ImageScanningConfiguration:
        ScanOnPush: true
      EncryptionConfiguration:
        EncryptionType: KMS
      LifecyclePolicy:
        LifecyclePolicyText: |
          {
            "rules": [{
              "rulePriority": 1,
              "description": "Keep last 20 images",
              "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 20
              },
              "action": {"type": "expire"}
            }]
          }

  # ── CodeBuild ─────────────────────────────────────────────────────────────
  BuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub "${AWS::StackName}-build"
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
        EnvironmentVariables:
          - Name: ECR_REPO
            Value: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/${ECRRepository}"
          - Name: AWS_DEFAULT_REGION
            Value: !Ref AWS::Region
      LogsConfig:
        CloudWatchLogs:
          Status: ENABLED
          GroupName: !Sub "/codebuild/${AWS::StackName}"

  IntegrationTestProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub "${AWS::StackName}-integration-tests"
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Source:
        Type: CODEPIPELINE
        BuildSpec: buildspec-integration.yml
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        Type: LINUX_CONTAINER
        Image: aws/codebuild/standard:7.0
        ComputeType: BUILD_GENERAL1_SMALL
        PrivilegedMode: false

  # ── Approval SNS Topic ────────────────────────────────────────────────────
  ApprovalTopic:
    Type: AWS::SNS::Topic
    Properties:
      Subscription:
        - Protocol: email
          Endpoint: !Ref ApprovalEmail

  # ── CodePipeline ──────────────────────────────────────────────────────────
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: !Sub "${AWS::StackName}-pipeline"
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
                Owner: !Ref GitHubOwner
                Repo: !Ref GitHubRepo
                Branch: !Ref GitHubBranch
                OAuthToken: !Sub "{{resolve:secretsmanager:github-token}}"
                PollForSourceChanges: false
              OutputArtifacts:
                - Name: SourceOutput

        - Name: Build
          Actions:
            - Name: BuildAndTest
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              Configuration:
                ProjectName: !Ref BuildProject
              InputArtifacts:
                - Name: SourceOutput
              OutputArtifacts:
                - Name: BuildOutput

        - Name: DeployStaging
          Actions:
            - Name: DeployToStaging
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CodeDeployToECS
                Version: '1'
              Configuration:
                ApplicationName: !Ref CodeDeployApp
                DeploymentGroupName: staging
                TaskDefinitionTemplateArtifact: BuildOutput
                AppSpecTemplateArtifact: BuildOutput
                TaskDefinitionTemplatePath: taskdef.json
                AppSpecTemplatePath: appspec.yaml
              InputArtifacts:
                - Name: BuildOutput

        - Name: IntegrationTest
          Actions:
            - Name: RunIntegrationTests
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: '1'
              Configuration:
                ProjectName: !Ref IntegrationTestProject
              InputArtifacts:
                - Name: SourceOutput

        - Name: ApproveProduction
          Actions:
            - Name: ManualApproval
              ActionTypeId:
                Category: Approval
                Owner: AWS
                Provider: Manual
                Version: '1'
              Configuration:
                NotificationArn: !Ref ApprovalTopic
                CustomData: "Review staging deployment before promoting to production"
                ExternalEntityLink: !Sub "https://staging.myapp.com"

        - Name: DeployProduction
          Actions:
            - Name: DeployToProduction
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CodeDeployToECS
                Version: '1'
              Configuration:
                ApplicationName: !Ref CodeDeployApp
                DeploymentGroupName: production
                TaskDefinitionTemplateArtifact: BuildOutput
                AppSpecTemplateArtifact: BuildOutput
              InputArtifacts:
                - Name: BuildOutput

  # ── CodeDeploy ────────────────────────────────────────────────────────────
  CodeDeployApp:
    Type: AWS::CodeDeploy::Application
    Properties:
      ApplicationName: !Sub "${AWS::StackName}-app"
      ComputePlatform: ECS

  ProductionDeploymentGroup:
    Type: AWS::CodeDeploy::DeploymentGroup
    Properties:
      ApplicationName: !Ref CodeDeployApp
      DeploymentGroupName: production
      ServiceRoleArn: !GetAtt CodeDeployRole.Arn
      DeploymentConfigName: CodeDeployDefault.ECSCanary10Percent5Minutes
      ECSServices:
        - ClusterName: !Ref ECSCluster
          ServiceName: !Ref ECSService
      LoadBalancerInfo:
        TargetGroupPairInfoList:
          - TargetGroups:
              - Name: blue-target-group
              - Name: green-target-group
            ProdTrafficRoute:
              ListenerArns:
                - !Ref ProductionListener
      AutoRollbackConfiguration:
        Enabled: true
        Events:
          - DEPLOYMENT_FAILURE
          - DEPLOYMENT_STOP_ON_ALARM
      AlarmConfiguration:
        Enabled: true
        Alarms:
          - Name: production-error-rate-alarm
          - Name: production-latency-alarm
```

## buildspec.yml

```yaml
version: 0.2

env:
  secrets-manager:
    SONAR_TOKEN: prod/sonar/token

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install pytest pytest-cov bandit safety --quiet

  pre_build:
    commands:
      - echo "Running security scan..."
      - bandit -r src/ -f json -o bandit-report.json || true
      - safety check --json > safety-report.json || true
      - echo "Running unit tests..."
      - pytest tests/unit/ --cov=src --cov-report=xml --cov-fail-under=80 -v
      - echo "Logging in to ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION |
          docker login --username AWS --password-stdin $ECR_REPO

  build:
    commands:
      - IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c1-8)
      - echo "Building image $ECR_REPO:$IMAGE_TAG"
      - docker build
          --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
          --build-arg GIT_COMMIT=$CODEBUILD_RESOLVED_SOURCE_VERSION
          -t $ECR_REPO:$IMAGE_TAG
          -t $ECR_REPO:latest .
      - docker push $ECR_REPO:$IMAGE_TAG
      - docker push $ECR_REPO:latest
      - echo "Scanning image for vulnerabilities..."
      - aws ecr wait image-scan-complete
          --repository-name $(echo $ECR_REPO | cut -d/ -f2)
          --image-id imageTag=$IMAGE_TAG
      - SCAN_FINDINGS=$(aws ecr describe-image-scan-findings
          --repository-name $(echo $ECR_REPO | cut -d/ -f2)
          --image-id imageTag=$IMAGE_TAG
          --query 'imageScanFindings.findingSeverityCounts.CRITICAL'
          --output text)
      - |
        if [ "$SCAN_FINDINGS" != "None" ] && [ "$SCAN_FINDINGS" -gt "0" ]; then
          echo "CRITICAL vulnerabilities found: $SCAN_FINDINGS"
          exit 1
        fi
      - echo "Generating deployment artifacts..."
      - sed -i "s|IMAGE_URI|$ECR_REPO:$IMAGE_TAG|g" taskdef.json
      - printf '[{"name":"app","imageUri":"%s"}]' $ECR_REPO:$IMAGE_TAG > imagedefinitions.json

  post_build:
    commands:
      - echo "Build completed successfully"

artifacts:
  files:
    - imagedefinitions.json
    - taskdef.json
    - appspec.yaml
  secondary-artifacts:
    TestReports:
      files:
        - coverage.xml
        - bandit-report.json

reports:
  UnitTestReport:
    files:
      - coverage.xml
    file-format: COBERTURAXML

cache:
  paths:
    - '/root/.cache/pip/**/*'
```

## Monitoring & Rollback

```bash
# CloudWatch alarm for automatic rollback
aws cloudwatch put-metric-alarm \
  --alarm-name production-error-rate-alarm \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/abc123 \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:prod-alerts

# Manual rollback
aws deploy stop-deployment \
  --deployment-id d-ABC123 \
  --auto-rollback-enabled

# View deployment history
aws deploy list-deployments \
  --application-name my-app \
  --deployment-group-name production \
  --include-only-statuses Succeeded Failed Stopped
```
