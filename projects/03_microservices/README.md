# Project 03: Microservices Architecture on EKS

## Architecture

```
Internet
    ↓
Route 53
    ↓
ALB (AWS Load Balancer Controller)
    ↓
EKS Cluster
├── Ingress (ALB Ingress Controller)
├── Order Service (3 replicas)
├── Payment Service (3 replicas)
├── Inventory Service (3 replicas)
├── Notification Service (2 replicas)
└── API Gateway Service (3 replicas)
    ↓
Data Layer
├── RDS Aurora PostgreSQL (per service DB)
├── ElastiCache Redis (shared cache)
└── SQS (async messaging between services)
```

## Services

| Service | Language | DB | Port |
|---------|---------|-----|------|
| order-service | Python | Aurora PostgreSQL | 8080 |
| payment-service | Node.js | Aurora PostgreSQL | 8081 |
| inventory-service | Python | DynamoDB | 8082 |
| notification-service | Python | - (SQS consumer) | 8083 |
| api-gateway | Python | - (proxy) | 80 |

## EKS Cluster Setup

```bash
# Create EKS cluster
eksctl create cluster \
  --name microservices-prod \
  --region us-east-1 \
  --nodegroup-name standard \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --with-oidc \
  --alb-ingress-access \
  --full-ecr-access

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=microservices-prod \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Install metrics server (for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## Kubernetes Manifests

### Order Service Deployment

```yaml
# k8s/order-service/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: production
  labels:
    app: order-service
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: order-service
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: order-service-sa
      containers:
        - name: order-service
          image: 123456789.dkr.ecr.us-east-1.amazonaws.com/order-service:v1.2.0
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
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: order-db-secret
                  key: host
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: order-db-secret
                  key: password
            - name: REDIS_HOST
              value: "redis.production.svc.cluster.local"
            - name: SQS_QUEUE_URL
              valueFrom:
                configMapKeyRef:
                  name: order-service-config
                  key: sqs_queue_url
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: order-service
---
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: production
spec:
  selector:
    app: order-service
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  minReplicas: 3
  maxReplicas: 30
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

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: microservices-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789:certificate/abc-123
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:123456789:regional/webacl/prod/abc123
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/load-balancer-attributes: |
      idle_timeout.timeout_seconds=60,
      access_logs.s3.enabled=true,
      access_logs.s3.bucket=my-alb-logs
spec:
  rules:
    - host: api.myapp.com
      http:
        paths:
          - path: /orders
            pathType: Prefix
            backend:
              service:
                name: order-service
                port:
                  number: 80
          - path: /payments
            pathType: Prefix
            backend:
              service:
                name: payment-service
                port:
                  number: 80
          - path: /inventory
            pathType: Prefix
            backend:
              service:
                name: inventory-service
                port:
                  number: 80
```

### IRSA for Service Account

```bash
# Create IAM role for order-service pod
eksctl create iamserviceaccount \
  --name order-service-sa \
  --namespace production \
  --cluster microservices-prod \
  --attach-policy-arn arn:aws:iam::123456789:policy/OrderServicePolicy \
  --approve

# OrderServicePolicy allows:
# - sqs:SendMessage, sqs:ReceiveMessage, sqs:DeleteMessage
# - secretsmanager:GetSecretValue (for DB credentials)
# - dynamodb:GetItem, PutItem (if using DynamoDB)
```

## Service-to-Service Communication

```python
# Synchronous: HTTP via Kubernetes DNS
import httpx

async def check_inventory(product_id: str, quantity: int) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://inventory-service.production.svc.cluster.local/inventory/{product_id}",
            timeout=5.0
        )
        data = response.json()
        return data['available'] >= quantity

# Asynchronous: SQS
import boto3
sqs = boto3.client('sqs')

def publish_order_event(order_id: str, event_type: str):
    sqs.send_message(
        QueueUrl=os.environ['ORDER_EVENTS_QUEUE'],
        MessageBody=json.dumps({
            'orderId': order_id,
            'eventType': event_type,
            'timestamp': datetime.utcnow().isoformat()
        })
    )
```

## Deployment

```bash
# Build and push all services
for SERVICE in order-service payment-service inventory-service notification-service; do
  docker build -t $SERVICE:latest services/$SERVICE/
  docker tag $SERVICE:latest $ECR_REPO/$SERVICE:latest
  docker push $ECR_REPO/$SERVICE:latest
done

# Deploy to EKS
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/order-service/
kubectl apply -f k8s/payment-service/
kubectl apply -f k8s/inventory-service/
kubectl apply -f k8s/notification-service/
kubectl apply -f k8s/ingress.yaml

# Verify
kubectl get pods -n production
kubectl get ingress -n production
kubectl get hpa -n production
```

## Estimated Monthly Cost

| Component | Cost |
|-----------|------|
| EKS Control Plane | $73 |
| EC2 Worker Nodes (3x m5.large) | $210 |
| RDS Aurora (3 clusters) | $300 |
| ElastiCache Redis | $100 |
| ALB | $20 |
| ECR | $5 |
| **Total** | **~$708/month** |
