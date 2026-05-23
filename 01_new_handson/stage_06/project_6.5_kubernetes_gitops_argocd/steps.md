# Steps — Project 6.5 Kubernetes GitOps with ArgoCD

## Phase 1 — Create EKS Cluster

```bash
cd terraform
terraform init && terraform apply -auto-approve

# Configure kubectl
aws eks update-kubeconfig \
  --region us-east-1 \
  --name handson-eks-cluster

# Verify
kubectl get nodes
kubectl get namespaces
```

---

## Phase 2 — Install ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment/argocd-server \
  -n argocd --timeout=300s

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo

# Port-forward to access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
# Open: https://localhost:8080
# Username: admin, Password: (from above)
```

---

## Phase 3 — Deploy Application via ArgoCD

```bash
# Update application.yaml with your repo URL
sed -i 's|YOUR_ORG/YOUR_REPO|your-github-username/your-repo|g' argocd/application.yaml

# Apply ArgoCD Application
kubectl apply -f argocd/application.yaml

# Watch sync status
kubectl get applications -n argocd
argocd app get flask-api-dev
argocd app sync flask-api-dev
```

---

## Phase 4 — Test GitOps (Make a Change via Git)

```bash
# Change replica count in dev overlay
sed -i 's/replicas: 1/replicas: 2/' k8s/overlays/dev/patch-replicas.yaml

git add . && git commit -m "scale: increase dev replicas to 2"
git push origin main

# ArgoCD detects the change within 3 minutes (default poll interval)
# Or trigger manual sync:
argocd app sync flask-api-dev

# Watch pods scale up
kubectl get pods -n dev -w
```

---

## Phase 5 — Test Self-healing

```bash
# Manually delete a pod (simulates crash)
kubectl delete pod -n dev -l app=flask-api

# ArgoCD detects drift and recreates the pod automatically
kubectl get pods -n dev -w
# Pod should come back within seconds
```

---

## Phase 6 — Test Drift Detection

```bash
# Manually scale deployment (bypassing GitOps)
kubectl scale deployment flask-api -n dev --replicas=5

# ArgoCD detects drift (selfHeal=true)
# Within 3 minutes, ArgoCD reverts to 1 replica (what's in Git)
kubectl get pods -n dev -w
```

---

## Phase 7 — Verification & Validation

### 7.1 AWS Console Verification
1. **EKS** → **Clusters** → `handson-eks-cluster` → confirm status = Active
2. **EKS** → **Compute** → **Node groups** → confirm nodes = Ready
3. **EC2** → **Instances** → confirm EKS worker nodes running
4. **EC2** → **Load Balancers** → confirm ALB created by ingress controller

### 7.2 CLI Verification Commands
```bash
# Confirm EKS cluster is active
aws eks describe-cluster --name handson-eks-cluster \
  --query "cluster.{Status:status,Version:version,Endpoint:endpoint}"
# Expected: Status=ACTIVE

# Confirm nodes are ready
kubectl get nodes -o wide
# Expected: all nodes STATUS=Ready

# Confirm ArgoCD is running
kubectl get pods -n argocd
# Expected: all pods Running (argocd-server, argocd-repo-server, etc.)

# Confirm ArgoCD application exists and is synced
kubectl get applications -n argocd
# Expected: flask-api-dev  Synced  Healthy

# Confirm app pods are running in dev namespace
kubectl get pods -n dev -l app=flask-api
# Expected: pods in Running state

# Confirm service and ingress exist
kubectl get svc,ingress -n dev
# Expected: flask-api service + ingress with ADDRESS

# Confirm ArgoCD is watching the correct repo
kubectl get application flask-api-dev -n argocd \
  -o jsonpath='{.spec.source.repoURL}'
# Expected: your GitHub repo URL
```

### 7.3 Functional Tests
```bash
# Test 1: App is accessible via ingress
INGRESS_URL=$(kubectl get ingress -n dev \
  -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
curl -s http://$INGRESS_URL/health | python3 -m json.tool
# Expected: {"status": "ok"}

# Test 2: GitOps — change replica count via Git
sed -i 's/replicas: 1/replicas: 2/' k8s/overlays/dev/patch-replicas.yaml
git add . && git commit -m "scale: dev replicas to 2"
git push origin main
# Wait for ArgoCD to sync (up to 3 minutes)
kubectl get pods -n dev -w
# Expected: second pod appears automatically

# Test 3: Verify ArgoCD synced the change
argocd app get flask-api-dev --grpc-web
# Expected: Sync Status=Synced, Health Status=Healthy

# Test 4: Self-healing — delete a pod manually
POD=$(kubectl get pods -n dev -l app=flask-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD -n dev
kubectl get pods -n dev -w
# Expected: new pod created within seconds (Kubernetes self-healing)

# Test 5: Drift detection — manually scale outside GitOps
kubectl scale deployment flask-api -n dev --replicas=5
kubectl get pods -n dev
# Expected: 5 pods briefly, then ArgoCD reverts to 2 (what's in Git) within 3 min
kubectl get pods -n dev -w
# Expected: scales back to 2

# Test 6: Dev vs Prod overlay difference
kubectl get deployment flask-api -n dev \
  -o jsonpath='{.spec.replicas}'
# Expected: 1 (dev overlay)

kubectl get deployment flask-api -n prod \
  -o jsonpath='{.spec.replicas}'
# Expected: 3 (prod overlay)
```

### 7.4 Terraform State Verification
```bash
cd terraform
terraform state list | grep -E "eks|node_group|iam"
# Expected: aws_eks_cluster, aws_eks_node_group, IAM roles

terraform output
# Expected: cluster_name, cluster_endpoint, kubeconfig_command

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

### 7.5 Logs & Monitoring Checks
```bash
# Check ArgoCD sync history
argocd app history flask-api-dev --grpc-web
# Expected: recent sync entries with Succeeded status

# Check pod logs for errors
kubectl logs -n dev -l app=flask-api --tail=20
# Expected: no ERROR lines

# Check ArgoCD application events
kubectl describe application flask-api-dev -n argocd | grep -A 20 "Events:"
# Expected: Sync succeeded events

# Check EKS cluster logs (control plane)
aws eks describe-cluster --name handson-eks-cluster \
  --query "cluster.logging.clusterLogging"
# Expected: logging enabled for api, audit, authenticator
```

### 7.6 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| EKS cluster | Status=ACTIVE |
| Nodes | All STATUS=Ready |
| ArgoCD pods | All Running |
| App sync status | Synced + Healthy |
| Git change → pods | New pods within 3 min |
| Deleted pod | Recreated within seconds |
| Manual scale to 5 | Reverted to Git value within 3 min |
| Dev replicas | 1 (from dev overlay) |
| Prod replicas | 3 (from prod overlay) |

### 7.7 Verification Checklist
- [ ] EKS cluster status = ACTIVE
- [ ] All worker nodes STATUS = Ready
- [ ] ArgoCD all pods Running in `argocd` namespace
- [ ] ArgoCD application `flask-api-dev` Synced + Healthy
- [ ] App pods running in `dev` namespace
- [ ] Ingress has an ADDRESS (ALB provisioned)
- [ ] `curl /health` via ingress returns HTTP 200
- [ ] Git commit (replica change) triggers ArgoCD sync within 3 min
- [ ] Deleted pod recreated automatically (self-healing)
- [ ] Manual kubectl scale reverted by ArgoCD (drift detection)
- [ ] Dev overlay = 1 replica, Prod overlay = 3 replicas
- [ ] Terraform state contains EKS cluster, no drift

---

## Screenshots to Take
- [ ] EKS cluster nodes running
- [ ] ArgoCD UI showing applications
- [ ] Application synced (green health status)
- [ ] Git commit triggering automatic sync
- [ ] Self-healing: deleted pod recreated
- [ ] Drift detection: manual change reverted
- [ ] Dev (1 replica) vs Prod (3 replicas) overlay difference
