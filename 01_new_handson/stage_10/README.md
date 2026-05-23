# Stage 10 — Advanced Cloud Architecture & Platform Engineering

> Master enterprise-grade AWS architecture: multi-account organizations, disaster recovery, cost optimization, Kubernetes on EKS, and a production microservices capstone platform.

---

## Projects

| # | Project | Key Services | Difficulty |
|---|---------|-------------|-----------|
| 10.1 | Multi-account AWS Organization | Organizations, SCPs, OUs, CloudTrail | ⭐⭐⭐ |
| 10.2 | Disaster Recovery Architecture | RDS Read Replica, S3 CRR, Route53 Failover | ⭐⭐⭐⭐ |
| 10.3 | Cost Optimization Automation | Budgets, Compute Optimizer, Lambda, EventBridge | ⭐⭐⭐ |
| 10.4 | Kubernetes on EKS | EKS, ALB Ingress, HPA, IRSA, kubectl | ⭐⭐⭐⭐ |
| 10.5 | Production Microservices Platform | ECS, API Gateway, CloudFront, WAF, Kinesis, RDS, Redis | ⭐⭐⭐⭐⭐ |

---

## Folder Structure

```
stage_10/
├── project_10.1_multi_account_org/
│   ├── code/org_manager.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_10.2_disaster_recovery/
│   ├── code/dr_failover.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_10.3_cost_optimization/
│   ├── src/cost_optimizer.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_10.4_kubernetes_eks/
│   ├── k8s/deployment.yaml
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
└── project_10.5_microservices_platform/
    ├── code/platform_health.py
    ├── terraform/main.tf
    ├── README.md  |  steps.md  |  verify.md ✅
```

---

## Quick Start

```bash
# Multi-account org (requires Organizations access)
cd project_10.1_multi_account_org/terraform
terraform init && terraform apply
python code/org_manager.py list-accounts

# EKS cluster
cd project_10.4_kubernetes_eks/terraform
terraform init && terraform apply
aws eks update-kubeconfig --region us-east-1 --name handson-eks
kubectl apply -f k8s/
kubectl get pods -n handson
```

---

## Architecture Concepts Covered

| Concept | Project | Key Takeaway |
|---------|---------|-------------|
| Multi-account governance | 10.1 | SCPs restrict what IAM can allow — defense in depth |
| Disaster recovery | 10.2 | RTO/RPO targets drive architecture choices |
| FinOps | 10.3 | Tag everything — you can't optimize what you can't identify |
| Kubernetes | 10.4 | IRSA for pod AWS permissions — no node-level IAM |
| Microservices | 10.5 | Each service owns its data — no shared databases |

---

## 7. Verification & Validation

Every project in Stage 10 has a `verify.md` covering:

- **AWS Console verification** — what to check and expected state for each resource
- **AWS CLI verification commands** — exact commands with expected outputs
- **Terraform state verification** — `terraform state list`, `terraform state show`, `terraform output`, `terraform plan`
- **Logs / monitoring checks** — SCP enforcement, DR replica lag, EKS pod health, platform health dashboard
- **Expected successful outputs** — exact JSON / text output to compare against
- **Health check procedures** — end-to-end tests (SCP enforcement, DR readiness, HPA scaling, platform health)
- **Verification checklist** — checkbox list to tick off before marking project complete

### Quick Verification Reference

| Project | Key CLI Check | Expected Result |
|---------|--------------|-----------------|
| 10.1 Multi-account | `aws organizations list-accounts` | All accounts ACTIVE |
| 10.2 DR | `python code/dr_failover.py test --primary us-east-1 --dr us-west-2` | DR Status = READY |
| 10.3 Cost | `python src/cost_optimizer.py --dry-run` | Savings opportunities listed |
| 10.4 EKS | `kubectl get pods -n handson` | All pods Running |
| 10.5 Platform | `python code/platform_health.py` | ALL SYSTEMS HEALTHY |

---

## Key Lessons

- **SCPs are deny-only**: SCP + IAM = effective permissions — both must allow the action
- **Management account exempt from SCPs**: be very careful with management account permissions
- **Test DR regularly**: untested DR plans fail when you need them — schedule quarterly DR drills
- **RDS promotion takes ~5 minutes**: factor this into your RTO calculation
- **EKS control plane costs $72/month**: always running — use Fargate profiles for dev to save costs
- **IRSA over node IAM**: pods get scoped AWS permissions — no over-privileged node roles
- **Microservices data isolation**: each service owns its DB — no cross-service DB queries
- **Cost tagging is the foundation**: enforce tags via SCPs and Config rules from day 1

---

## Certification Alignment

| Cert | Relevant Projects |
|------|------------------|
| AWS Solutions Architect Professional | 10.1, 10.2, 10.3, 10.5 |
| AWS DevOps Engineer Professional | 10.1, 10.4, 10.5 |
| AWS SysOps Administrator | 10.2, 10.3 |
| CKA (Kubernetes) | 10.4 |
