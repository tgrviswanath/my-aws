# Steps — Project 2.1 Custom VPC Architecture

## Phase 1 — Console

### 1.1 Create VPC
1. Go to **VPC** → **Your VPCs** → **Create VPC**
2. Name: `handson-vpc`
3. IPv4 CIDR: `10.0.0.0/16`
4. Tenancy: Default
5. Create

### 1.2 Create Subnets
Create 6 subnets (2 per tier, spread across 2 AZs):

| Name | CIDR | AZ | Tier |
|------|------|----|------|
| public-subnet-a | 10.0.1.0/24 | us-east-1a | Web |
| public-subnet-b | 10.0.2.0/24 | us-east-1b | Web |
| private-app-a | 10.0.3.0/24 | us-east-1a | App |
| private-app-b | 10.0.4.0/24 | us-east-1b | App |
| private-db-a | 10.0.5.0/24 | us-east-1a | DB |
| private-db-b | 10.0.6.0/24 | us-east-1b | DB |

For each: **VPC** → **Subnets** → **Create subnet** → select `handson-vpc`

### 1.3 Create Internet Gateway
1. **VPC** → **Internet Gateways** → **Create**
2. Name: `handson-igw`
3. After creation: **Actions** → **Attach to VPC** → select `handson-vpc`

### 1.4 Create NAT Gateway
1. **VPC** → **NAT Gateways** → **Create**
2. Name: `handson-nat`
3. Subnet: `public-subnet-a` (NAT must be in a PUBLIC subnet)
4. Connectivity: Public
5. Allocate Elastic IP → Create
6. Wait for status: Available (~1 minute)

### 1.5 Create Route Tables

**Public Route Table:**
1. **VPC** → **Route Tables** → **Create**
2. Name: `public-rt`, VPC: `handson-vpc`
3. Routes tab → **Edit routes** → Add:
   - Destination: `0.0.0.0/0`, Target: `handson-igw`
4. Subnet associations → Associate `public-subnet-a` and `public-subnet-b`

**Private Route Table:**
1. Create another route table: `private-rt`
2. Routes → Add: `0.0.0.0/0` → `handson-nat`
3. Associate all 4 private subnets

---

## Phase 2 — AWS CLI

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=handson-vpc
echo "VPC: $VPC_ID"

# Enable DNS hostnames (needed for RDS, ECS, etc.)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create public subnets
PUB_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB_A --tags Key=Name,Value=public-subnet-a

PUB_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB_B --tags Key=Name,Value=public-subnet-b

# Create private subnets
PRIV_APP_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_APP_A --tags Key=Name,Value=private-app-a

PRIV_APP_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_APP_B --tags Key=Name,Value=private-app-b

PRIV_DB_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.5.0/24 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_DB_A --tags Key=Name,Value=private-db-a

PRIV_DB_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.6.0/24 \
  --availability-zone us-east-1b \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_DB_B --tags Key=Name,Value=private-db-b

# Create and attach Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=handson-igw

# Allocate Elastic IP and create NAT Gateway
EIP=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)
NAT_ID=$(aws ec2 create-nat-gateway \
  --subnet-id $PUB_A \
  --allocation-id $EIP \
  --query "NatGateway.NatGatewayId" --output text)
aws ec2 create-tags --resources $NAT_ID --tags Key=Name,Value=handson-nat
echo "Waiting for NAT Gateway..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_ID

# Public route table
PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PUB_RT --tags Key=Name,Value=public-rt
aws ec2 create-route --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_A
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_B

# Private route table
PRIV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PRIV_RT --tags Key=Name,Value=private-rt
aws ec2 create-route --route-table-id $PRIV_RT \
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_ID
for SUBNET in $PRIV_APP_A $PRIV_APP_B $PRIV_DB_A $PRIV_DB_B; do
  aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $SUBNET
done

echo "VPC setup complete!"
echo "VPC ID: $VPC_ID"
```

---

## Phase 3 — Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply

# View outputs
terraform output
```

---

## Phase 4 — Verify

```bash
# Verify VPC exists
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=handson-vpc"

# Verify subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,CIDR:CidrBlock,AZ:AvailabilityZone}"

# Verify route tables
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,Routes:Routes[*].DestinationCidrBlock}"

# Test: launch EC2 in private subnet and verify it can reach internet via NAT
# (it should be able to run: curl https://example.com)
```

---

## Screenshots to Take
- [ ] VPC created with correct CIDR
- [ ] All 6 subnets visible with correct CIDRs and AZs
- [ ] Internet Gateway attached to VPC
- [ ] NAT Gateway in Available state with Elastic IP
- [ ] Public route table showing `0.0.0.0/0 → igw-xxx`
- [ ] Private route table showing `0.0.0.0/0 → nat-xxx`
- [ ] `terraform apply` success with all outputs
