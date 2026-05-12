# Project 6.5 — Kubernetes GitOps with ArgoCD

## What This Does
Deploys the Flask API to Amazon EKS using GitOps methodology with ArgoCD. The Git repository is the single source of truth — ArgoCD continuously syncs the cluster state to match what's in Git.

## GitOps Principles
```
1. Declarative: all infrastructure and app config in Git
2. Versioned: every change is a Git commit (auditable)
3. Automated: ArgoCD syncs cluster to Git automatically
4. Reconciled: ArgoCD detects and fixes drift
```

## Architecture
```
Developer → Git push → GitHub repo (Kubernetes manifests)
                            ↓ ArgoCD watches
                       ArgoCD (running in EKS)
                            ↓ applies changes
                       EKS Cluster
                            └── Flask API Pods
                            └── Service
                            └── Ingress
```

## Repository Structure
```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   ├── kustomization.yaml
    │   └── patch-replicas.yaml
    └── prod/
        ├── kustomization.yaml
        └── patch-replicas.yaml
```

## How to Deploy
```bash
# 1. Create EKS cluster
cd terraform
terraform init && terraform apply

# 2. Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Create ArgoCD Application
kubectl apply -f argocd/application.yaml
```

## Lessons Learned
- GitOps: never `kubectl apply` manually — always commit to Git and let ArgoCD sync
- Kustomize: overlay pattern allows environment-specific config without duplication
- ArgoCD sync policy: `automated` with `selfHeal=true` fixes manual changes automatically
- Image updater: ArgoCD Image Updater watches ECR and updates image tags in Git automatically
- Health checks: ArgoCD shows deployment health — green = all pods running and ready

## Code

### `k8s/` — Kubernetes manifests

```bash
# Apply base manifests
kubectl apply -f k8s/base/

# Apply environment overlay (Kustomize)
kubectl apply -k k8s/overlays/dev/
kubectl apply -k k8s/overlays/prod/

# Check deployment status
kubectl get pods -n handson
kubectl get svc -n handson
```

### `argocd/application.yaml` — ArgoCD Application manifest

```bash
# Register the app with ArgoCD
kubectl apply -f argocd/application.yaml

# Sync manually
argocd app sync handson-app

# Watch sync status
argocd app get handson-app
```
