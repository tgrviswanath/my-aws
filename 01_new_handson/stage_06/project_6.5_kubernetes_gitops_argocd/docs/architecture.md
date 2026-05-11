# Architecture — Project 6.5 Kubernetes GitOps with ArgoCD

## GitOps Flow

```
Developer
    │
    │ git commit + push (Kubernetes manifests)
    ▼
GitHub Repository
    │
    │ ArgoCD polls every 3 minutes (or webhook)
    ▼
┌──────────────────────────────────────────────────────────────┐
│                  ArgoCD (running in EKS)                      │
│                                                               │
│  Compares:                                                    │
│    Desired state (Git) vs Live state (EKS cluster)           │
│                                                               │
│  If diff detected:                                            │
│    selfHeal=true  → auto-sync                                │
│    selfHeal=false → show OutOfSync, wait for manual sync     │
└──────────────────────────────────────────────────────────────┘
    │
    │ kubectl apply (Kustomize rendered manifests)
    ▼
┌──────────────────────────────────────────────────────────────┐
│                  EKS Cluster                                  │
│                                                               │
│  Namespace: dev                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Deployment: flask-api (1 replica)                    │   │
│  │  Service: flask-api (ClusterIP)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Namespace: prod                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Deployment: flask-api (3 replicas, spread 3 AZs)    │   │
│  │  Service: flask-api (ClusterIP)                       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Kustomize Overlay Pattern

```
k8s/
├── base/                    ← shared config (both envs)
│   ├── deployment.yaml      ← 2 replicas, image placeholder
│   ├── service.yaml
│   └── kustomization.yaml
│
└── overlays/
    ├── dev/                 ← dev-specific overrides
    │   ├── kustomization.yaml  ← namespace: dev, image: :latest
    │   └── patch-replicas.yaml ← replicas: 1
    │
    └── prod/                ← prod-specific overrides
        ├── kustomization.yaml  ← namespace: prod, image: :1.0.0
        └── patch-replicas.yaml ← replicas: 3
```

## ArgoCD Sync Policies

| Setting | Dev | Prod |
|---------|-----|------|
| Auto-sync | ✅ Yes | ❌ No (manual) |
| Self-heal | ✅ Yes | ❌ No |
| Prune | ✅ Yes | ✅ Yes |
| Image tag | `:latest` (auto-updated) | `:1.0.0` (pinned) |

## GitOps vs Traditional CI/CD

```
Traditional:
  CI/CD pipeline → kubectl apply → cluster
  (pipeline has cluster credentials)

GitOps:
  CI/CD pipeline → git push manifests → repo
  ArgoCD (in cluster) → pulls from repo → kubectl apply
  (cluster credentials never leave the cluster)
```
