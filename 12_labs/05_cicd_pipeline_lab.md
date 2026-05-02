# Lab 05 — Build a Complete CI/CD Pipeline with CodePipeline

## Objective
Build a full CI/CD pipeline: GitHub → CodePipeline → CodeBuild (test + Docker build) → ECR → ECS blue/green deployment.

## Prerequisites
- AWS CLI configured
- Docker installed locally
- GitHub account with a sample repo
- Estimated time: 60 minutes
- Estimated cost: ~$0.50 (CodeBuild minutes + ECR storage)

---

## Step 1: Create Supporting Infrastructure

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
APP_NAME="lab05-app"
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME"

# Create ECR repository
aws ecr create-repository \
  --repository-name $APP_NAME \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  --region $REGION

echo "ECR: $ECR_REPO"

# Create S3 bucket for artifacts
ARTIFACT_BUCKET="$ACCOUNT_ID-$APP_NAME-artifacts"
aws s3api create-bucket \
  --bucket $ARTIFACT_BUCKET \
  --region $REGION

aws s3api put-bucket-versioning \
  --bucket $ARTIFACT_BUCKET \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket $ARTIFACT_BUCKET \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

echo "Artifact bucket: $ARTIFACT_BUCKET"
```

---

## Step 2: Create IAM Roles

```bash
# CodeBuild role
aws iam create-role \
  --role-name lab05-codebuild-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "codebuild.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name lab05-codebuild-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam put-role-policy \
  --role-name lab05-codebuild-role \
  --policy-name CodeBuildPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"logs:*\", \"s3:*\", \"ecr:*\"],
        \"Resource\": \"*\"
      }
    ]
  }"

# CodePipeline role
aws iam create-role \
  --role-name lab05-codepipeline-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "codepipeline.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name lab05-codepipeline-role \
  --policy-arn arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess

aws iam put-role-policy \
  --role-name lab05-codepipeline-role \
  --policy-name PipelinePolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:*\", \"codebuild:*\", \"ecs:*\", \"iam:PassRole\"],
      \"Resource\": \"*\"
    }]
  }"

echo "IAM roles created"
sleep 10
```

---

## Step 3: Create buildspec.yml

```bash
# Create sample app with buildspec
mkdir -p /tmp/lab05-app
cat > /tmp/lab05-app/buildspec.yml << 'EOF'
version: 0.2

env:
  variables:
    AWS_DEFAULT_REGION: us-east-1

phases:
  install:
    runtime-versions:
      nodejs: 18
    commands:
      - echo "Installing dependencies..."
      - npm ci --quiet

  pre_build:
    commands:
      - echo "Running tests..."
      - npm test
      - echo "Logging in to ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION |
          docker login --username AWS --password-stdin $ECR_REPO
      - IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c1-8)
      - echo "Building image tag $IMAGE_TAG"

  build:
    commands:
      - echo "Building Docker image..."
      - docker build -t $ECR_REPO:$IMAGE_TAG -t $ECR_REPO:latest .
      - echo "Scanning image..."
      - docker push $ECR_REPO:$IMAGE_TAG
      - docker push $ECR_REPO:latest
      - echo "Writing image definitions..."
      - printf '[{"name":"app","imageUri":"%s"}]' $ECR_REPO:$IMAGE_TAG > imagedefinitions.json

  post_build:
    commands:
      - echo "Build completed on $(date)"
      - echo "Image: $ECR_REPO:$IMAGE_TAG"

artifacts:
  files:
    - imagedefinitions.json
    - appspec.yaml
    - taskdef.json

cache:
  paths:
    - node_modules/**/*
EOF

# Simple Dockerfile
cat > /tmp/lab05-app/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O- http://localhost:8080/health || exit 1
USER node
CMD ["node", "server.js"]
EOF

# Simple Node.js server
cat > /tmp/lab05-app/server.js << 'EOF'
const http = require('http');
const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, {'Content-Type': 'application/json'});
    res.end(JSON.stringify({status: 'healthy', version: process.env.APP_VERSION || '1.0'}));
  } else {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    res.end('Hello from Lab 05!\n');
  }
});
server.listen(8080, () => console.log('Server running on port 8080'));
EOF

cat > /tmp/lab05-app/package.json << 'EOF'
{
  "name": "lab05-app",
  "version": "1.0.0",
  "scripts": {
    "start": "node server.js",
    "test": "echo 'Tests passed'"
  }
}
EOF

echo "App files created in /tmp/lab05-app"
```

---

## Step 4: Create CodeBuild Project

```bash
CODEBUILD_ROLE_ARN=$(aws iam get-role \
  --role-name lab05-codebuild-role \
  --query 'Role.Arn' --output tsv)

aws codebuild create-project \
  --name lab05-build \
  --source '{
    "type": "CODEPIPELINE",
    "buildspec": "buildspec.yml"
  }' \
  --artifacts '{"type": "CODEPIPELINE"}' \
  --environment "{
    \"type\": \"LINUX_CONTAINER\",
    \"image\": \"aws/codebuild/standard:7.0\",
    \"computeType\": \"BUILD_GENERAL1_SMALL\",
    \"privilegedMode\": true,
    \"environmentVariables\": [
      {\"name\": \"ECR_REPO\", \"value\": \"$ECR_REPO\"},
      {\"name\": \"AWS_DEFAULT_REGION\", \"value\": \"$REGION\"}
    ]
  }" \
  --service-role $CODEBUILD_ROLE_ARN \
  --logs-config '{
    "cloudWatchLogs": {
      "status": "ENABLED",
      "groupName": "/codebuild/lab05"
    }
  }' \
  --region $REGION

echo "CodeBuild project created"
```

---

## Step 5: Create CodePipeline

```bash
PIPELINE_ROLE_ARN=$(aws iam get-role \
  --role-name lab05-codepipeline-role \
  --query 'Role.Arn' --output tsv)

# Store GitHub token in Secrets Manager
aws secretsmanager create-secret \
  --name lab05/github-token \
  --secret-string "YOUR_GITHUB_TOKEN_HERE" \
  --region $REGION

aws codepipeline create-pipeline \
  --pipeline "{
    \"name\": \"lab05-pipeline\",
    \"roleArn\": \"$PIPELINE_ROLE_ARN\",
    \"artifactStore\": {
      \"type\": \"S3\",
      \"location\": \"$ARTIFACT_BUCKET\"
    },
    \"stages\": [
      {
        \"name\": \"Source\",
        \"actions\": [{
          \"name\": \"Source\",
          \"actionTypeId\": {
            \"category\": \"Source\",
            \"owner\": \"ThirdParty\",
            \"provider\": \"GitHub\",
            \"version\": \"1\"
          },
          \"configuration\": {
            \"Owner\": \"YOUR_GITHUB_USERNAME\",
            \"Repo\": \"lab05-app\",
            \"Branch\": \"main\",
            \"OAuthToken\": \"{{resolve:secretsmanager:lab05/github-token}}\"
          },
          \"outputArtifacts\": [{\"name\": \"SourceOutput\"}]
        }]
      },
      {
        \"name\": \"Build\",
        \"actions\": [{
          \"name\": \"Build\",
          \"actionTypeId\": {
            \"category\": \"Build\",
            \"owner\": \"AWS\",
            \"provider\": \"CodeBuild\",
            \"version\": \"1\"
          },
          \"configuration\": {\"ProjectName\": \"lab05-build\"},
          \"inputArtifacts\": [{\"name\": \"SourceOutput\"}],
          \"outputArtifacts\": [{\"name\": \"BuildOutput\"}]
        }]
      }
    ]
  }" \
  --region $REGION

echo "Pipeline created: lab05-pipeline"
```

---

## Step 6: Trigger and Monitor Pipeline

```bash
# Trigger pipeline manually
aws codepipeline start-pipeline-execution \
  --name lab05-pipeline \
  --region $REGION

# Watch pipeline status
watch -n 5 "aws codepipeline get-pipeline-state \
  --name lab05-pipeline \
  --region $REGION \
  --query 'stageStates[*].{Stage:stageName,Status:latestExecution.status}' \
  --output table"

# View CodeBuild logs
BUILD_ID=$(aws codebuild list-builds-for-project \
  --project-name lab05-build \
  --query 'ids[0]' --output tsv)

aws logs tail /codebuild/lab05 --follow
```

---

## Step 7: Cleanup

```bash
# Delete pipeline
aws codepipeline delete-pipeline --name lab05-pipeline --region $REGION

# Delete CodeBuild project
aws codebuild delete-project --name lab05-build --region $REGION

# Delete ECR repository
aws ecr delete-repository \
  --repository-name $APP_NAME \
  --force \
  --region $REGION

# Delete S3 bucket
aws s3 rm s3://$ARTIFACT_BUCKET --recursive
aws s3api delete-bucket --bucket $ARTIFACT_BUCKET

# Delete IAM roles
for ROLE in lab05-codebuild-role lab05-codepipeline-role; do
  aws iam list-attached-role-policies --role-name $ROLE \
    --query 'AttachedPolicies[*].PolicyArn' --output text | \
    tr '\t' '\n' | while read ARN; do
      aws iam detach-role-policy --role-name $ROLE --policy-arn $ARN
    done
  aws iam delete-role-policy --role-name $ROLE --policy-name CodeBuildPolicy 2>/dev/null || true
  aws iam delete-role-policy --role-name $ROLE --policy-name PipelinePolicy 2>/dev/null || true
  aws iam delete-role --role-name $ROLE
done

# Delete secret
aws secretsmanager delete-secret \
  --secret-id lab05/github-token \
  --force-delete-without-recovery \
  --region $REGION

echo "Cleanup complete"
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Source stage fails | Invalid GitHub token | Update token in Secrets Manager |
| Build fails: Docker permission | privilegedMode not enabled | Set `privilegedMode: true` in CodeBuild |
| Build fails: ECR push denied | Missing ECR permissions | Attach `AmazonEC2ContainerRegistryPowerUser` |
| Pipeline not triggering | Webhook not configured | Enable GitHub webhook in pipeline settings |
| Build cache not working | Wrong cache paths | Verify `node_modules` path in buildspec |

## What You Learned

✅ Create ECR repository with image scanning
✅ Write a complete buildspec.yml with test, build, push stages
✅ Create CodeBuild project with Docker support
✅ Build a CodePipeline with GitHub source
✅ Trigger and monitor pipeline execution
✅ View CodeBuild logs in CloudWatch
