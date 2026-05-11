# Cost Estimate — Project 10.4 Kubernetes on EKS

| Resource | Monthly Cost |
|----------|-------------|
| EKS control plane | $72 |
| Worker nodes (t3.medium x2) | ~$60 |
| ALB (Ingress) | ~$16 |
| **Total** | **~$148/month** |

## Cost Reduction
- Use EKS with Fargate: no worker nodes, pay per pod (~$0.04/vCPU-hr)
- Use minikube locally for learning (free)
- Destroy after learning: `terraform destroy`
- Karpenter: provision spot instances automatically — 60-90% cheaper
