# Cost Estimate — Project 6.5 Kubernetes GitOps with ArgoCD

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| EKS cluster (control plane) | 1 cluster | $72 |
| EKS worker nodes (t3.medium x2) | 2 nodes | ~$60 |
| ArgoCD (runs on worker nodes) | Included above | $0 |
| ALB Ingress Controller | 1 ALB | ~$16 |
| ECR images | < 500 MB | $0 (free tier) |
| **Total** | | **~$148/month** |

## ⚠️ EKS is Expensive for Learning
- EKS control plane: $0.10/hr = $72/month — always running
- Worker nodes: ~$0.04/hr each for t3.medium

## Cost Reduction Options
1. **Destroy after learning**: `terraform destroy` — saves ~$148/month
2. **Use minikube locally**: free, runs on your laptop
3. **Use k3s on EC2**: ~$15/month (single t3.small node)
4. **EKS with Fargate**: no worker nodes, pay per pod — cheaper for low traffic

## Recommended Approach for Learning
```bash
# Use minikube locally first (free)
minikube start
kubectl apply -f k8s/overlays/dev/

# Only deploy to EKS when you need to test AWS-specific features
# Always destroy EKS when done
terraform destroy
```
