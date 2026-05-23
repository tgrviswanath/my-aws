# Steps — Project 11.15 Multi-Account Network Architecture

## Prerequisites
- AWS Organizations enabled with at least 2 accounts (Management + Dev)
- RAM sharing enabled in Organizations settings
- AWS CLI profiles configured for each account

## Phase 1 — Console

### 1.1 Enable RAM in Organizations
1. **AWS Organizations** → **Services** → **Resource Access Manager** → Enable
2. This allows RAM shares to be accepted automatically within the org

### 1.2 Create Shared VPC (in Management/Network Account)
- VPC: `vpc-shared-11-15`, CIDR: `10.0.0.0/16`
- Shared subnet A: `shared-subnet-a-11-15`, `10.0.1.0/24`, us-east-1a
- Shared subnet B: `shared-subnet-b-11-15`, `10.0.2.0/24`, us-east-1b
- Private subnet (not shared): `private-mgmt-11-15`, `10.0.3.0/24`
- IGW, NAT Gateway, route tables

### 1.3 Share Subnets via RAM
1. **RAM** → **Resource shares** → **Create resource share**
2. Name: `share-subnets-11-15`
3. Resources: select `shared-subnet-a-11-15` and `shared-subnet-b-11-15`
4. Principals: add Dev account ID (or entire OU)
5. Create

### 1.4 Accept RAM Share (in Dev Account)
1. Switch to Dev account
2. **RAM** → **Shared with me** → find the share → **Accept**
3. Shared subnets now appear in Dev account's subnet list

### 1.5 Launch EC2 in Dev Account Using Shared Subnet
1. In Dev account: **EC2** → **Launch Instance**
2. Network: `vpc-shared-11-15` (visible because subnet is shared)
3. Subnet: `shared-subnet-a-11-15`
4. Launch — EC2 is in Dev account but uses Management account's VPC

### 1.6 Create Centralized Route 53 Private Hosted Zone
1. In Management account: **Route 53** → **Hosted zones** → **Create**
2. Name: `internal.company.com`
3. Type: Private
4. VPC: `vpc-shared-11-15`
5. Create records: `app.internal.company.com → 10.0.1.x`

### 1.7 Associate PHZ with Dev Account VPC
1. In Management account, authorize association:
```bash
aws route53 create-vpc-association-authorization \
  --hosted-zone-id <PHZ_ID> \
  --vpc VPCRegion=us-east-1,VPCId=<DEV_VPC_ID>
```
2. In Dev account, associate:
```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <PHZ_ID> \
  --vpc VPCRegion=us-east-1,VPCId=<DEV_VPC_ID>
```

---

## Phase 2 — AWS CLI

```bash
# --- Management Account ---
MGMT_PROFILE=management
DEV_ACCOUNT_ID=<dev-account-id>

# Create shared VPC
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --profile $MGMT_PROFILE --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --profile $MGMT_PROFILE \
  --tags Key=Name,Value=vpc-shared-11-15

# Create shared subnets
SUBNET_A=$(aws ec2 create-subnet --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 --availability-zone us-east-1a \
  --profile $MGMT_PROFILE --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $SUBNET_A --profile $MGMT_PROFILE \
  --tags Key=Name,Value=shared-subnet-a-11-15

# Create RAM share
SHARE_ARN=$(aws ram create-resource-share \
  --name share-subnets-11-15 \
  --resource-arns \
    arn:aws:ec2:us-east-1:$(aws sts get-caller-identity --profile $MGMT_PROFILE --query Account --output text):subnet/$SUBNET_A \
  --principals $DEV_ACCOUNT_ID \
  --profile $MGMT_PROFILE \
  --query "resourceShare.resourceShareArn" --output text)
echo "RAM Share: $SHARE_ARN"

# --- Dev Account ---
DEV_PROFILE=dev

# Accept RAM share (if not auto-accepted via Organizations)
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn <INVITATION_ARN> \
  --profile $DEV_PROFILE

# Verify shared subnet is visible in Dev account
aws ec2 describe-subnets \
  --filters "Name=subnet-id,Values=$SUBNET_A" \
  --profile $DEV_PROFILE \
  --query "Subnets[*].{ID:SubnetId,Owner:OwnerId,VPC:VpcId}"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
# Requires two AWS provider configurations (management + dev accounts)
```

---

## Phase 4 — Verify

```bash
# 1. Confirm RAM share is active
aws ram get-resource-shares \
  --resource-owner SELF \
  --profile $MGMT_PROFILE \
  --query "resourceShares[?name=='share-subnets-11-15'].{Name:name,Status:status}"
# Expected: ACTIVE

# 2. Confirm shared subnets visible in Dev account
aws ec2 describe-subnets \
  --profile $DEV_PROFILE \
  --query "Subnets[?OwnerId!='$(aws sts get-caller-identity --profile $DEV_PROFILE --query Account --output text)'].{ID:SubnetId,Owner:OwnerId,CIDR:CidrBlock}"
# Should show subnets owned by Management account

# 3. Confirm Route 53 PHZ is associated with Dev VPC
aws route53 list-vpc-association-authorizations \
  --hosted-zone-id <PHZ_ID> \
  --profile $MGMT_PROFILE

# 4. Confirm DNS resolution works in Dev account
# From Dev EC2: nslookup app.internal.company.com
# Expected: resolves to 10.0.1.x
```

---

## Phase 5 — Test

```bash
# Test 1: Launch EC2 in Dev account using shared subnet
# Verify it gets an IP in 10.0.1.0/24 (Management account's CIDR)
aws ec2 describe-instances \
  --profile $DEV_PROFILE \
  --query "Reservations[*].Instances[*].{ID:InstanceId,IP:PrivateIpAddress,Subnet:SubnetId}"

# Test 2: Dev EC2 can reach Management EC2 (same VPC, different accounts)
# From Dev EC2:
ping -c 5 <MGMT_EC2_PRIVATE_IP>
# Expected: success — same VPC, no peering needed

# Test 3: DNS resolution across accounts
# From Dev EC2:
nslookup app.internal.company.com
# Expected: returns 10.0.1.x (record created in Management account's PHZ)

# Test 4: Dev account CANNOT modify the shared VPC
aws ec2 delete-subnet --subnet-id $SUBNET_A --profile $DEV_PROFILE
# Expected: error — participant cannot modify owner's resources

# Test 5: Dev account CAN launch resources in shared subnet
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro \
  --subnet-id $SUBNET_A \
  --profile $DEV_PROFILE
# Expected: success

# Run automated checker
python code/multiaccnt_checker.py \
  --share-name share-subnets-11-15 \
  --profile-mgmt $MGMT_PROFILE \
  --profile-dev $DEV_PROFILE
```

### Verification Checklist
- [ ] RAM sharing enabled in AWS Organizations
- [ ] Shared VPC created in Management account
- [ ] RAM share created with shared subnets
- [ ] Dev account can see shared subnets
- [ ] EC2 launched in Dev account using shared subnet gets correct IP
- [ ] Dev EC2 can communicate with Management EC2 (same VPC)
- [ ] Route 53 PHZ associated with Dev VPC
- [ ] DNS resolution works from Dev EC2 for `internal.company.com`
- [ ] Dev account cannot delete/modify shared subnet (permission denied)

---

## Teardown
```bash
terraform destroy
# Also: disassociate PHZ from Dev VPC, delete RAM share
```
