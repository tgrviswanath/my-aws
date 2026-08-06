# Project 10.4 — Amazon EKS
## Managed Kubernetes: Cluster, Node Group, ALB Ingress, HPA, IRSA

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] kubectl installed: `kubectl version --client`
- [ ] eksctl installed: `eksctl version` (easiest EKS cluster tool)
- [ ] helm installed: `helm version` (for AWS Load Balancer Controller)
- [ ] IAM permissions: `eks:*`, `ec2:*`, `iam:*`, `autoscaling:*`
- [ ] Region: `us-east-1`

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
CLUSTER_NAME="myapp-eks-cluster"

# Verify tools
aws --version
kubectl version --client
eksctl version
helm version
```

---

## Decision Point 1

**EKS vs ECS vs App Runner — which container orchestration?**

| Factor | EKS ✅ | ECS ✅ | App Runner ✅ |
|--------|-------|-------|-------------|
| **Standard** | Kubernetes | AWS proprietary | AWS proprietary |
| **Portability** | ✅ Run anywhere | ❌ AWS only | ❌ AWS only |
| **Complexity** | High — full Kubernetes | Medium | Low |
| **Ops overhead** | High | Medium | Minimal |
| **Control** | Full | Good | Limited |
| **Cost** | $0.10/hr + nodes | No cluster fee + tasks | $0.064/vCPU-hour |
| **Best for** | Microservices, multi-cloud | AWS-native apps | Simple web services |

**Choose EKS when:**
- Team already knows Kubernetes
- Need multi-cloud portability
- Complex networking (service mesh, eBPF)
- Kubernetes ecosystem tools (Helm, ArgoCD, Istio)

**Choose ECS when:**
- Simpler AWS-native operations
- Deep ECS-Fargate integration (no servers to manage)
- Smaller team, less Kubernetes expertise

**Verdict:** EKS ✅ — portability and ecosystem are worth the complexity.

---

## 1. Architecture Overview

```
Internet
   │
   ▼
ALB (AWS Load Balancer Controller)
   │  managed by ALB Ingress Controller
   ▼
EKS Cluster (us-east-1)
├── Control Plane (managed by AWS — you don't see it)
│   └── API Server, etcd, scheduler, controller manager
│
├── Node Group (Managed): 3× t3.medium (auto-scaling 2-10)
│   ├── Pod: myapp-frontend (3 replicas) ← HPA scales by CPU
│   ├── Pod: myapp-backend (3 replicas) ← IRSA → S3, Secrets Manager
│   └── DaemonSet: aws-node (VPC CNI)
│
└── Add-ons
    ├── CoreDNS (service discovery)
    ├── kube-proxy (network rules)
    ├── AWS VPC CNI (pod networking)
    └── AWS Load Balancer Controller (ALB ingress)
```

---

## 2. Create EKS Cluster with eksctl

```bash
# Create cluster config file
cat > /tmp/eks-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: $CLUSTER_NAME
  region: $REGION
  version: "1.29"

iam:
  withOIDC: true  # Required for IRSA

managedNodeGroups:
  - name: general-workers
    instanceType: t3.medium
    minSize: 2
    maxSize: 10
    desiredCapacity: 3
    volumeSize: 50
    amiFamily: AmazonLinux2
    labels:
      role: worker
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/$CLUSTER_NAME: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
        albIngress: true
        cloudWatch: true

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Create cluster (takes 15-20 minutes)
eksctl create cluster -f /tmp/eks-cluster.yaml

# Update kubeconfig
aws eks update-kubeconfig \
  --region $REGION \
  --name $CLUSTER_NAME

# Verify cluster
kubectl get nodes -o wide
kubectl cluster-info
```

---

## 3. Install AWS Load Balancer Controller (ALB Ingress)

```bash
# Create IAM policy for LBC
curl -o /tmp/lbc-policy.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

LBC_POLICY_ARN=$(aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file:///tmp/lbc-policy.json \
  --query 'Policy.Arn' \
  --output text)

# Create service account with IRSA
eksctl create iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=$LBC_POLICY_ARN \
  --approve

# Install LBC via Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

VPC_ID=$(aws eks describe-cluster \
  --name $CLUSTER_NAME \
  --query 'cluster.resourcesVpcConfig.vpcId' \
  --output text)

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=$REGION \
  --set vpcId=$VPC_ID

# Verify LBC deployment
kubectl get deployment -n kube-system aws-load-balancer-controller
```

---

## 4. Set Up IRSA (IAM Roles for Service Accounts)

```bash
# IRSA lets Kubernetes pods assume IAM roles without storing credentials

# Create IAM policy for application
cat > /tmp/app-s3-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
    "Resource": ["arn:aws:s3:::myapp-bucket","arn:aws:s3:::myapp-bucket/*"]
  }]
}
EOF

APP_POLICY_ARN=$(aws iam create-policy \
  --policy-name MyAppS3Policy \
  --policy-document file:///tmp/app-s3-policy.json \
  --query 'Policy.Arn' --output text)

# Create IAM service account (IRSA)
eksctl create iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=default \
  --name=myapp-service-account \
  --role-name MyAppServiceAccountRole \
  --attach-policy-arn=$APP_POLICY_ARN \
  --approve

# Verify IRSA setup
kubectl describe serviceaccount myapp-service-account
# Should show annotation: eks.amazonaws.com/role-arn
```

---

## 5A. Console: Create EKS Cluster

1. Navigate to **Amazon EKS** → **Add cluster** → **Create**
2. **Step 1 — Configure cluster**:
   - **Name**: `myapp-eks-cluster`
   - **Kubernetes version**: 1.29
   - **Cluster service role**: Create new or select existing
3. **Step 2 — Networking**:
   - VPC, subnets (private + public)
   - Cluster endpoint access: Public and private
4. **Step 3 — Logging**: Enable API, audit, authenticator
5. **Step 4 — Add-ons**: Add CoreDNS, kube-proxy, VPC CNI, EBS CSI Driver
6. Click **Create** — wait 15-20 minutes

**Add Node Group:**
1. Cluster detail → **Compute** tab → **Add node group**
2. Name: `general-workers`
3. Node IAM role: Create new
4. Instance type: `t3.medium`
5. Min/Max/Desired: 2/10/3
6. Click **Create**

---

## 5B. CLI: Deploy Application to EKS

```bash
# Deploy sample application
cat > /tmp/myapp-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-backend
  labels:
    app: myapp-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp-backend
  template:
    metadata:
      labels:
        app: myapp-backend
    spec:
      serviceAccountName: myapp-service-account  # IRSA
      containers:
        - name: myapp-backend
          image: nginx:1.25  # Replace with your image
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          env:
            - name: AWS_REGION
              value: us-east-1
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-backend-svc
spec:
  selector:
    app: myapp-backend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:ACCOUNT:certificate/xxx
spec:
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-backend-svc
                port:
                  number: 80
EOF

kubectl apply -f /tmp/myapp-deployment.yaml

# Check deployment
kubectl get pods -l app=myapp-backend
kubectl get ingress myapp-ingress  # Shows ALB DNS
```

---

## 6. Configure Horizontal Pod Autoscaler (HPA)

```bash
# Ensure metrics-server is running
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for metrics-server
kubectl wait --for=condition=Available deployment/metrics-server \
  -n kube-system --timeout=120s

# Create HPA: scale between 2-20 pods based on CPU
cat > /tmp/hpa.yaml << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp-backend
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min before scaling down
    scaleUp:
      stabilizationWindowSeconds: 60   # 1 min before scaling up
EOF

kubectl apply -f /tmp/hpa.yaml

# Watch HPA
kubectl get hpa myapp-backend-hpa -w
```

---

## 7. Enable Cluster Autoscaler

```bash
# Install Cluster Autoscaler (scales EC2 nodes up/down)
cat > /tmp/cluster-autoscaler.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
      annotations:
        cluster-autoscaler.kubernetes.io/safe-to-evict: "false"
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
        - image: registry.k8s.io/autoscaling/cluster-autoscaler:v1.29.0
          name: cluster-autoscaler
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/${CLUSTER_NAME}
          env:
            - name: AWS_REGION
              value: ${REGION}
EOF

kubectl apply -f /tmp/cluster-autoscaler.yaml
```

---

## 8. Configure Monitoring with CloudWatch

```bash
# Install CloudWatch Container Insights
CLUSTER_NAME_VAR=$CLUSTER_NAME
REGION_VAR=$REGION

curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml \
  | sed "s/{{cluster_name}}/$CLUSTER_NAME_VAR/;s/{{region_name}}/$REGION_VAR/" \
  | kubectl apply -f -

# View logs via CloudWatch
# Console: CloudWatch → Container Insights → EKS → select cluster
```

---

## 9. Deploy Helm Chart (Production Pattern)

```bash
# Create Helm chart for myapp
helm create myapp-chart
cd myapp-chart

# Update values.yaml with your values
cat > values.yaml << 'EOF'
replicaCount: 3

image:
  repository: ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/myapp
  tag: latest
  pullPolicy: Always

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
  hosts:
    - host: api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

serviceAccount:
  create: false
  name: myapp-service-account
EOF

# Install Helm chart
helm install myapp ./myapp-chart \
  --namespace default \
  --create-namespace \
  --wait

# Upgrade
helm upgrade myapp ./myapp-chart --set image.tag=v1.1.0
```

---

## 10. Verify Complete EKS Setup

```bash
echo "=== EKS Setup Verification ==="

# 1. Cluster running
aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.{Status:status,Version:version,Endpoint:endpoint}'

# 2. Nodes ready
kubectl get nodes --no-headers | grep -c "Ready"

# 3. LBC running
kubectl get deployment aws-load-balancer-controller -n kube-system

# 4. App pods running
kubectl get pods -l app=myapp-backend

# 5. Ingress has ALB address
kubectl get ingress myapp-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# 6. HPA configured
kubectl get hpa myapp-backend-hpa

# 7. IRSA working (pod should access S3)
kubectl exec -it $(kubectl get pod -l app=myapp-backend -o name | head -1) \
  -- aws s3 ls s3://myapp-bucket --region us-east-1

echo "=== EKS Verification Complete ==="
```

---

## Troubleshooting

**Nodes not joining cluster:**
```bash
kubectl describe nodes
# Check security group allows worker nodes to reach API server
```

**LBC not creating ALB:**
```bash
kubectl describe ingress myapp-ingress
kubectl logs -n kube-system deployment/aws-load-balancer-controller
# Common: subnet tags missing: kubernetes.io/cluster/CLUSTER_NAME=shared
```

**IRSA not working:**
```bash
kubectl exec -it POD_NAME -- env | grep AWS
# Should see AWS_ROLE_ARN and AWS_WEB_IDENTITY_TOKEN_FILE
```

**HPA not scaling:**
```bash
kubectl describe hpa myapp-backend-hpa
# Verify metrics-server running and resources.requests set on pods
```

---

## Expected Outcome

- ✅ EKS cluster running Kubernetes 1.29
- ✅ Managed node group with 3× t3.medium workers (auto-scales 2-10)
- ✅ AWS Load Balancer Controller creating ALBs from Ingress resources
- ✅ Application deployed and accessible via ALB
- ✅ HPA scaling pods 2-20 based on CPU/memory
- ✅ IRSA — pods access S3 without hardcoded credentials
- ✅ Cluster Autoscaler adding/removing nodes as needed
- ✅ CloudWatch Container Insights for observability

---

## Cleanup

```bash
# Delete application resources
kubectl delete -f /tmp/myapp-deployment.yaml
kubectl delete -f /tmp/hpa.yaml

# Uninstall Helm releases
helm uninstall myapp
helm uninstall aws-load-balancer-controller -n kube-system

# Delete node group (must do before deleting cluster)
aws eks delete-nodegroup \
  --cluster-name $CLUSTER_NAME \
  --nodegroup-name general-workers
# Wait for deletion...
aws eks wait nodegroup-deleted \
  --cluster-name $CLUSTER_NAME \
  --nodegroup-name general-workers

# Delete EKS cluster
aws eks delete-cluster --name $CLUSTER_NAME
# Wait for deletion...
aws eks wait cluster-deleted --name $CLUSTER_NAME

# Delete IAM resources
aws iam delete-policy --policy-arn $LBC_POLICY_ARN
aws iam delete-policy --policy-arn $APP_POLICY_ARN

echo "EKS cleanup complete"
echo "Note: Deleting cluster takes 10-15 minutes"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
