# Steps — Project 11.10 Multi-Region VPC Architecture

## Phase 1 — Console

### 1.1 Create VPC in us-east-1
- Switch region to **us-east-1**
- VPC: `vpc-east-11-10`, CIDR: `10.0.0.0/16`
- Subnet: `subnet-east-11-10`, `10.0.1.0/24`, us-east-1a
- IGW: `igw-east-11-10`, attach to VPC
- Route table with `0.0.0.0/0 → igw`

### 1.2 Create VPC in us-west-2
- Switch region to **us-west-2**
- VPC: `vpc-west-11-10`, CIDR: `10.1.0.0/16`
- Subnet: `subnet-west-11-10`, `10.1.1.0/24`, us-west-2a
- IGW: `igw-west-11-10`, attach to VPC
- Route table with `0.0.0.0/0 → igw`

### 1.3 Create Inter-Region VPC Peering
1. In **us-east-1**: **VPC** → **Peering Connections** → **Create**
2. Name: `pcx-east-west-11-10`
3. Requester VPC: `vpc-east-11-10` (us-east-1)
4. Accepter: **Another region** → us-west-2
5. Accepter VPC ID: `<vpc-west-11-10-id>`
6. Create

### 1.4 Accept Peering in us-west-2
1. Switch to **us-west-2**
2. **VPC** → **Peering Connections** → find pending request
3. **Actions** → **Accept request**

### 1.5 Update Route Tables on BOTH sides
- **us-east-1** route table: add `10.1.0.0/16 → pcx-east-west-11-10`
- **us-west-2** route table: add `10.0.0.0/16 → pcx-east-west-11-10`

### 1.6 Update Security Groups
- East EC2 SG: allow ICMP + SSH from `10.1.0.0/16`
- West EC2 SG: allow ICMP + SSH from `10.0.0.0/16`

---

## Phase 2 — AWS CLI

```bash
# Create VPC in us-east-1
VPC_EAST=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --region us-east-1 --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_EAST --region us-east-1 \
  --tags Key=Name,Value=vpc-east-11-10

# Create VPC in us-west-2
VPC_WEST=$(aws ec2 create-vpc --cidr-block 10.1.0.0/16 \
  --region us-west-2 --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_WEST --region us-west-2 \
  --tags Key=Name,Value=vpc-west-11-10

# Create inter-region peering (from us-east-1)
PCX=$(aws ec2 create-vpc-peering-connection \
  --vpc-id $VPC_EAST \
  --peer-vpc-id $VPC_WEST \
  --peer-region us-west-2 \
  --region us-east-1 \
  --query "VpcPeeringConnection.VpcPeeringConnectionId" --output text)
aws ec2 create-tags --resources $PCX --region us-east-1 \
  --tags Key=Name,Value=pcx-east-west-11-10

# Accept from us-west-2
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id $PCX \
  --region us-west-2

# Add routes on both sides
RT_EAST=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_EAST" "Name=association.main,Values=true" \
  --region us-east-1 --query "RouteTables[0].RouteTableId" --output text)
RT_WEST=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_WEST" "Name=association.main,Values=true" \
  --region us-west-2 --query "RouteTables[0].RouteTableId" --output text)

aws ec2 create-route --route-table-id $RT_EAST \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id $PCX --region us-east-1

aws ec2 create-route --route-table-id $RT_WEST \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id $PCX --region us-west-2

echo "Peering: $PCX  East: $VPC_EAST  West: $VPC_WEST"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check peering status from both regions
aws ec2 describe-vpc-peering-connections \
  --filters "Name=tag:Name,Values=pcx-east-west-11-10" \
  --region us-east-1 \
  --query "VpcPeeringConnections[*].{ID:VpcPeeringConnectionId,Status:Status.Code}"
# Expected: active

# 2. Verify routes exist in both regions
aws ec2 describe-route-tables --route-table-ids $RT_EAST --region us-east-1 \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null]"

aws ec2 describe-route-tables --route-table-ids $RT_WEST --region us-west-2 \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null]"
```

---

## Phase 5 — Test

```bash
# SSH to EC2-East
ssh -i key.pem ec2-user@<EC2_EAST_PUBLIC_IP>

# Test 1: Ping EC2-West private IP (cross-region)
ping -c 5 <EC2_WEST_PRIVATE_IP>
# Expected: ~60-80ms RTT (us-east-1 to us-west-2)

# Test 2: SSH to EC2-West via private IP
ssh -i key.pem ec2-user@<EC2_WEST_PRIVATE_IP>
# Should succeed — traffic goes over peering, not internet

# Test 3: Measure latency
ping -c 20 <EC2_WEST_PRIVATE_IP> | tail -1
# Compare with: ping -c 20 <EC2_WEST_PUBLIC_IP>
# Private (peering) should be similar or slightly better than public

# Test 4: Transfer a file cross-region
scp -i key.pem /tmp/testfile.txt ec2-user@<EC2_WEST_PRIVATE_IP>:/tmp/
# Should succeed

# Test 5: Confirm traffic uses peering (not internet)
# Check VPC Flow Logs — traffic to 10.1.x.x should show ACCEPT
# Traffic should NOT appear in internet gateway logs

# Run automated checker
python code/multiregion_checker.py \
  --vpc-east $VPC_EAST --vpc-west $VPC_WEST \
  --region-east us-east-1 --region-west us-west-2
```

### Verification Checklist
- [ ] VPC created in us-east-1 with CIDR 10.0.0.0/16
- [ ] VPC created in us-west-2 with CIDR 10.1.0.0/16
- [ ] Inter-region peering status = active
- [ ] us-east-1 route table has `10.1.0.0/16 → pcx`
- [ ] us-west-2 route table has `10.0.0.0/16 → pcx`
- [ ] Ping from EC2-East to EC2-West private IP succeeds
- [ ] Latency ~60-80ms (cross-region over AWS backbone)
- [ ] SSH from EC2-East to EC2-West private IP succeeds
- [ ] File transfer (SCP) cross-region works

---

## Teardown
```bash
terraform destroy
# Remember to destroy resources in BOTH regions
```
