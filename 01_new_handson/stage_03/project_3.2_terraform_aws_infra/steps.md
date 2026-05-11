# Steps — Project 3.2 Terraform AWS Infrastructure

## Phase 1 — Plan and Review

```bash
cd terraform

# Initialize
terraform init

# Format and validate
terraform fmt -recursive
terraform validate

# Preview everything that will be created
terraform plan -var-file="terraform.tfvars"

# Count resources in the plan
terraform plan -var-file="terraform.tfvars" | grep "will be created" | wc -l
```

---

## Phase 2 — Apply in Stages (recommended for learning)

```bash
# Apply only the VPC first
terraform apply -target=module.vpc -var-file="terraform.tfvars"

# Then apply security groups
terraform apply -target=aws_security_group.alb \
                -target=aws_security_group.app \
                -target=aws_security_group.rds \
                -var-file="terraform.tfvars"

# Then apply everything else
terraform apply -var-file="terraform.tfvars"
```

---

## Phase 3 — Verify

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "ALB: http://$ALB_DNS"

# Test the application
curl http://$ALB_DNS
curl http://$ALB_DNS/health

# Run multiple times to see load balancing
for i in {1..5}; do curl -s http://$ALB_DNS | grep "hostname"; done

# Verify RDS is in private subnet (not publicly accessible)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
echo "RDS endpoint: $RDS_ENDPOINT"
# Try to connect from your laptop — should FAIL (private subnet)
mysql -h $RDS_ENDPOINT -u admin -p
# Expected: timeout (good — it's private)
```

---

## Phase 4 — Make a Change (Terraform Update Workflow)

```bash
# Change desired EC2 count from 2 to 3
# Edit terraform.tfvars: desired_capacity = 3

terraform plan -var-file="terraform.tfvars"
# Shows: ~ aws_autoscaling_group.app will be updated in-place

terraform apply -var-file="terraform.tfvars"

# Verify 3 instances are now running
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names handson-asg \
  --query "AutoScalingGroups[0].Instances[*].InstanceId"
```

---

## Phase 5 — Save and Apply a Plan File

```bash
# Save plan to file (useful in CI/CD — plan in PR, apply on merge)
terraform plan -var-file="terraform.tfvars" -out=infra.tfplan

# Review the saved plan
terraform show infra.tfplan

# Apply exactly the saved plan (no surprises)
terraform apply infra.tfplan
```

---

## Phase 6 — Destroy

```bash
# Preview what will be destroyed
terraform plan -destroy -var-file="terraform.tfvars"

# Destroy all resources
terraform destroy -var-file="terraform.tfvars"

# Verify nothing is left
terraform state list
# Expected: empty
```

---

## Screenshots to Take
- [ ] `terraform plan` showing all resources to create
- [ ] `terraform apply` completion with outputs
- [ ] ALB DNS responding in browser
- [ ] Load balancing working (different hostnames on refresh)
- [ ] `terraform state list` showing all managed resources
- [ ] `terraform destroy` completion
