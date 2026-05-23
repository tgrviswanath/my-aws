# Verification & Validation — Project 11.15 Multi-Account Network Architecture

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| RAM Share | RAM → Resource shares (Management account) | `share-subnets-11-15`, Status = **Active** |
| Shared Subnets | VPC → Subnets (Dev account) | Subnets visible, Owner = Management account ID |
| Route 53 PHZ | Route 53 → Hosted zones (Management) | `internal.company.com`, Type = Private |
| PHZ VPC Association | Hosted zone → VPC associations | Dev VPC listed |
| Dev EC2 | EC2 → Instances (Dev account) | Running, IP in Management account's CIDR |

📸 Screenshot: RAM share showing Status = Active with shared subnet ARNs  
📸 Screenshot: Dev account Subnets list showing subnets owned by Management account ID  
📸 Screenshot: DNS resolution from Dev EC2 showing `app.internal.company.com` resolves correctly

---

## 2. AWS CLI Verification

```bash
MGMT_PROFILE=management
DEV_PROFILE=dev

# 2.1 RAM share is active
aws ram get-resource-shares \
  --resource-owner SELF \
  --profile $MGMT_PROFILE \
  --query "resourceShares[?name=='share-subnets-11-15'].{Name:name,Status:status}"
# Expected: Status=ACTIVE

# 2.2 Shared subnets visible in Dev account
aws ec2 describe-subnets \
  --profile $DEV_PROFILE \
  --query "Subnets[?OwnerId!='$(aws sts get-caller-identity --profile $DEV_PROFILE --query Account --output text)'].{ID:SubnetId,Owner:OwnerId,CIDR:CidrBlock,VPC:VpcId}"
# Expected: subnets owned by Management account ID

# 2.3 Dev EC2 uses shared subnet and gets correct IP
aws ec2 describe-instances \
  --profile $DEV_PROFILE \
  --query "Reservations[*].Instances[*].{ID:InstanceId,IP:PrivateIpAddress,Subnet:SubnetId}"
# Expected: IP in 10.0.1.0/24 (Management account's CIDR)

# 2.4 Dev account cannot modify shared subnet
aws ec2 delete-subnet --subnet-id $SUBNET_A --profile $DEV_PROFILE
# Expected: error — participant cannot modify owner's resources

# 2.5 DNS resolution from Dev EC2
# From Dev EC2:
nslookup app.internal.company.com
# Expected: resolves to 10.0.1.x (record in Management account's PHZ)
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected (uses two provider aliases):
# aws_vpc.shared                    (management provider)
# aws_subnet.shared_a               (management provider)
# aws_subnet.shared_b               (management provider)
# aws_ram_resource_share.main       (management provider)
# aws_ram_resource_association.a    (management provider)
# aws_ram_principal_association.dev (management provider)
# aws_route53_zone.internal         (management provider)
# aws_route53_record.app            (management provider)

terraform state show aws_ram_resource_share.main
# Shows: id, name, allow_external_principals=false

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Confirm Dev EC2 can communicate with Management EC2 (same VPC, different accounts)
# From Dev EC2:
ping -c 5 <MGMT_EC2_PRIVATE_IP>   # succeeds — same VPC, no peering needed

# Confirm Dev account cannot see Management account's private subnet (not shared)
aws ec2 describe-subnets \
  --filters "Name=cidr-block,Values=10.0.3.0/24" \
  --profile $DEV_PROFILE
# Expected: empty — private management subnet not shared
```

---

## 5. Expected Successful Outputs

**RAM share status:**
```json
[{ "Name": "share-subnets-11-15", "Status": "ACTIVE" }]
```

**Dev account subnets (showing shared subnets):**
```json
[
  { "ID": "subnet-0abc", "Owner": "111122223333", "CIDR": "10.0.1.0/24", "VPC": "vpc-0abc" },
  { "ID": "subnet-0def", "Owner": "111122223333", "CIDR": "10.0.2.0/24", "VPC": "vpc-0abc" }
]
```

**DNS resolution from Dev EC2:**
```
Server:   169.254.169.253
Address:  169.254.169.253#53
Name:     app.internal.company.com
Address:  10.0.1.x
```

---

## 6. Verification Checklist

- [ ] RAM sharing enabled in AWS Organizations
- [ ] RAM share status = ACTIVE
- [ ] Dev account can see shared subnets (owned by Management account)
- [ ] Dev EC2 launched in shared subnet gets IP in Management account's CIDR
- [ ] Dev EC2 can communicate with Management EC2 (same VPC)
- [ ] Route 53 PHZ associated with Dev VPC
- [ ] DNS resolution works from Dev EC2 for `internal.company.com`
- [ ] Dev account cannot delete/modify shared subnet (permission denied)
- [ ] Management account's private subnet NOT visible in Dev account
- [ ] `terraform plan` shows no changes
