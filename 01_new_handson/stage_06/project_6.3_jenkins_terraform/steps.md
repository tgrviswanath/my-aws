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

## Screenshots to Take
- [ ] Jenkins running at localhost:8080
- [ ] Pipeline stages visualization (Blue Ocean)
- [ ] Approval gate paused waiting for input
- [ ] Terraform plan output in Jenkins console
- [ ] Successful apply with outputs
- [ ] Multi-branch pipeline showing all branches
