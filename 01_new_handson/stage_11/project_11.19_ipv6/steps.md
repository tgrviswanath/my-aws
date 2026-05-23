# Steps — Project 11.19 IPv6 Implementation

## Phase 1 — Console

### 1.1 Create Dual-Stack VPC
1. **VPC** → **Your VPCs** → **Create VPC**
2. Name: `vpc-11-19`
3. IPv4 CIDR: `10.0.0.0/16`
4. IPv6 CIDR block: **Amazon-provided IPv6 CIDR block** ← enable this
5. Create
6. Note the assigned IPv6 CIDR (e.g., `2600:1f18:xxxx:xx00::/56`)

### 1.2 Create Dual-Stack Subnets

**Public Subnet:**
1. **VPC** → **Subnets** → **Create subnet**
2. Name: `public-ipv6-11-19`
3. VPC: `vpc-11-19`
4. AZ: us-east-1a
5. IPv4 CIDR: `10.0.1.0/24`
6. IPv6 CIDR: **Specify a custom IPv6 CIDR** → enter `00` (first /64 from the /56)
7. Create
8. Select subnet → **Actions** → **Edit subnet settings**:
   - Enable auto-assign IPv6 address: ✅
   - Enable auto-assign public IPv4: ✅

**Private Subnet:**
1. Same process, name: `private-ipv6-11-19`
2. IPv4 CIDR: `10.0.2.0/24`
3. IPv6 CIDR: `01` (second /64)
4. Enable auto-assign IPv6 only (no public IPv4)

### 1.3 Create Internet Gateway
- Name: `igw-11-19` → attach to `vpc-11-19`

### 1.4 Create Egress-Only Internet Gateway
1. **VPC** → **Egress-only internet gateways** → **Create**
2. Name: `eigw-11-19`
3. VPC: `vpc-11-19`
4. Create

### 1.5 Create Route Tables

**Public Route Table** (`public-rt-11-19`):
- IPv4 route: `0.0.0.0/0 → igw-11-19`
- IPv6 route: `::/0 → igw-11-19`
- Associate: `public-ipv6-11-19`

**Private Route Table** (`private-rt-11-19`):
- IPv4 route: `0.0.0.0/0 → NAT Gateway` (if needed)
- IPv6 route: `::/0 → eigw-11-19`
- Associate: `private-ipv6-11-19`

### 1.6 Update Security Groups
- Add inbound rules for IPv6:
  - SSH: `::/0` (or restrict to your IPv6 address)
  - ICMP v6: `::/0` (for ping6 testing)

### 1.7 Launch EC2 Instances
- Public EC2: `public-ipv6-11-19` subnet, auto-assign IPv6 enabled
- Private EC2: `private-ipv6-11-19` subnet, auto-assign IPv6 enabled

---

## Phase 2 — AWS CLI

```bash
# Create VPC with IPv6
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --amazon-provided-ipv6-cidr-block \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=vpc-11-19
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Wait for IPv6 CIDR to be assigned
sleep 5
IPV6_CIDR=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID \
  --query "Vpcs[0].Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock" --output text)
echo "VPC IPv6 CIDR: $IPV6_CIDR"
# e.g., 2600:1f18:xxxx:xx00::/56

# Derive /64 subnet CIDRs from /56
# Replace last two hex groups: xx00::/56 → xx00::/64 and xx01::/64
IPV6_BASE=$(echo $IPV6_CIDR | sed 's|::/56||')
PUB_IPV6="${IPV6_BASE}00::/64"
PRIV_IPV6="${IPV6_BASE}01::/64"

# Create public subnet (dual-stack)
PUB_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --ipv6-cidr-block $PUB_IPV6 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB_SUBNET --tags Key=Name,Value=public-ipv6-11-19
aws ec2 modify-subnet-attribute --subnet-id $PUB_SUBNET --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id $PUB_SUBNET \
  --assign-ipv6-address-on-creation

# Create private subnet (dual-stack)
PRIV_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --ipv6-cidr-block $PRIV_IPV6 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_SUBNET --tags Key=Name,Value=private-ipv6-11-19
aws ec2 modify-subnet-attribute --subnet-id $PRIV_SUBNET \
  --assign-ipv6-address-on-creation

# Create IGW
IGW=$(aws ec2 create-internet-gateway \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC_ID
aws ec2 create-tags --resources $IGW --tags Key=Name,Value=igw-11-19

# Create Egress-Only IGW
EIGW=$(aws ec2 create-egress-only-internet-gateway \
  --vpc-id $VPC_ID \
  --query "EgressOnlyInternetGateway.EgressOnlyInternetGatewayId" --output text)
echo "EIGW: $EIGW"

# Public route table — IPv4 + IPv6
PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PUB_RT --tags Key=Name,Value=public-rt-11-19
aws ec2 create-route --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW
aws ec2 create-route --route-table-id $PUB_RT \
  --destination-ipv6-cidr-block ::/0 --gateway-id $IGW
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUBNET

# Private route table — IPv6 via EIGW
PRIV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PRIV_RT --tags Key=Name,Value=private-rt-11-19
aws ec2 create-route --route-table-id $PRIV_RT \
  --destination-ipv6-cidr-block ::/0 \
  --egress-only-internet-gateway-id $EIGW
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV_SUBNET

echo "Done. VPC=$VPC_ID  IPv6=$IPV6_CIDR  EIGW=$EIGW"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
terraform output
```

---

## Phase 4 — Verify

```bash
# 1. Confirm VPC has IPv6 CIDR
aws ec2 describe-vpcs --vpc-ids $VPC_ID \
  --query "Vpcs[0].{IPv4:CidrBlock,IPv6:Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock}"

# 2. Confirm subnets have IPv6 CIDRs
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,IPv4:CidrBlock,IPv6:Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock,AutoIPv6:AssignIpv6AddressOnCreation}"

# 3. Confirm Egress-Only IGW exists
aws ec2 describe-egress-only-internet-gateways \
  --query "EgressOnlyInternetGateways[*].{ID:EgressOnlyInternetGatewayId,State:Attachments[0].State}"

# 4. Confirm route tables have ::/0 routes
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,IPv6Routes:Routes[?DestinationIpv6CidrBlock!=null].{Dest:DestinationIpv6CidrBlock,Target:GatewayId}}"

# 5. Confirm EC2 instances have IPv6 addresses
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,IPv4:PrivateIpAddress,IPv6:NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address}"
```

---

## Phase 5 — Test

```bash
# Get IPv6 addresses
PUB_IPV6_ADDR=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ec2-public-11-19" \
  --query "Reservations[0].Instances[0].NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address" \
  --output text)
PRIV_IPV6_ADDR=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ec2-private-11-19" \
  --query "Reservations[0].Instances[0].NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address" \
  --output text)
echo "Public EC2 IPv6:  $PUB_IPV6_ADDR"
echo "Private EC2 IPv6: $PRIV_IPV6_ADDR"

# Test 1: SSH to public EC2 via IPv6
ssh -6 -i key.pem ec2-user@$PUB_IPV6_ADDR
# Expected: success (IPv6 SSH)

# Test 2: From public EC2 — ping6 to internet
ping6 -c 5 ipv6.google.com
# Expected: success (IPv6 internet via IGW)

# Test 3: From public EC2 — ping6 to private EC2
ping6 -c 5 $PRIV_IPV6_ADDR
# Expected: success (same VPC, IPv6)

# Test 4: From private EC2 — outbound IPv6 works (via EIGW)
# SSH to private EC2 via public EC2 (hop)
ssh -i key.pem ec2-user@<PUBLIC_EC2_IPV4>
ssh -i key.pem ec2-user@$PRIV_IPV6_ADDR   # or via private IPv4

# From private EC2:
ping6 -c 5 ipv6.google.com
# Expected: success (outbound via Egress-Only IGW)

# Test 5: Inbound IPv6 to private EC2 is BLOCKED
# From your laptop:
ping6 $PRIV_IPV6_ADDR
# Expected: no response (EIGW blocks inbound)

# Test 6: Verify dual-stack — both IPv4 and IPv6 work
curl -4 http://<PUBLIC_EC2_IPV4>   # IPv4
curl -6 http://[$PUB_IPV6_ADDR]    # IPv6
# Both should return nginx response

# Run automated checker
python code/ipv6_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] VPC has both IPv4 (`10.0.0.0/16`) and IPv6 (`2600::/56`) CIDRs
- [ ] Public subnet has IPv6 /64 CIDR, auto-assign IPv6 enabled
- [ ] Private subnet has IPv6 /64 CIDR, auto-assign IPv6 enabled
- [ ] Public route table: `::/0 → igw` (bidirectional IPv6)
- [ ] Private route table: `::/0 → eigw` (outbound-only IPv6)
- [ ] Public EC2 has both IPv4 and IPv6 addresses
- [ ] Private EC2 has IPv6 address (no public IPv4)
- [ ] SSH to public EC2 via IPv6 succeeds
- [ ] `ping6 ipv6.google.com` from public EC2 succeeds
- [ ] `ping6 ipv6.google.com` from private EC2 succeeds (via EIGW)
- [ ] Inbound ping6 to private EC2 from internet is blocked

---

## Teardown
```bash
terraform destroy
# Egress-Only IGW is free — no cost concern
```
