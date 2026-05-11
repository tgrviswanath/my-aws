# Project 10.4 — Kubernetes on EKS

## What This Does
Deploys a production-grade Kubernetes cluster on Amazon EKS with auto-scaling, ingress, monitoring, and proper RBAC. Covers the core Kubernetes concepts needed for real-world work.

## Kubernetes Concepts Covered
| Concept | Description |
|---------|-------------|
| Pod | Smallest deployable unit — one or more containers |
| Deployment | Manages replica sets, rolling updates |
| Service | Stable network endpoint for pods |
| Ingress | HTTP routing rules (path/host-based) |
| ConfigMap | Non-secret configuration |
| Secret | Sensitive configuration (base64 encoded) |
| HPA | Horizontal Pod Autoscaler — scale on CPU/memory |
| RBAC | Role-Based Access Control |
| Namespace | Logical isolation within a cluster |
| Node Group | EC2 instances that run pods |

## Architecture
```
Internet → ALB Ingress Controller → Services → Pods
                                              ↑
                                         HPA scales
                                         based on CPU
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
aws eks update-kubeconfig --region us-east-1 --name handson-eks
kubectl apply -f k8s/
```

## Lessons Learned
- EKS control plane: $0.10/hr = $72/month — always running
- Fargate profiles: serverless pods — no node management, pay per pod
- Karpenter: better autoscaler than Cluster Autoscaler — provisions nodes in seconds
- AWS Load Balancer Controller: creates ALBs from Ingress resources
- IRSA: IAM Roles for Service Accounts — pods get AWS permissions without node IAM role
