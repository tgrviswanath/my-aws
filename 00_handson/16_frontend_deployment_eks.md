# End-to-End Frontend Deployment on AWS using Docker, ECR & EKS

> **Document Type**: Step-by-step deployment guide with troubleshooting  
> **Use for**: Portfolio, resume, interviews, internal documentation, knowledge sharing  
> **Difficulty**: Intermediate  
> **Time**: ~45 minutes (excluding cluster creation ~20 min)

---

## 1. Introduction

This document describes the complete process of deploying a **React frontend application** on **Amazon EKS (Elastic Kubernetes Service)** using:

| Tool | Purpose |
|------|---------|
| **Docker** | Containerize the application |
| **Amazon ECR** | Store Docker images privately |
| **Amazon EKS** | Run containers on Kubernetes |
| **AWS CloudShell** | Manage cluster from browser (no local setup) |
| **Kubernetes LoadBalancer** | Expose app to the internet |

This guide includes **real issues faced** and how they were resolved — making it production-relevant and interview-ready.

---

## 2. High-Level Architecture

```
Developer Machine (WSL / Linux)
          │
          │  docker build
          ▼
  ┌───────────────────┐
  │   Docker Image    │
  │  frontend-app:v4  │
  └────────┬──────────┘
           │  docker push
           ▼
  ┌───────────────────────────────────────┐
  │     Amazon ECR (Private Registry)     │
  │  ACCOUNT_ID.dkr.ecr.ap-south-1.      │
  │  amazonaws.com/frontend-app:v4        │
  └────────┬──────────────────────────────┘
           │  image pull (on deploy)
           ▼
  ┌───────────────────────────────────────┐
  │       Amazon EKS Cluster              │
  │  ┌─────────────────────────────────┐  │
  │  │  Deployment (1 replica)         │  │
  │  │  Pod: frontend-app container    │  │
  │  └──────────────┬──────────────────┘  │
  │                 │                     │
  │  ┌──────────────▼──────────────────┐  │
  │  │  Service (LoadBalancer)         │  │
  │  │  Port 80 → Pod Port 80          │  │
  │  └──────────────┬──────────────────┘  │
  └─────────────────┼─────────────────────┘
                    │
                    ▼
           Internet Users
    http://xxxxx.ap-south-1.elb.amazonaws.com
```

---

## 3. Prerequisites

### Required
- ✅ AWS Account
- ✅ IAM User with permissions for: ECR, EKS, EC2, IAM
- ✅ Docker installed locally
- ✅ AWS CLI installed and configured
- ✅ Basic Kubernetes knowledge

### Verification Commands

```bash
# Verify AWS CLI is configured
aws sts get-caller-identity
# Expected output:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }

# Verify Docker is installed
docker --version
# Expected: Docker version 24.x.x

# Verify kubectl (if installed locally)
kubectl version --client
```

> 📸 **Screenshot point**: AWS CLI identity output showing your Account ID

---

## 4. Application Overview

```
Type:       Frontend Web Application (React/Vite)
Runtime:    Static files served via Nginx
Container:  Multi-stage Docker build (Node.js build → Nginx serve)
Exposure:   Public via Kubernetes LoadBalancer Service
Port:       80 (HTTP)
```

---

## 5. Step 1 — Dockerize the Application

### 5.1 Why Multi-Stage Build?

```
Single-stage build:
  Image size: ~1.2 GB (includes Node.js, npm, source code)
  Security risk: build tools exposed in production

Multi-stage build:
  Image size: ~25 MB (only Nginx + compiled static files)
  Security: no Node.js, no source code, no npm in final image
  Speed: faster pull, faster startup
```

### 5.2 Dockerfile

```dockerfile
# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files first (layer caching — only reinstall if deps change)
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source and build
COPY . .
RUN npm run build
# Output: /app/dist (or /app/build for CRA)

# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:alpine

# Copy compiled static files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Optional: custom nginx config for React Router (handle client-side routing)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Optional nginx.conf** (needed if using React Router):

```nginx
# nginx.conf — handle React Router (all routes → index.html)
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Serve static assets with long cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # All other routes → index.html (React Router handles it)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 5.3 Build the Docker Image

```bash
# Build with version tag (always use version tags, never just 'latest')
docker build -t frontend-app:v4 .

# Verify image was created
docker images | grep frontend-app
# Expected:
# frontend-app   v4   abc123def456   2 minutes ago   25.3MB

# Test locally before pushing
docker run -d -p 8080:80 --name test-frontend frontend-app:v4
curl http://localhost:8080
# Should return HTML content

# Clean up test container
docker stop test-frontend && docker rm test-frontend
```

> 📸 **Screenshot point**: `docker build` output showing "Successfully built" and image size

---

## 6. Step 2 — Push Image to Amazon ECR

### 6.1 Create ECR Repository

```bash
# Set your region
REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create private ECR repository
aws ecr create-repository \
  --repository-name frontend-app \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability IMMUTABLE

# Output includes repositoryUri:
# ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/frontend-app

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/frontend-app"
echo "ECR URI: $ECR_URI"
```

> 📸 **Screenshot point**: ECR repository created in AWS Console

### 6.2 Authenticate Docker with ECR

**Why?** Docker must authenticate before pushing to a private registry. ECR uses temporary tokens (valid 12 hours).

```bash
# Get ECR login token and pipe to docker login
aws ecr get-login-password --region $REGION \
  | docker login \
    --username AWS \
    --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Expected output:
# Login Succeeded
```

> 📸 **Screenshot point**: "Login Succeeded" message

### 6.3 Tag and Push Image

```bash
# Tag local image with ECR URI
docker tag frontend-app:v4 ${ECR_URI}:v4

# Push to ECR
docker push ${ECR_URI}:v4

# Expected output:
# v4: digest: sha256:abc123... size: 8765
```

> 📸 **Screenshot point**: Docker push output showing layer uploads

### 6.4 Verify Image in ECR

```bash
aws ecr describe-images \
  --repository-name frontend-app \
  --region $REGION \
  --query 'imageDetails[*].{Tag:imageTags[0],Size:imageSizeInBytes,Pushed:imagePushedAt}' \
  --output table

# Expected:
# -----------------------------------------------
# | Tag | Size    | Pushed                       |
# |-----|---------|------------------------------|
# | v4  | 8765432 | 2024-01-15T10:30:00+00:00   |
# -----------------------------------------------
```

> 📸 **Screenshot point**: Image visible in ECR console with tag v4

---

## 7. Issues Faced During ECR Push ⚠️

### Issue 1: Image Not Visible in ECR Console

**Symptom**: `docker push` completed without errors, but image not visible in ECR console.

**Root Cause**: 
- Image layers were uploaded successfully
- But the **manifest was not registered** due to:
  - Repeated reuse of the same tag (`latest`) with `MUTABLE` tag setting
  - Alpine base image warnings during build caused partial layer issues

**Fix**:
```bash
# Step 1: Rebuild with a new, unique version tag
docker build -t frontend-app:v4 .

# Step 2: Re-tag with new version
docker tag frontend-app:v4 ${ECR_URI}:v4

# Step 3: Push again
docker push ${ECR_URI}:v4
```

**✅ Lesson Learned**: 
> Always use **immutable, versioned tags** (v1, v2, v3...) instead of `latest`.  
> Enable `--image-tag-mutability IMMUTABLE` on ECR repositories to enforce this.

---

## 8. Step 3 — Kubernetes Setup using AWS CloudShell

### Why CloudShell?

```
Problem:  Corporate/local machine blocked GitHub access
          → eksctl could not be downloaded locally

Solution: AWS CloudShell provides:
  ✅ AWS CLI pre-installed and authenticated
  ✅ kubectl pre-installed
  ✅ Internet access (can download eksctl)
  ✅ Secure — uses your IAM credentials automatically
  ✅ No local setup required
```

**How to open CloudShell**: AWS Console → top navigation bar → CloudShell icon (>_)

> 📸 **Screenshot point**: AWS CloudShell terminal opened in browser

### 8.1 Verify Tools in CloudShell

```bash
# Verify kubectl
kubectl version --client
# Expected: Client Version: v1.28.x

# Verify AWS CLI and identity
aws sts get-caller-identity
# Expected: your Account ID and IAM user/role

# Verify AWS region
aws configure get region
```

> 📸 **Screenshot point**: Tool verification output in CloudShell

### 8.2 Install eksctl in CloudShell

```bash
# Download eksctl binary
curl -L -o eksctl.tar.gz \
  https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz

# Extract
tar -xzf eksctl.tar.gz

# Move to PATH
sudo mv eksctl /usr/local/bin/

# Verify
eksctl version
# Expected: 0.170.x or later
```

> 📸 **Screenshot point**: eksctl version output

---

## 9. Step 4 — Create EKS Cluster

```bash
eksctl create cluster \
  --name frontend-cluster \
  --region ap-south-1 \
  --node-type t3.small \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

# What this creates automatically:
# ✅ EKS Control Plane (managed by AWS)
# ✅ 1 Worker Node (t3.small EC2 instance)
# ✅ VPC with public and private subnets
# ✅ Security Groups
# ✅ IAM Roles for nodes
# ✅ kubeconfig updated automatically

# ⏱ Duration: ~15-20 minutes
```

> 📸 **Screenshot point**: eksctl cluster creation progress output

### 9.1 Verify Cluster is Ready

```bash
# Check nodes
kubectl get nodes
# Expected:
# NAME                                         STATUS   ROLES    AGE   VERSION
# ip-192-168-xx-xx.ap-south-1.compute.internal Ready    <none>   2m    v1.28.x

# Check cluster info
kubectl cluster-info
# Expected: Kubernetes control plane running at https://xxxxx.gr7.ap-south-1.eks.amazonaws.com
```

> 📸 **Screenshot point**: Node status showing "Ready"

---

## 10. Step 5 — Deploy Application to Kubernetes

### 10.1 Create Deployment YAML

```bash
mkdir -p k8s
nano k8s/deployment.yaml
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-app
  labels:
    app: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/frontend-app:v4
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "200m"
              memory: "128Mi"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
```

> 📸 **Screenshot point**: deployment.yaml file content

**Why these settings?**

| Setting | Value | Reason |
|---------|-------|--------|
| `replicas: 1` | 1 pod | Single node cluster (scale up for production) |
| `resources.requests` | 100m CPU, 64Mi | Kubernetes scheduler uses this to place pod |
| `resources.limits` | 200m CPU, 128Mi | Prevents one pod from consuming all node resources |
| `livenessProbe` | HTTP GET / | Restart pod if it becomes unresponsive |
| `readinessProbe` | HTTP GET / | Only send traffic when pod is ready |

### 10.2 Create Service YAML (LoadBalancer)

```bash
nano k8s/service.yaml
```

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  annotations:
    # Optional: specify internal or internet-facing
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
spec:
  type: LoadBalancer
  selector:
    app: frontend          # Must match Deployment labels
  ports:
    - name: http
      protocol: TCP
      port: 80             # External port (what users access)
      targetPort: 80       # Container port (Nginx listens on 80)
```

> 📸 **Screenshot point**: service.yaml file content

**Why LoadBalancer Service?**

```
Kubernetes Service Types:
  ClusterIP:    Only accessible within the cluster (internal)
  NodePort:     Accessible via node IP + port (testing only)
  LoadBalancer: Creates AWS ELB, accessible from internet ✅ (we use this)
  ExternalName: Maps to external DNS name
```

### 10.3 Apply Configuration

```bash
# Apply deployment
kubectl apply -f k8s/deployment.yaml
# Expected: deployment.apps/frontend-app created

# Apply service
kubectl apply -f k8s/service.yaml
# Expected: service/frontend-service created
```

> 📸 **Screenshot point**: kubectl apply output

---

## 11. Step 6 — Verify Deployment

### Check Pods

```bash
kubectl get pods
# Expected:
# NAME                            READY   STATUS    RESTARTS   AGE
# frontend-app-7d9f8b6c4-xk2p9   1/1     Running   0          2m

# If status is not Running, check logs:
kubectl logs frontend-app-7d9f8b6c4-xk2p9
kubectl describe pod frontend-app-7d9f8b6c4-xk2p9
```

> 📸 **Screenshot point**: Pod status showing "Running"

### Check Service & Get External URL

```bash
kubectl get svc
# Expected (wait 2-3 minutes for EXTERNAL-IP to appear):
# NAME               TYPE           CLUSTER-IP      EXTERNAL-IP                                    PORT(S)        AGE
# frontend-service   LoadBalancer   10.100.xx.xx    a99247b15d77948579d93aa305a51e4f-968649669.   80:31234/TCP   3m
#                                                   ap-south-1.elb.amazonaws.com

# Watch until EXTERNAL-IP is assigned (not <pending>)
kubectl get svc -w
```

> 📸 **Screenshot point**: Service with EXTERNAL-IP assigned

---

## 12. Step 7 — Access the Application

```bash
# Get the external URL
EXTERNAL_IP=$(kubectl get svc frontend-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Application URL: http://$EXTERNAL_IP"

# Test from command line
curl -I http://$EXTERNAL_IP
# Expected: HTTP/1.1 200 OK
```

**Open in browser**:
```
http://a99247b15d77948579d93aa305a51e4f-968649669.ap-south-1.elb.amazonaws.com/
```

> 📸 **Screenshot point**: Application running in browser showing your React app

---

## 13. Kubernetes Service Types Reference

| Type | Access | Use Case |
|------|--------|---------|
| `ClusterIP` | Internal only | Microservice-to-microservice communication |
| `NodePort` | Node IP + port | Local testing, not for production |
| `LoadBalancer` ✅ | Public internet | **Used here** — expose frontend publicly |
| `ExternalName` | External DNS | Route to external services |

---

## 14. Debug & Maintenance Commands

```bash
# ── Pod Management ────────────────────────────────────────────────────────────
kubectl get pods                          # List all pods
kubectl get pods -o wide                  # Show node assignment
kubectl describe pod <pod-name>           # Detailed pod info + events
kubectl logs <pod-name>                   # Container logs
kubectl logs <pod-name> --previous        # Logs from crashed container
kubectl exec -it <pod-name> -- /bin/sh    # Shell into container

# ── Service Management ────────────────────────────────────────────────────────
kubectl get svc                           # List services
kubectl describe svc frontend-service     # Service details

# ── Deployment Management ─────────────────────────────────────────────────────
kubectl get deployments                   # List deployments
kubectl rollout status deployment/frontend-app  # Check rollout
kubectl rollout history deployment/frontend-app # Rollout history
kubectl rollout undo deployment/frontend-app    # Rollback to previous

# ── Update Image (Zero-Downtime Deploy) ───────────────────────────────────────
kubectl set image deployment/frontend-app \
  frontend=ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/frontend-app:v5

# ── Scale ─────────────────────────────────────────────────────────────────────
kubectl scale deployment frontend-app --replicas=3

# ── Cluster Info ──────────────────────────────────────────────────────────────
kubectl get nodes                         # Node status
kubectl top nodes                         # Node resource usage
kubectl top pods                          # Pod resource usage
```

---

## 15. Cleanup — Avoid AWS Charges ⚠️

> **Important**: EKS clusters cost ~$0.10/hour for the control plane + EC2 costs for nodes. Always delete when not in use.

```bash
# Step 1: Delete Kubernetes resources first
kubectl delete -f k8s/service.yaml      # Deletes the AWS Load Balancer
kubectl delete -f k8s/deployment.yaml

# Step 2: Verify Load Balancer is deleted (check AWS Console → EC2 → Load Balancers)
# Wait 2-3 minutes before deleting cluster

# Step 3: Delete EKS cluster (deletes nodes, VPC, security groups)
eksctl delete cluster \
  --name frontend-cluster \
  --region ap-south-1

# ⏱ Duration: ~10-15 minutes

# Step 4: Delete ECR repository (optional)
aws ecr delete-repository \
  --repository-name frontend-app \
  --region ap-south-1 \
  --force
```

> 📸 **Screenshot point**: Cluster deletion in progress

---

## 16. Key Learnings

| # | Learning | Detail |
|---|---------|--------|
| 1 | **Multi-stage Docker builds** | Reduces image size from ~1.2GB to ~25MB |
| 2 | **ECR tagging strategy** | Always use immutable versioned tags (v1, v2...) |
| 3 | **Kubernetes Services** | LoadBalancer type creates AWS ELB automatically |
| 4 | **CloudShell for restricted environments** | Bypasses corporate firewall restrictions |
| 5 | **Resource requests/limits** | Critical for production stability |
| 6 | **Health probes** | Liveness + readiness prevent traffic to unhealthy pods |
| 7 | **Cleanup discipline** | Always delete EKS clusters when not in use |

---

## 17. Next Enhancements (Production Readiness)

### Priority 1 — Security & HTTPS
```bash
# Add HTTPS with AWS Certificate Manager + Ingress
# 1. Request ACM certificate for your domain
aws acm request-certificate \
  --domain-name app.mycompany.com \
  --validation-method DNS

# 2. Install AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=frontend-cluster

# 3. Create Ingress (replaces LoadBalancer Service)
# ingress.yaml:
# annotations:
#   kubernetes.io/ingress.class: alb
#   alb.ingress.kubernetes.io/scheme: internet-facing
#   alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

### Priority 2 — CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to EKS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
          docker build -t $ECR_URI:${{ github.sha }} .
          docker push $ECR_URI:${{ github.sha }}

      - name: Deploy to EKS
        run: |
          aws eks update-kubeconfig --name frontend-cluster --region ap-south-1
          kubectl set image deployment/frontend-app \
            frontend=$ECR_URI:${{ github.sha }}
          kubectl rollout status deployment/frontend-app
```

### Priority 3 — Auto Scaling
```yaml
# hpa.yaml — Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Priority 4 — Monitoring
```bash
# Install Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Or use CloudWatch Container Insights
aws eks create-addon \
  --cluster-name frontend-cluster \
  --addon-name amazon-cloudwatch-observability
```

---

## 18. Resume Bullet Points

Use these in your CV/resume:

```
• Containerized a React frontend using multi-stage Docker builds, reducing image size by 95% (1.2GB → 25MB)
• Deployed application to Amazon EKS using eksctl, kubectl, and Kubernetes Deployments/Services
• Configured Amazon ECR with immutable image tags and automated vulnerability scanning
• Exposed application publicly via Kubernetes LoadBalancer Service backed by AWS ELB
• Resolved ECR manifest registration issue by implementing versioned image tagging strategy
• Utilized AWS CloudShell to overcome corporate network restrictions for cluster management
• Documented end-to-end deployment process including troubleshooting steps and lessons learned
```

---

## 19. Interview Explanation (30-Second Version)

> *"I containerized a React app using a multi-stage Dockerfile — the build stage uses Node.js to compile the app, and the runtime stage uses Nginx to serve the static files, keeping the image under 25MB. I pushed the image to Amazon ECR with versioned tags, then deployed it to an EKS cluster using kubectl. I exposed it publicly using a Kubernetes LoadBalancer Service, which automatically provisioned an AWS ELB. One issue I faced was the ECR image not appearing in the console — I fixed it by rebuilding with a new version tag and enabling immutable tags. The whole pipeline is now ready to be automated with GitHub Actions."*

---

## 20. Architecture Diagram (Text Version)

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT PIPELINE                           │
│                                                                  │
│  Developer                                                       │
│  ┌──────────┐   docker build    ┌──────────────────────────┐    │
│  │  React   │ ──────────────►  │   Docker Image            │    │
│  │  App     │                  │   frontend-app:v4 (25MB)  │    │
│  └──────────┘                  └────────────┬─────────────┘    │
│                                             │ docker push       │
│                                             ▼                   │
│                               ┌────────────────────────────┐   │
│                               │     Amazon ECR              │   │
│                               │  Private Image Registry     │   │
│                               │  Immutable tags enforced    │   │
│                               └────────────┬───────────────┘   │
│                                            │ kubectl apply      │
│                                            ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Amazon EKS Cluster                      │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  Deployment: frontend-app                        │   │   │
│  │  │  ┌─────────────────────────────────────────────┐ │   │   │
│  │  │  │  Pod: Nginx serving React static files      │ │   │   │
│  │  │  │  Resources: 100m CPU, 64Mi RAM              │ │   │   │
│  │  │  │  Health: liveness + readiness probes        │ │   │   │
│  │  │  └─────────────────────────────────────────────┘ │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                          │                               │   │
│  │  ┌───────────────────────▼──────────────────────────┐   │   │
│  │  │  Service: LoadBalancer (port 80)                 │   │   │
│  │  │  → AWS ELB created automatically                 │   │   │
│  │  └───────────────────────┬──────────────────────────┘   │   │
│  └──────────────────────────┼──────────────────────────────┘   │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────── ┘
                              │
                              ▼
                    Internet Users
          http://xxxxx.ap-south-1.elb.amazonaws.com
```

---

*Document created: 2024 | Region: ap-south-1 (Mumbai) | Stack: Docker + ECR + EKS*
