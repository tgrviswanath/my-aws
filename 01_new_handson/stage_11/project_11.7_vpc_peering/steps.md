# Steps — Project 11.7 VPC Peering Connection

## Phase 1 — Console

### 1.1 Create VPC-A
- Name: `vpc-a-11-7`, CIDR: `10.0.0.0/16`
- Subnet: `subnet-a-11-7`, CIDR: `10.0.1.0/24`, AZ: us-east-1a
- IGW: `igw-a-11-7`, attach to VPC-A
- Route table: `rt-a-11-7`, route `0.0.0.0/0 → igw-a-11-7`

### 1.2 Create VPC-B
- Name: `vpc-b-11-7`, CIDR: `10.1.0.0/16`
- Subnet: `subnet-b-11-7`, CIDR: `10.1.1.0/24`, AZ: us-east-1b
- IGW: `igw-b-11-7`, attach to VPC-B
- Route table: `rt-b-11-7`, route `0.0.0.0/0 → igw-b-11-7`

### 1.3 Create VPC Peering Connection
1. **VPC** → **Peering Connections** → **Create peering connection**
2. Name: `pcx-11-7`
3. Requester VPC: `vpc-a-11-7`
4. Accepter VPC: `vpc-b-11-7` (same account, same region)
5. Create
6. Select the peering connection → **Actions** → **Accept request**

### 1.4 Update Route Tables on BOTH sides
**VPC-A route table** (`rt-a-11-7`):
- Add route: `10.1.0.0/16` → `pcx-11-7`

**VPC-B route table** (`rt-b-11-7`):
- Add route: `10.0.0.0/16` → `pcx-11-7`

### 1.5 Update Security Groups
- EC2-A SG: allow ICMP + SSH from `10.1.0.0/16`
- EC2-B SG: allow ICMP + SSH from `10.0.0.0/16`

### 1.6 Launch EC2 in Each VPC
- EC2-A: `subnet-a-11-7`, public IP enabled
- EC2-B: `subnet-b-11-7`, public IP enabled

---

## Phase 2 — AWS CLI

```bash
# Create VPC-A
VPC_A=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_A --tags Key=Name,Value=vpc-a-11-7

# Create VPC-B
VPC_B=$(aws ec2 create-vpc --cidr-block 10.1.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_B --tags Key=Name,Value=vpc-b-11-7

# Create subnets
SUBNET_A=$(aws ec2 create-subnet --vpc-id $VPC_A --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
SUBNET_B=$(aws ec2 create-subnet --vpc-id $VPC_B --cidr-block 10.1.1.0/24 \
  --availability-zone us-east-1b --query "Subnet.SubnetId" --output text)

# Create peering connection
PCX=$(aws ec2 create-vpc-peering-connection \
  --vpc-id $VPC_A --peer-vpc-id $VPC_B \
  --query "VpcPeeringConnection.VpcPeeringConnectionId" --output text)
aws ec2 create-tags --resources $PCX --tags Key=Name,Value=pcx-11-7

# Accept peering
aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id $PCX

# Get route table IDs
RT_A=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_A" "Name=association.main,Values=true" \
  --query "RouteTables[0].RouteTableId" --output text)
RT_B=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_B" "Name=association.main,Values=true" \
  --query "RouteTables[0].RouteTableId" --output text)

# Add routes on BOTH sides
aws ec2 create-route --route-table-id $RT_A \
  --destination-cidr-block 10.1.0.0/16 --vpc-peering-connection-id $PCX
aws ec2 create-route --route-table-id $RT_B \
  --destination-cidr-block 10.0.0.0/16 --vpc-peering-connection-id $PCX

echo "Peering: $PCX  VPC-A: $VPC_A  VPC-B: $VPC_B"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check peering connection status
aws ec2 describe-vpc-peering-connections \
  --filters "Name=tag:Name,Values=pcx-11-7" \
  --query "VpcPeeringConnections[*].{ID:VpcPeeringConnectionId,Status:Status.Code}"
# Expected: active

# 2. Check routes in VPC-A RT
aws ec2 describe-route-tables --route-table-ids $RT_A \
  --query "RouteTables[0].Routes[*].{Dest:DestinationCidrBlock,Target:VpcPeeringConnectionId}"

# 3. Check routes in VPC-B RT
aws ec2 describe-route-tables --route-table-ids $RT_B \
  --query "RouteTables[0].Routes[*].{Dest:DestinationCidrBlock,Target:VpcPeeringConnectionId}"

# 4. SSH to EC2-A, ping EC2-B's private IP
ssh -i key.pem ec2-user@<EC2_A_PUBLIC_IP>
ping -c 3 <EC2_B_PRIVATE_IP>    # should succeed
ssh ec2-user@<EC2_B_PRIVATE_IP> # should succeed (if SG allows)

# 5. Verify non-transitivity — create VPC-C, peer with VPC-B only
# EC2-A should NOT be able to reach EC2-C (no direct peering)

# 6. Run peering checker
python code/peering_checker.py --vpc-a $VPC_A --vpc-b $VPC_B
```

### Verification Checklist
- [ ] VPC-A and VPC-B created with non-overlapping CIDRs
- [ ] Peering connection status = active
- [ ] VPC-A route table has `10.1.0.0/16 → pcx-xxx`
- [ ] VPC-B route table has `10.0.0.0/16 → pcx-xxx`
- [ ] Security groups allow ICMP from the other VPC's CIDR
- [ ] Ping from EC2-A to EC2-B private IP succeeds
- [ ] SSH from EC2-A to EC2-B private IP succeeds
- [ ] Non-transitivity confirmed (A cannot reach C via B)

---

## Teardown
```bash
terraform destroy
```
