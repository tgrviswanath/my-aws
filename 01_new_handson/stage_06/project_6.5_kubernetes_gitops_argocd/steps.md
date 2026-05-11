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

## Screenshots to Take
- [ ] EKS cluster nodes running
- [ ] ArgoCD UI showing applications
- [ ] Application synced (green health status)
- [ ] Git commit triggering automatic sync
- [ ] Self-healing: deleted pod recreated
- [ ] Drift detection: manual change reverted
- [ ] Dev (1 replica) vs Prod (3 replicas) overlay difference
