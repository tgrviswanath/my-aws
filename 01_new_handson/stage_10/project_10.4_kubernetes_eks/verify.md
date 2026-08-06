# Verification & Validation — Project 10.4 Kubernetes on EKS

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| EKS Cluster | EKS → Clusters | `handson-eks` Status = **Active** |
| Node Group | EKS → Clusters → `handson-eks` → Compute | Node group Status = **Active**, nodes = desired count |
| ALB Ingress | EC2 → Load Balancers | ALB created by AWS Load Balancer Controller |
| ECR Repository | ECR → Repositories | `handson-api` repository exists |
| IAM OIDC Provider | IAM → Identity providers | OIDC provider for EKS cluster listed |

📸 Screenshot: EKS cluster Active with node group  
📸 Screenshot: `kubectl get pods -n handson` showing Running pods  
📸 Screenshot: `kubectl get ingress -n handson` showing ALB address  
📸 Screenshot: curl to ALB returning 200 response

---

## 2. AWS CLI + kubectl Verification

```bash
# 2.1 Confirm EKS cluster is active
aws eks describe-cluster \
  --name handson-eks \
  --query "cluster.{Status:status,Version:version,Endpoint:endpoint}"
# Expected: status=ACTIVE, version=1.28+

# 2.2 Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name handson-eks
# Expected: kubeconfig updated

# 2.3 Confirm nodes are ready
kubectl get nodes -o wide
# Expected: all nodes Status=Ready

# 2.4 Apply manifests
kubectl apply -f k8s/
# Expected: namespace/handson created, deployment/handson-api created, etc.

# 2.5 Check pods are running
kubectl get pods -n handson -o wide
# Expected: all pods Status=Running, Ready=1/1

# 2.6 Check deployment
kubectl get deployment handson-api -n handson \
  -o jsonpath='{.status.readyReplicas}/{.spec.replicas}'
# Expected: 2/2 (or desired/desired)

# 2.7 Check service
kubectl get svc -n handson
# Expected: handson-api service listed with ClusterIP

# 2.8 Check ingress and ALB
kubectl get ingress -n handson
# Expected: ADDRESS column shows ALB DNS name

# 2.9 Check HPA
kubectl get hpa -n handson
# Expected: HPA listed with TARGETS and MINPODS/MAXPODS

# 2.10 Test application via ALB
ALB_DNS=$(kubectl get ingress -n handson \
  -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/health
# Expected: 200

# 2.11 Check IRSA (IAM Roles for Service Accounts)
kubectl get serviceaccount -n handson -o yaml | grep "eks.amazonaws.com/role-arn"
# Expected: IAM role ARN annotation present

# 2.12 Check node group
aws eks describe-nodegroup \
  --cluster-name handson-eks \
  --nodegroup-name handson-nodes \
  --query "nodegroup.{Status:status,DesiredSize:scalingConfig.desiredSize,InstanceType:instanceTypes[0]}"
# Expected: status=ACTIVE
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_eks_cluster.main
# aws_eks_node_group.main
# aws_iam_role.eks_cluster
# aws_iam_role.eks_nodes
# aws_iam_openid_connect_provider.eks
# aws_vpc.main (or data source)
# aws_subnet.private[0]
# aws_subnet.private[1]

terraform state show aws_eks_cluster.main
# Shows: name=handson-eks, version, role_arn, vpc_config

terraform output cluster_name
# Expected: handson-eks

terraform output cluster_endpoint
# Expected: https://xxx.gr7.us-east-1.eks.amazonaws.com

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Pod Scaling Test

```bash
# Check current HPA state
kubectl get hpa -n handson

# Generate load to trigger HPA scaling
kubectl run load-generator \
  --image=busybox \
  --restart=Never \
  --rm -it \
  -n handson \
  -- /bin/sh -c "while true; do wget -q -O- http://handson-api/health; done" &

# Watch HPA scale up (takes ~2-3 minutes)
kubectl get hpa -n handson -w
# Expected: REPLICAS increases from 2 toward max

# Stop load generator
kubectl delete pod load-generator -n handson 2>/dev/null

# Watch HPA scale back down
kubectl get hpa -n handson -w
# Expected: REPLICAS decreases back to min after ~5 minutes

# Verify rolling update works
kubectl set image deployment/handson-api \
  handson-api=nginx:latest -n handson
kubectl rollout status deployment/handson-api -n handson
# Expected: "successfully rolled out"

# Rollback
kubectl rollout undo deployment/handson-api -n handson
kubectl rollout status deployment/handson-api -n handson
# Expected: "successfully rolled out"
```

---

## 5. Expected Successful Outputs

**kubectl get nodes:**
```
NAME                          STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ec2.internal    Ready    <none>   10m   v1.28.x
ip-10-0-2-xxx.ec2.internal    Ready    <none>   10m   v1.28.x
```

**kubectl get pods -n handson:**
```
NAME                           READY   STATUS    RESTARTS   AGE
handson-api-7d9f8b6c5-abc12    1/1     Running   0          5m
handson-api-7d9f8b6c5-def34    1/1     Running   0          5m
```

**kubectl get ingress -n handson:**
```
NAME          CLASS   HOSTS   ADDRESS                                    PORTS   AGE
handson-api   alb     *       k8s-handson-xxx.us-east-1.elb.amazonaws.com   80      5m
```

**curl ALB:**
```
HTTP/1.1 200 OK
{"status": "healthy", "version": "1.0.0"}
```

---

## 6. Verification Checklist

- [ ] EKS cluster `handson-eks` Status = ACTIVE
- [ ] Node group Status = ACTIVE, all nodes Ready
- [ ] `kubectl get pods -n handson` — all pods Running
- [ ] Deployment ready replicas = desired replicas
- [ ] Service exists in handson namespace
- [ ] Ingress has ALB DNS address
- [ ] `curl http://<ALB>/health` returns 200
- [ ] HPA configured with min/max replicas
- [ ] IRSA annotation on service account
- [ ] Rolling update completes successfully
- [ ] Rollback completes successfully
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
