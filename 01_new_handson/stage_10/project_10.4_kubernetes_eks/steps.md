# Steps — Project 10.4 Kubernetes on EKS

## Phase 1 — Deploy EKS Cluster (from Project 6.5 terraform)

```bash
# Reuse the EKS cluster from Project 6.5
aws eks update-kubeconfig \
  --region us-east-1 \
  --name handson-eks-cluster

kubectl get nodes
kubectl get namespaces
```

---

## Phase 2 — Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace production

# Create secret (base64 encoded)
kubectl create secret generic flask-api-secrets \
  --namespace production \
  --from-literal=db_password=Admin@1234!

# Verify
kubectl get secrets -n production
```

---

## Phase 3 — Deploy Application

```bash
# Apply all manifests
kubectl apply -f k8s/deployment.yaml

# Watch rollout
kubectl rollout status deployment/flask-api -n production

# Check pods
kubectl get pods -n production -o wide

# Check service
kubectl get svc -n production

# Check ingress (ALB URL)
kubectl get ingress -n production
```

---

## Phase 4 — Test HPA (Auto-scaling)

```bash
# Generate load to trigger HPA
kubectl run load-generator \
  --image=busybox \
  --restart=Never \
  -n production \
  -- /bin/sh -c "while true; do wget -q -O- http://flask-api/health; done"

# Watch HPA scale up
kubectl get hpa -n production -w

# Stop load generator
kubectl delete pod load-generator -n production

# Watch HPA scale back down
kubectl get hpa -n production -w
```

---

## Phase 5 — Rolling Update

```bash
# Update image to new version
kubectl set image deployment/flask-api \
  flask-api=ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/handson-flask-api:2.0.0 \
  -n production

# Watch rolling update
kubectl rollout status deployment/flask-api -n production

# Rollback if needed
kubectl rollout undo deployment/flask-api -n production
```

---

## Phase 6 — RBAC

```bash
# Create read-only role for developers
kubectl apply -f - << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-read
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
EOF
```

---

## Screenshots to Take
- [ ] EKS cluster nodes running
- [ ] Pods spread across AZs
- [ ] HPA scaling up under load
- [ ] Rolling update in progress
- [ ] Ingress showing ALB URL
- [ ] `kubectl top pods` showing resource usage
