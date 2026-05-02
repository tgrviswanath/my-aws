# Containers on AWS — ECS & EKS Deep Dive

## Container Services Overview

| Service | Description | Best For |
|---------|-------------|---------|
| ECS (Fargate) | Serverless containers | Simple, no K8s overhead |
| ECS (EC2) | Containers on your EC2 | Cost control, GPU, custom AMI |
| EKS | Managed Kubernetes | K8s workloads, portability |
| App Runner | Fully managed container service | Simple web apps, APIs |
| Lambda Container | Lambda with container image | Serverless, up to 10GB image |

---

## ECS — Elastic Container Service

### Core Concepts

```
ECS Cluster
├── Services (long-running tasks)
│   ├── Task Definition (blueprint)
│   │   ├── Container definitions
│   │   ├── CPU/Memory
│   │   ├── IAM Task Role
│   │   └── Networking mode
│   └── Tasks (running instances of task def)
└── Capacity Providers
    ├── Fargate (serverless)
    └── EC2 (your instances)
```

### Task Definition

```json
{
  "family": "web-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/web-app:latest",
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "ENV", "value": "production"}
      ],
      "secrets": [
        {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/web-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "web"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### ECS Service with ALB

```bash
# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Create ECS cluster
aws ecs create-cluster \
  --cluster-name production \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=4

# Create service
aws ecs create-service \
  --cluster production \
  --service-name web-service \
  --task-definition web-app:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-aaa", "subnet-bbb"],
      "securityGroups": ["sg-12345678"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "arn:aws:elasticloadbalancing:...",
    "containerName": "web",
    "containerPort": 8080
  }]' \
  --deployment-configuration '{
    "maximumPercent": 200,
    "minimumHealthyPercent": 100,
    "deploymentCircuitBreaker": {"enable": true, "rollback": true}
  }'
```

### ECS Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/production/web-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 50

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/production/web-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

### ECR — Elastic Container Registry

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository \
  --repository-name web-app \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# Build, tag, push
docker build -t web-app .
docker tag web-app:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/web-app:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/web-app:latest

# Set lifecycle policy (keep last 10 images)
aws ecr put-lifecycle-policy \
  --repository-name web-app \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {"type": "expire"}
    }]
  }'
```

---

## EKS — Elastic Kubernetes Service

### Architecture

```
EKS Control Plane (AWS managed)
├── API Server
├── etcd
├── Controller Manager
└── Scheduler

Worker Nodes (you manage)
├── EC2 Node Groups
│   └── EC2 instances with kubelet, kube-proxy
├── Fargate Profiles (serverless)
└── Managed Node Groups (AWS manages EC2 lifecycle)
```

### Create EKS Cluster

```bash
# Install eksctl
# Create cluster with managed node group
eksctl create cluster \
  --name production \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --with-oidc \
  --ssh-access \
  --ssh-public-key my-key

# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name production

# Verify
kubectl get nodes
kubectl get pods --all-namespaces
```

### Kubernetes Deployment on EKS

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: web-app
    spec:
      serviceAccountName: web-app-sa
      containers:
        - name: web
          image: 123456789.dkr.ecr.us-east-1.amazonaws.com/web-app:v1.2.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: production
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
spec:
  selector:
    app: web-app
  ports:
    - port: 80
      targetPort: 8080
  type: LoadBalancer
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
```

### IAM Roles for Service Accounts (IRSA)

```bash
# Create IAM role for pod
eksctl create iamserviceaccount \
  --name web-app-sa \
  --namespace production \
  --cluster production \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess \
  --approve \
  --override-existing-serviceaccounts
```

---

## ECS vs EKS Decision Matrix

| Factor | ECS Fargate | ECS EC2 | EKS |
|--------|------------|---------|-----|
| Operational overhead | Low | Medium | High |
| Kubernetes compatibility | ❌ | ❌ | ✅ |
| Cost (small scale) | Medium | Low | High (control plane $0.10/hr) |
| Auto scaling | ✅ | ✅ | ✅ |
| GPU support | ❌ | ✅ | ✅ |
| Service mesh | AWS App Mesh | AWS App Mesh | Istio/App Mesh |
| Multi-cloud portability | ❌ | ❌ | ✅ |

---

## Interview Q&A

### Q1: What is the difference between ECS and EKS?
**ECS**: AWS-native container orchestration. Simpler, tighter AWS integration, lower operational overhead. No Kubernetes knowledge needed. Best for teams going all-in on AWS.
**EKS**: Managed Kubernetes. Industry-standard, portable across clouds, rich ecosystem (Helm, Istio, etc.). Higher operational complexity and cost. Best for teams with K8s expertise or multi-cloud requirements.

### Q2: What is Fargate and when would you use it?
Fargate is serverless compute for containers — you don't manage EC2 instances. AWS provisions, scales, and patches the underlying infrastructure. Use when: you want to focus on apps not infrastructure, workloads are variable, you don't need GPU or custom AMIs. Slightly more expensive than EC2 but eliminates node management.

### Q3: How do you handle secrets in ECS/EKS?
**ECS**: Reference Secrets Manager or SSM Parameter Store ARNs in task definition `secrets` field. ECS injects them as environment variables at runtime. Never hardcode in task definition or image.
**EKS**: Use AWS Secrets Manager with External Secrets Operator, or AWS Secrets and Config Provider (ASCP) with CSI driver to mount secrets as files. Use IRSA to grant pods access to Secrets Manager.

### Q4: How does rolling deployment work in ECS?
ECS replaces tasks gradually. `maximumPercent=200, minimumHealthyPercent=100` means: launch new tasks first (up to 200% capacity), wait for health checks, then terminate old tasks. `deploymentCircuitBreaker` automatically rolls back if new tasks fail health checks. Zero downtime if configured correctly.

### Q5: What is IRSA and why is it important?
IRSA (IAM Roles for Service Accounts) allows Kubernetes pods to assume IAM roles without storing credentials. Uses OIDC federation — EKS issues tokens, AWS STS validates them. Each pod gets its own IAM role with least-privilege permissions. Much more secure than node-level IAM roles (which grant all pods on a node the same permissions).
