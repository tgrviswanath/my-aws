# Cost Estimate — Project 10.4: Amazon EKS

## EKS Pricing Components

| Resource | Price | Notes |
|----------|-------|-------|
| EKS cluster | $0.10/hour | Control plane — always running |
| EC2 worker nodes | EC2 on-demand prices | You pay for the EC2 instances |
| EKS Fargate | $0.04048/vCPU-hour + $0.004445/GB-hour | Serverless nodes |
| AWS Load Balancer | Standard ALB pricing | $0.008/LCU-hour |
| Data transfer | Standard EC2 pricing | $0.09/GB out |

---

## Free Tier

- **EKS control plane**: No free tier — $0.10/hour from day one
- **EC2 worker nodes**: t2.micro/t3.micro free tier (12 months)
- **EKS Fargate**: No free tier

---

## Scenario Estimates

### Minimal Cluster (Learning)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| EKS cluster control plane | 1 × 730 hours | $73.00 |
| Worker nodes: t3.medium × 2 | 2 × $0.0416/hr × 730 | $60.73 |
| ALB (minimal traffic) | 1 ALB | $16.20 |
| Data transfer out (10 GB) | 10 GB | $0.90 |
| CloudWatch logs (1 GB) | 1 GB | $0.50 |
| **Total** | | **~$151.33/month** |

### Development Cluster (3 nodes)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| EKS control plane | 1 | $73.00 |
| t3.medium × 3 nodes | 3 × $0.0416/hr × 730 | $91.10 |
| ALB | 1 | $16.20 |
| NAT Gateway (for private nodes) | 2 AZs | $65.70 |
| CloudWatch logs (5 GB) | 5 GB | $2.50 |
| ECR storage | 5 GB | $0.50 |
| **Total** | | **~$249/month** |

### Production Cluster (Auto-scaling 5-20 nodes)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| EKS control plane | 1 | $73.00 |
| m5.xlarge nodes (avg 8 nodes) | 8 × $0.192/hr × 730 | $1,121.28 |
| ALB × 2 (multi-env) | 2 | $32.40 |
| NAT Gateway × 2 | 2 | $65.70 |
| CloudWatch Container Insights | 50 GB logs | $25.00 |
| ECR storage | 20 GB | $2.00 |
| Data transfer out (100 GB) | 100 GB | $9.00 |
| **Total** | | **~$1,328/month** |

### Fargate Only (No EC2 worker nodes)
| Resource | Quantity | Monthly Cost |
|----------|----------|-------------|
| EKS control plane | 1 | $73.00 |
| Fargate: 10 pods × 0.25vCPU × 0.5GB, 730hr | 10 pods | $78.00 |
| ALB | 1 | $16.20 |
| **Total** | | **~$167/month** |

---

## Cost Savings: Spot Instances for Worker Nodes

Using Spot instances for non-critical workloads:
- t3.medium On-Demand: $0.0416/hour
- t3.medium Spot: ~$0.0125/hour (70% savings)
- 3 Spot nodes vs On-Demand: $27.38 vs $91.10 = **$63.72/month saved**

```bash
# Mixed node group: On-Demand base + Spot for burst
eksctl create nodegroup \
  --cluster myapp-eks-cluster \
  --name spot-workers \
  --spot \
  --instance-types t3.medium,t3a.medium,m5.large \
  --nodes-min 0 \
  --nodes-max 20
```

---

## EKS vs ECS vs App Runner Cost Comparison

| Service | 3-node equivalent | Monthly |
|---------|------------------|---------|
| **EKS (t3.medium × 3)** | Full cluster | ~$249 |
| **ECS on EC2 (t3.medium × 3)** | No cluster fee | ~$176 |
| **ECS Fargate (same workload)** | No servers | ~$150-200 |
| **App Runner** | 3 services | ~$50-100 |

**ECS is cheaper** for pure AWS workloads. **EKS is worth it** for Kubernetes portability.

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Learning (minimal cluster) | ~$151 | ~$1,812 |
| Development (3 nodes) | ~$249 | ~$2,988 |
| Production (auto-scaling) | ~$1,328 | ~$15,936 |
| Fargate only | ~$167 | ~$2,004 |

**For learning:** Consider running cluster only during active use — stop node groups overnight.

---

## Cleanup

```bash
CLUSTER_NAME="myapp-eks-cluster"
REGION="us-east-1"

# Delete all Kubernetes resources first
kubectl delete all --all --all-namespaces 2>/dev/null
helm uninstall aws-load-balancer-controller -n kube-system 2>/dev/null

# Delete node groups (most expensive part — stops EC2 charges)
for NG in $(aws eks list-nodegroups --cluster-name $CLUSTER_NAME \
  --query 'nodegroups[]' --output text); do
  echo "Deleting node group: $NG"
  aws eks delete-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NG
  aws eks wait nodegroup-deleted --cluster-name $CLUSTER_NAME --nodegroup-name $NG
done

# Delete Fargate profiles if any
for FP in $(aws eks list-fargate-profiles --cluster-name $CLUSTER_NAME \
  --query 'fargateProfileNames[]' --output text); do
  aws eks delete-fargate-profile --cluster-name $CLUSTER_NAME --fargate-profile-name $FP
done

# Delete EKS cluster ($0.10/hr stops)
aws eks delete-cluster --name $CLUSTER_NAME
aws eks wait cluster-deleted --name $CLUSTER_NAME

# Delete IAM policies
aws iam delete-policy --policy-arn $LBC_POLICY_ARN 2>/dev/null
aws iam delete-policy --policy-arn $APP_POLICY_ARN 2>/dev/null

# Delete CloudWatch log groups
aws logs delete-log-group \
  --log-group-name "/aws/eks/${CLUSTER_NAME}/cluster" 2>/dev/null

echo "EKS cleanup complete — billing stops within 1 hour"
echo "Major savings: deleting node groups stops EC2 charges immediately"
```
