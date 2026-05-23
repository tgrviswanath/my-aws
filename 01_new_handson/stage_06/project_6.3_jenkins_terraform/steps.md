# Steps — Project 6.3 Jenkins + Terraform Pipeline

## Phase 1 — Run Jenkins Locally (Docker)

```bash
# Build custom Jenkins image
cd jenkins
docker build -t jenkins-terraform:latest .

# Run Jenkins locally
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins-data:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins-terraform:latest

# Get initial admin password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# Open Jenkins: http://localhost:8080
```

---

## Phase 2 — Configure Jenkins

```
1. Open http://localhost:8080
2. Enter initial admin password
3. Install suggested plugins (or use plugins.txt)
4. Create admin user

5. Add AWS credentials:
   Manage Jenkins → Credentials → Global → Add Credentials
   Kind: AWS Credentials
   ID: aws-credentials
   Access Key ID: YOUR_KEY
   Secret Access Key: YOUR_SECRET

6. Configure GitHub webhook:
   GitHub repo → Settings → Webhooks → Add webhook
   Payload URL: http://YOUR_JENKINS_URL/github-webhook/
   Content type: application/json
   Events: Push, Pull Request
```

---

## Phase 3 — Create Pipeline Job

```
1. New Item → Pipeline
2. Name: terraform-pipeline
3. Pipeline → Definition: Pipeline script from SCM
4. SCM: Git
5. Repository URL: https://github.com/YOUR_ORG/YOUR_REPO
6. Branch: */main
7. Script Path: Jenkinsfile
8. Save
```

---

## Phase 4 — Run the Pipeline

```bash
# Trigger manually first
# Jenkins → terraform-pipeline → Build Now

# Watch stages:
# Checkout → Format Check → Init → Validate → Plan → Approval → Apply → Output

# On the Approval stage:
# Jenkins pauses and shows the plan
# Click "Proceed" to apply or "Abort" to cancel
```

---

## Phase 5 — Multi-branch Pipeline

```
1. New Item → Multibranch Pipeline
2. Branch Sources: GitHub
3. Repository: YOUR_REPO
4. Scan Multibranch Pipeline Triggers: 1 minute

# Jenkins automatically creates jobs for each branch
# main branch → runs full pipeline with approval
# feature/* branches → runs plan only (no apply)
```

---

## Phase 6 — Verification & Validation

### 6.1 AWS Console Verification
1. **IAM** → **Users** → `jenkins-terraform` → confirm programmatic access key exists
2. **EC2** → **Instances** → confirm any EC2 created by Terraform pipeline is running
3. **S3** → confirm Terraform state bucket exists and contains state file
4. **DynamoDB** → confirm lock table exists
5. **CloudTrail** → filter by `jenkins-terraform` IAM user → confirm API calls visible

### 6.2 CLI Verification Commands
```bash
# Confirm Jenkins is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
# Expected: 200 or 403 (login required = Jenkins is up)

# Confirm Jenkins container is healthy
docker ps --filter "name=jenkins" --format "table {{.Names}}\t{{.Status}}"
# Expected: jenkins  Up X minutes

# Confirm Terraform is available inside Jenkins
docker exec jenkins terraform version
# Expected: Terraform v1.x.x

# Confirm AWS CLI is available inside Jenkins
docker exec jenkins aws --version
# Expected: aws-cli/2.x.x

# Confirm Terraform state bucket exists
aws s3 ls | grep tf-state
# Expected: bucket name visible

# Confirm state file was written after pipeline run
aws s3 ls s3://YOUR-TF-STATE-BUCKET/ --recursive
# Expected: terraform.tfstate file present

# Confirm DynamoDB lock table exists
aws dynamodb describe-table --table-name terraform-lock \
  --query "Table.{Name:TableName,Status:TableStatus}"
# Expected: Status=ACTIVE
```

### 6.3 Functional Tests
```bash
# Test 1: Jenkins UI accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login
# Expected: 200

# Test 2: Pipeline runs successfully
# Jenkins → terraform-pipeline → Build Now
# Watch stages: Checkout → Format → Init → Validate → Plan → Approval → Apply → Output
# Expected: all stages green (green in Blue Ocean view)

# Test 3: Approval gate pauses pipeline
# During pipeline run, confirm it stops at "Approval" stage
# Jenkins → terraform-pipeline → current build → Paused for Input
# Click "Proceed" → pipeline continues to Apply
# Expected: pipeline resumes and completes

# Test 4: Abort at approval triggers no apply
# Run pipeline again → at Approval stage, click "Abort"
# Expected: pipeline stops, no terraform apply runs, no AWS resources changed

# Test 5: Feature branch runs plan-only (no apply)
# Push to a feature branch → multibranch pipeline detects it
# Expected: pipeline runs Checkout → Format → Init → Validate → Plan
# Expected: NO Apply stage on feature branch

# Test 6: Terraform state locking prevents concurrent runs
# Start two pipeline builds simultaneously
# Expected: second build waits or fails with "state locked" message

# Test 7: Verify infrastructure created by pipeline
aws ec2 describe-vpcs --filters "Name=tag:ManagedBy,Values=jenkins-terraform" \
  --query "Vpcs[*].{ID:VpcId,CIDR:CidrBlock,Tags:Tags}"
# Expected: VPC created by the pipeline
```

### 6.4 Logs & Monitoring Checks
```bash
# Check Jenkins build logs for errors
docker exec jenkins cat /var/jenkins_home/jobs/terraform-pipeline/builds/lastSuccessfulBuild/log \
  | grep -i "error\|failed\|exception" | head -20
# Expected: no errors

# Check Terraform plan output in Jenkins
# Jenkins → terraform-pipeline → last build → Console Output
# Look for: "Plan: X to add, 0 to change, 0 to destroy"

# Check CloudTrail for Terraform API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=jenkins-terraform \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --query "Events[*].{Time:EventTime,Event:EventName}" \
  --output table
# Expected: CreateVpc, CreateSubnet, etc. from the pipeline run
```

### 6.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| Jenkins UI | Accessible at localhost:8080 |
| `terraform version` in Jenkins | v1.x.x |
| Pipeline all stages | Green |
| Approval gate | Pauses pipeline, waits for input |
| Feature branch | Plan only, no Apply stage |
| State file in S3 | Present after apply |
| DynamoDB lock table | ACTIVE |
| AWS resources | Created with `ManagedBy=jenkins-terraform` tag |

### 6.6 Verification Checklist
- [ ] Jenkins running at localhost:8080
- [ ] Terraform and AWS CLI available inside Jenkins container
- [ ] AWS credentials configured in Jenkins credential store
- [ ] Pipeline job created from Jenkinsfile in SCM
- [ ] Pipeline runs all stages successfully (Checkout → Apply)
- [ ] Approval gate pauses pipeline and waits for human input
- [ ] Aborting at approval prevents terraform apply
- [ ] Feature branch runs plan-only (no apply stage)
- [ ] Terraform state file written to S3 after apply
- [ ] DynamoDB lock table prevents concurrent runs
- [ ] CloudTrail shows API calls from `jenkins-terraform` user
- [ ] Infrastructure tagged with `ManagedBy=jenkins-terraform`

---

## Screenshots to Take
- [ ] Jenkins running at localhost:8080
- [ ] Pipeline stages visualization (Blue Ocean)
- [ ] Approval gate paused waiting for input
- [ ] Terraform plan output in Jenkins console
- [ ] Successful apply with outputs
- [ ] Multi-branch pipeline showing all branches
