# Steps — Project 11.2 Two-Tier Architecture with NAT Gateway

## Phase 1 — Console

### 1.1 Create VPC
- Name: `vpc-11-2`, CIDR: `10.0.0.0/16`, DNS hostnames: enabled

### 1.2 Create Subnets
| Name | CIDR | AZ | Type |
|------|------|----|------|
| public-subnet-11-2 | 10.0.1.0/24 | us-east-1a | Public |
| private-subnet-11-2 | 10.0.2.0/24 | us-east-1a | Private |

Enable auto-assign public IP on `public-subnet-11-2` only.

### 1.3 Create and Attach Internet Gateway
- Name: `igw-11-2` → attach to `vpc-11-2`

### 1.4 Create NAT Gateway
1. **VPC** → **NAT Gateways** → **Create**
2. Name: `nat-11-2`
3. Subnet: `public-subnet-11-2` ← must be public
4. Connectivity: Public
5. **Allocate Elastic IP** → Create
6. Wait for status: **Available**

### 1.5 Create Route Tables
**Public RT** (`public-rt-11-2`):
- Route: `0.0.0.0/0` → `igw-11-2`
- Associate: `public-subnet-11-2`

**Private RT** (`private-rt-11-2`):
- Route: `0.0.0.0/0` → `nat-11-2`
- Associate: `private-subnet-11-2`

### 1.6 Security Groups
- `sg-web-11-2`: allow SSH(22) from My IP, HTTP(80) from 0.0.0.0/0
- `sg-db-11-2`: allow SSH(22) from `sg-web-11-2` only (no public access)

### 1.7 Launch EC2 Instances
- Web EC2: public subnet, `sg-web-11-2`, public IP enabled
- DB EC2: private subnet, `sg-db-11-2`, no public IP

---

## Phase 2 — AWS CLI

```bash
# VPC
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=vpc-11-2
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Subnets
PUB=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB --tags Key=Name,Value=public-subnet-11-2
aws ec2 modify-subnet-attribute --subnet-id $PUB --map-public-ip-on-launch

PRIV=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV --tags Key=Name,Value=private-subnet-11-2

# IGW
IGW=$(aws ec2 create-internet-gateway \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC_ID
aws ec2 create-tags --resources $IGW --tags Key=Name,Value=igw-11-2

# NAT Gateway
EIP=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)
NAT=$(aws ec2 create-nat-gateway --subnet-id $PUB --allocation-id $EIP \
  --query "NatGateway.NatGatewayId" --output text)
aws ec2 create-tags --resources $NAT --tags Key=Name,Value=nat-11-2
echo "Waiting for NAT Gateway..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT

# Route tables
PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PUB_RT --tags Key=Name,Value=public-rt-11-2
aws ec2 create-route --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB

PRIV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PRIV_RT --tags Key=Name,Value=private-rt-11-2
aws ec2 create-route --route-table-id $PRIV_RT \
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV

echo "Done. VPC=$VPC_ID NAT=$NAT"
```

---

## Phase 3 — Terraform

```bash
cd terraform
terraform init && terraform apply
terraform output
```

---

## Phase 4 — Verify

```bash
# 1. Confirm NAT Gateway is available
aws ec2 describe-nat-gateways \
  --filter "Name=tag:Name,Values=nat-11-2" \
  --query "NatGateways[*].{ID:NatGatewayId,State:State,Subnet:SubnetId}"

# 2. Confirm private route table routes to NAT
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=private-rt-11-2" \
  --query "RouteTables[*].Routes"

# 3. SSH to web EC2, then hop to private EC2
ssh -i key.pem ec2-user@<WEB_PUBLIC_IP>
# From web EC2:
ssh -i key.pem ec2-user@<PRIVATE_EC2_IP>

# 4. From private EC2 — confirm outbound internet works via NAT
curl -s https://checkip.amazonaws.com   # returns NAT Gateway's public IP
ping -c 3 8.8.8.8                        # should succeed

# 5. Confirm private EC2 has NO public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ec2-db-11-2" \
  --query "Reservations[*].Instances[*].PublicIpAddress"
# Expected: empty / null

# 6. Run checker
python code/nat_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] VPC created with two subnets (public + private)
- [ ] NAT Gateway in public subnet with Elastic IP
- [ ] Public RT: `0.0.0.0/0 → igw`
- [ ] Private RT: `0.0.0.0/0 → nat`
- [ ] Web EC2 has public IP; DB EC2 has no public IP
- [ ] SSH to web EC2 succeeds
- [ ] From private EC2: `curl checkip.amazonaws.com` returns NAT's IP
- [ ] Cannot SSH directly to private EC2 from internet

---

## Teardown
```bash
terraform destroy
# NAT Gateway charges by the hour — destroy immediately after lab
```
