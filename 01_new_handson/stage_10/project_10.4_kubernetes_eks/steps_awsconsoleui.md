# Project 10.4 — Amazon EKS: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] kubectl installed locally: `kubectl version --client`
- [ ] AWS CLI configured with EKS permissions
- [ ] IAM permissions: `eks:*`, `ec2:*`, `iam:CreateRole`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] VPC with public and private subnets

---

## Step 1 — Navigate to Amazon EKS

1. Sign in to the **AWS Management Console**
2. Search for **EKS** or **Elastic Kubernetes Service**
3. Click **Amazon Elastic Kubernetes Service**
4. You see the **Clusters** list
5. Note the region — EKS clusters are regional

📸 Screenshot: EKS console home showing empty cluster list

---

## Step 2 — Create EKS Cluster (Step 1: Configure)

1. Click **Add cluster** → **Create**
2. **Configure cluster**:
   - **Name**: `myapp-eks-cluster`
   - **Kubernetes version**: `1.29` (or latest)
   - **Cluster service role**: Click **Create recommended role** or select existing
     - Role name: `eksClusterRole`
     - Permissions: `AmazonEKSClusterPolicy`
3. **Secrets encryption** (optional):
   - Envelope encryption with KMS CMK
4. Click **Next**

📸 Screenshot: EKS cluster configuration with name and version fields

---

## Step 3 — Cluster Networking

1. **Specify networking**:
   - **VPC**: Select your VPC
   - **Subnets**: Select all subnets (public + private)
   - **Security groups**: Leave default or select existing
2. **Cluster endpoint access**:
   - Select **Public and private** (recommended)
   - Public: kubectl from your laptop works
   - Private: Internal cluster communication secured
3. Click **Next**

📸 Screenshot: Networking configuration with Public and private endpoint access selected

---

## Step 4 — Configure Logging and Add-ons

1. **Configure logging**:
   - Enable: ✅ API server, ✅ Audit, ✅ Authenticator
   - Optional: ✅ Controller manager, ✅ Scheduler (more verbose)
2. Click **Next**
3. **Select add-ons**:
   - ✅ `CoreDNS` (cluster DNS)
   - ✅ `kube-proxy` (network rules)
   - ✅ `Amazon VPC CNI` (pod networking)
   - ✅ `Amazon EBS CSI Driver` (persistent volumes)
   - Optional: `AWS Load Balancer Controller` (managed separately with Helm)
4. Click **Next** → Review → **Create**
5. Wait 15-20 minutes for cluster to reach Active state

📸 Screenshot: Add-ons selection page with CoreDNS, VPC CNI, and EBS CSI checked

---

## Step 5 — Add Managed Node Group

1. Cluster status shows **Active**
2. Click the cluster name → **Compute** tab
3. Click **Add node group**
4. **Configure node group**:
   - **Name**: `general-workers`
   - **Node IAM role**: Create recommended role
     - Role includes: `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, `AmazonEC2ContainerRegistryReadOnly`
5. **Set compute and scaling configuration**:
   - **AMI type**: Amazon Linux 2 (AL2_x86_64)
   - **Capacity type**: On-Demand
   - **Instance types**: `t3.medium`
   - **Disk size**: 50 GB
6. **Node group scaling configuration**:
   - **Minimum**: 2
   - **Maximum**: 10
   - **Desired**: 3
7. Click **Next** → select subnets (private subnets preferred) → **Create**
8. Wait 5-10 minutes for nodes to join

📸 Screenshot: Node group configuration with t3.medium and min/max/desired scaling fields

---

## Step 6 — Connect kubectl to Cluster

From your local machine:
```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name myapp-eks-cluster

kubectl get nodes
# Should show 3 nodes in Ready state
```

From EKS console:
1. Cluster → **Overview** tab
2. Copy the **API server endpoint** and **Cluster ARN**
3. CloudShell (top nav): Run kubectl commands directly in AWS

📸 Screenshot: EKS cluster overview showing API endpoint and cluster status Active

---

## Step 7 — Install AWS Load Balancer Controller via Helm

From your terminal (not console UI — Helm required):
```bash
# Add EKS Helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install LBC
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=myapp-eks-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=us-east-1
```

Verify in console:
1. EKS cluster → **Resources** tab → **Workloads** → **Deployments**
2. Find `aws-load-balancer-controller` in `kube-system` namespace
3. Status should show "2 of 2 pods running"

📸 Screenshot: EKS Resources → Deployments showing aws-load-balancer-controller healthy

---

## Step 8 — Deploy Application and View in Console

After applying your manifests with `kubectl apply -f`, verify in console:

1. EKS cluster → **Resources** tab
2. **Workloads** → **Pods**: See all running pods
3. **Workloads** → **Deployments**: See deployment status and replicas
4. **Service and Networking** → **Ingresses**: See created ALB ARN
5. **Service and Networking** → **Services**: See ClusterIP services

📸 Screenshot: EKS Resources tab showing pods, deployments, and services

---

## Step 9 — View HPA in EKS Console

1. EKS cluster → **Resources** tab
2. **Autoscaling** → **Horizontal Pod Autoscalers**
3. See your HPA with:
   - Current replicas: 3
   - Min replicas: 2
   - Max replicas: 20
   - CPU utilization: Current% / Target%
4. During load test: watch replica count increase here

📸 Screenshot: HPA detail page showing current CPU utilization and scaling status

---

## Step 10 — Monitor with CloudWatch Container Insights

1. Navigate to **CloudWatch** → **Container Insights**
2. Select **EKS Clusters** from the dropdown
3. Select `myapp-eks-cluster`
4. View:
   - **Cluster**: Overall CPU/memory, pod count
   - **Node**: Per-node metrics
   - **Service**: Per-service request counts
   - **Pod**: Per-pod CPU/memory
5. Click **View logs** to see pod container logs

📸 Screenshot: CloudWatch Container Insights cluster view with CPU/memory graphs

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| kubectl connection refused | Not updated kubeconfig | Run `aws eks update-kubeconfig` |
| Nodes not showing in console | Node IAM role missing policies | Add `AmazonEKSWorkerNodePolicy` |
| LBC not creating ALB | Subnets missing tags | Tag subnets: `kubernetes.io/cluster/CLUSTER_NAME=shared` |
| Pods in Pending state | Insufficient node resources | Check `kubectl describe pod` for events |
| IRSA pod can't access AWS | OIDC not enabled | Enable OIDC provider on cluster |

---

## Console Navigation Quick Reference

```
Amazon EKS
├── Clusters                     → List all clusters
│   └── [Cluster Name]
│       ├── Overview             → API endpoint, status, ARN
│       ├── Compute              → Node groups, Fargate profiles
│       ├── Networking           → VPC, subnets, security groups
│       ├── Add-ons              → CoreDNS, VPC CNI, EBS CSI
│       ├── Resources tab
│       │   ├── Workloads        → Pods, Deployments, StatefulSets
│       │   ├── Service and Networking → Services, Ingresses
│       │   ├── Config and Storage → ConfigMaps, Secrets, PVCs
│       │   └── Autoscaling      → HPA, VPA
│       ├── Logging              → CloudWatch log groups
│       └── Access               → IAM access entries, RBAC

CloudWatch → Container Insights → EKS (monitoring)
```

---

**Decision Point 1:** Choose your deployment approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual setup | âœ… Good for learning |
| AWS CLI | Scripted, repeatable | âœ… Recommended |
| AWS CDK | Infrastructure as Code | Optional advanced |
