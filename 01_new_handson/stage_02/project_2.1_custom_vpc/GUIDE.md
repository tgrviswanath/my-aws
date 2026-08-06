# Project 2.1 — Custom VPC with Public and Private Subnets

> Stage 02 | Networking | AWS CLI + Console | No Terraform

---

## 1. Project Overview

**Title:** Custom VPC with Public and Private Subnets

**Problem:** The AWS default VPC provides no subnet isolation — all resources share the same network segment, making it impossible to enforce security boundaries between public-facing and internal workloads.

**Objectives:**
- Create a custom VPC with CIDR `10.0.0.0/16`
- Create a public subnet (`10.0.1.0/24`) and a private subnet (`10.0.2.0/24`)
- Attach an Internet Gateway for public internet access
- Deploy a NAT Gateway so private resources can reach the internet (outbound only)
- Configure route tables to control traffic flow
- Deploy an EC2 bastion host in the public subnet and an app/DB EC2 in the private subnet
- Verify connectivity between subnets and to the internet

**Key Concepts:** CIDR notation, subnet isolation, route table association, IGW vs NAT Gateway, bastion host pattern

---

## 2. Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  VPC: handson-vpc (10.0.0.0/16)                         │
│                                                         │
│  ┌──────────────────────────┐                          │
│  │  Internet Gateway (IGW)  │                          │
│  └────────────┬─────────────┘                          │
│               │                                         │
│  ┌────────────▼─────────────────────────────────────┐  │
│  │  Public Subnet (10.0.1.0/24) — us-east-1a        │  │
│  │                                                   │  │
│  │   ┌────────────────┐    ┌─────────────────────┐  │  │
│  │   │ EC2 Bastion    │    │  NAT Gateway        │  │  │
│  │   │ (public IP)    │    │  (Elastic IP)       │  │  │
│  │   └────────────────┘    └──────────┬──────────┘  │  │
│  └──────────────────────────────────── │ ────────────┘  │
│                                        │                 │
│  ┌─────────────────────────────────────▼────────────┐  │
│  │  Private Subnet (10.0.2.0/24) — us-east-1b       │  │
│  │                                                   │  │
│  │   ┌──────────────────────────────────────────┐   │  │
│  │   │ EC2 App / DB  (no public IP)             │   │  │
│  │   └──────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Route Tables:                                          │
│  • public-rt:  0.0.0.0/0 → IGW                         │
│  • private-rt: 0.0.0.0/0 → NAT GW                      │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Prerequisites

- AWS account with active billing (NAT Gateway incurs cost)
- IAM permissions: `ec2:*` (VPC, subnets, IGW, NAT, route tables, security groups)
- AWS CLI v2 installed and configured (`aws configure` with access key + region)
- Basic understanding of CIDR notation (e.g., `/16` = 65536 IPs, `/24` = 256 IPs)
- SSH key pair created in us-east-1 (for EC2 access)
- Region: `us-east-1` (all commands assume this region)

**Prerequisites Check:**
```bash
# Verify CLI is configured
aws sts get-caller-identity

# Verify VPC permissions
aws ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text

# Check existing key pairs
aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName'
```

---

## 4. Folder Structure

```
project_2.1_custom_vpc/
├── GUIDE.md                  # This file — full implementation guide
├── steps_awsconsoleui.md     # Console UI step-by-step with screenshots
├── cleanup.sh                # Optional: automated cleanup script
└── README.md                 # Quick reference
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method

#### Prerequisites Check
Before starting, confirm in the AWS Console:
- Navigate to **VPC Dashboard** → verify you see the default VPC
- Navigate to **EC2 → Key Pairs** → confirm a key pair exists
- Check your region is **us-east-1** (top-right corner)

---

#### Decision Point 1 — Single-AZ vs Multi-AZ

| Option | Use Case | Cost | Resilience |
|--------|----------|------|------------|
| ✅ Single-AZ | Dev / learning (this guide) | Lower | Single point of failure |
| ✅ Multi-AZ | Production | Higher (duplicate NAT GW) | High availability |

**This guide uses Single-AZ** to keep costs minimal. For production, duplicate subnets and NAT Gateway into a second AZ.

---

#### Step-by-Step Console Instructions

**Create the VPC:**
1. Go to **VPC → Your VPCs → Create VPC**
2. Select **VPC only** (not VPC and more)
3. Name tag: `handson-vpc`
4. IPv4 CIDR: `10.0.0.0/16`
5. Tenancy: Default
6. Click **Create VPC**

**Create Public Subnet:**
1. Go to **VPC → Subnets → Create subnet**
2. VPC: select `handson-vpc`
3. Subnet name: `public-subnet-1a`
4. AZ: `us-east-1a`
5. IPv4 CIDR: `10.0.1.0/24`
6. Click **Create subnet**
7. Select the subnet → **Actions → Edit subnet settings** → enable **Auto-assign public IPv4**

**Create Private Subnet:**
1. Go to **VPC → Subnets → Create subnet**
2. VPC: select `handson-vpc`
3. Subnet name: `private-subnet-1b`
4. AZ: `us-east-1b`
5. IPv4 CIDR: `10.0.2.0/24`
6. Click **Create subnet**
7. Do NOT enable auto-assign public IP

**Create Internet Gateway:**
1. Go to **VPC → Internet Gateways → Create internet gateway**
2. Name tag: `handson-igw`
3. Click **Create internet gateway**
4. Select the IGW → **Actions → Attach to VPC** → select `handson-vpc`

**Create NAT Gateway:**
1. Go to **VPC → NAT Gateways → Create NAT gateway**
2. Name: `handson-nat-gw`
3. Subnet: `public-subnet-1a` (must be in public subnet!)
4. Connectivity type: Public
5. Elastic IP: Click **Allocate Elastic IP**
6. Click **Create NAT gateway**
7. Wait ~2 minutes until status shows **Available**

**Create Public Route Table:**
1. Go to **VPC → Route Tables → Create route table**
2. Name: `public-rt`
3. VPC: `handson-vpc`
4. Click **Create route table**
5. Select `public-rt` → **Routes tab → Edit routes → Add route**
6. Destination: `0.0.0.0/0`, Target: `Internet Gateway` → select `handson-igw`
7. Save routes
8. **Subnet associations tab → Edit subnet associations** → select `public-subnet-1a`

**Create Private Route Table:**
1. Go to **VPC → Route Tables → Create route table**
2. Name: `private-rt`
3. VPC: `handson-vpc`
4. Click **Create route table**
5. Select `private-rt` → **Routes tab → Edit routes → Add route**
6. Destination: `0.0.0.0/0`, Target: `NAT Gateway` → select `handson-nat-gw`
7. Save routes
8. **Subnet associations tab → Edit subnet associations** → select `private-subnet-1b`

**Deploy EC2 in Public Subnet (Bastion):**
1. EC2 → Launch Instance
2. Name: `bastion-host`, AMI: Amazon Linux 2023
3. Instance type: `t2.micro`
4. Key pair: select your key pair
5. Network: `handson-vpc`, Subnet: `public-subnet-1a`
6. Auto-assign public IP: Enable
7. Security group: allow SSH (port 22) from your IP
8. Launch

**Deploy EC2 in Private Subnet:**
1. EC2 → Launch Instance
2. Name: `private-app`, AMI: Amazon Linux 2023
3. Instance type: `t2.micro`
4. Key pair: select your key pair
5. Network: `handson-vpc`, Subnet: `private-subnet-1b`
6. Auto-assign public IP: Disable
7. Security group: allow SSH (port 22) from `10.0.1.0/24` (bastion subnet only)
8. Launch

**Expected Outcome:**
- Bastion has a public IP and is reachable from the internet via SSH
- Private EC2 has no public IP, only reachable from bastion
- Private EC2 can reach the internet outbound (via NAT GW) — test with `curl https://checkip.amazonaws.com`

**Troubleshooting:**
- Cannot SSH to bastion: check security group allows port 22 from your IP
- Private EC2 cannot reach internet: verify private-rt has 0.0.0.0/0 → NAT GW route and NAT GW is in Available state
- NAT GW still pending: wait 2-3 minutes; it takes time to provision

---

### 5B. AWS CLI Method

```bash
# ── STEP 1: Create VPC ──────────────────────────────────────────────────────
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=handson-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)
echo "VPC_ID=$VPC_ID"

# Enable DNS hostnames (needed for EC2 public DNS)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# ── STEP 2: Create Subnets ──────────────────────────────────────────────────
PUBLIC_SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-1a}]' \
  --query 'Subnet.SubnetId' \
  --output text)
echo "PUBLIC_SUBNET_ID=$PUBLIC_SUBNET_ID"

PRIVATE_SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet-1b}]' \
  --query 'Subnet.SubnetId' \
  --output text)
echo "PRIVATE_SUBNET_ID=$PRIVATE_SUBNET_ID"

# Enable auto-assign public IP for public subnet
aws ec2 modify-subnet-attribute \
  --subnet-id $PUBLIC_SUBNET_ID \
  --map-public-ip-on-launch

# ── STEP 3: Create and Attach Internet Gateway ──────────────────────────────
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=handson-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)
echo "IGW_ID=$IGW_ID"

aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# ── STEP 4: Create NAT Gateway (requires Elastic IP) ───────────────────────
EIP_ALLOC_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' \
  --output text)
echo "EIP_ALLOC_ID=$EIP_ALLOC_ID"

NAT_GW_ID=$(aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_ID \
  --allocation-id $EIP_ALLOC_ID \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=handson-nat-gw}]' \
  --query 'NatGateway.NatGatewayId' \
  --output text)
echo "NAT_GW_ID=$NAT_GW_ID"

# Wait for NAT GW to become available
echo "Waiting for NAT Gateway to become available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_ID
echo "NAT Gateway is ready."

# ── STEP 5: Create Route Tables ─────────────────────────────────────────────
PUBLIC_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

PRIVATE_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=private-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# ── STEP 6: Add Routes ───────────────────────────────────────────────────────
aws ec2 create-route \
  --route-table-id $PUBLIC_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 create-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_ID

# ── STEP 7: Associate Route Tables with Subnets ──────────────────────────────
aws ec2 associate-route-table \
  --route-table-id $PUBLIC_RT_ID \
  --subnet-id $PUBLIC_SUBNET_ID

aws ec2 associate-route-table \
  --route-table-id $PRIVATE_RT_ID \
  --subnet-id $PRIVATE_SUBNET_ID

echo "VPC setup complete!"
echo "VPC=$VPC_ID | Public Subnet=$PUBLIC_SUBNET_ID | Private Subnet=$PRIVATE_SUBNET_ID"
echo "IGW=$IGW_ID | NAT GW=$NAT_GW_ID"
```

---

## 6. Code Deep Dive

### AWS CLI Parameter Explanations

| Command | Key Parameter | Meaning |
|---------|--------------|---------|
| `create-vpc` | `--cidr-block` | IP range for the entire VPC. `/16` gives 65,536 addresses |
| `create-subnet` | `--availability-zone` | Physical AZ placement. Affects latency and HA design |
| `create-subnet` | `--cidr-block` | Must be a subset of the VPC CIDR. `/24` gives 251 usable IPs (AWS reserves 5) |
| `create-internet-gateway` | (none required) | Creates an IGW object; must be explicitly attached to a VPC |
| `allocate-address` | `--domain vpc` | Allocates an Elastic IP in VPC scope (required for NAT GW) |
| `create-nat-gateway` | `--subnet-id` | NAT GW must be placed in a **public** subnet — this is a common mistake |
| `create-route` | `--destination-cidr-block` | Traffic matching this CIDR uses the specified target |
| `modify-subnet-attribute` | `--map-public-ip-on-launch` | Instances launched in this subnet automatically get a public IP |

### Route Table Priority
Routes are matched by most-specific prefix first (longest prefix match):
- `10.0.0.0/16` (local) always takes priority for VPC-internal traffic
- `0.0.0.0/0` is the catch-all default route for external traffic
- More specific routes (e.g., `10.0.1.0/24`) always win over less specific ones

### NACLs vs Security Groups

| Feature | NACL | Security Group |
|---------|------|----------------|
| Level | Subnet level | Instance level |
| Statefulness | Stateless (must allow both directions) | Stateful (return traffic auto-allowed) |
| Rule evaluation | Numbered rules, lowest wins | All rules evaluated together |
| Scope | Applies to all instances in subnet | Applies per-instance |
| Default behavior | Default NACL allows all traffic | Default SG denies all inbound |

---

## 7. Verification

```bash
# Verify VPC was created
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=handson-vpc" \
  --query 'Vpcs[*].{ID:VpcId,CIDR:CidrBlock,State:State}' \
  --output table

# Verify subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].{ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,Name:Tags[?Key==`Name`].Value|[0]}' \
  --output table

# Verify route tables
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[*].{ID:RouteTableId,Routes:Routes[*].DestinationCidrBlock}' \
  --output json

# Verify IGW is attached
aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
  --query 'InternetGateways[*].{ID:InternetGatewayId,State:Attachments[0].State}' \
  --output table

# Verify NAT Gateway
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[*].{ID:NatGatewayId,State:State,Subnet:SubnetId}' \
  --output table

# SSH to bastion, then from bastion ping private EC2
ssh -i your-key.pem ec2-user@<bastion-public-ip>
# From bastion:
ping 10.0.2.x  # private EC2 internal IP

# From private EC2 (SSH through bastion): verify outbound internet via NAT GW
curl https://checkip.amazonaws.com
# Should return the NAT Gateway's Elastic IP
```

---

## 8. Observations

### NAT Gateway Cost Warning
NAT Gateway is the most expensive component in this setup:
- **Hourly charge:** ~$0.045/hr ≈ **$32.40/month** just for the gateway existing
- **Data processing:** $0.045 per GB of data processed
- **Elastic IP:** $0.005/hr when not associated; free when in use with NAT GW
- **Action:** Delete the NAT Gateway when not actively using it to avoid charges

### Subnet Auto-Assign Public IP
- Enabling `map-public-ip-on-launch` on the public subnet means every new EC2 in that subnet automatically gets a public IP
- This is a convenience setting — you can still disable it per-instance at launch time
- The private subnet should never have this enabled

### Route Propagation
- Route tables take effect immediately upon association — no restart needed
- Local route (`10.0.0.0/16`) is always present and cannot be deleted
- If you change a route table association, traffic shifts immediately
- Main route table (default) catches subnets not explicitly associated with a custom route table

### Security Group Inheritance
- Security groups are VPC-scoped — you can reference other security groups within the same VPC
- A bastion host security group allowing SSH from `0.0.0.0/0` is a learning convenience — in production, restrict to your office/VPN IP

---

## 9. Screenshots Guide

Take screenshots at these moments for documentation:

1. **VPC Dashboard** — after VPC creation, showing VPC ID and CIDR `10.0.0.0/16`
2. **Subnet list** — both subnets visible with correct CIDRs and AZs
3. **IGW attached state** — Internet Gateway showing "Attached" to handson-vpc
4. **NAT Gateway Available** — NAT GW showing "Available" state with Elastic IP
5. **Public Route Table routes** — showing `10.0.0.0/16 → local` and `0.0.0.0/0 → igw-xxxx`
6. **Private Route Table routes** — showing `10.0.0.0/16 → local` and `0.0.0.0/0 → nat-xxxx`
7. **Subnet association** — public-rt associated with public-subnet-1a
8. **EC2 instances** — both bastion and private-app showing correct subnet placement
9. **Bastion SSH** — terminal showing successful SSH connection
10. **curl checkip** — from private EC2, showing NAT GW Elastic IP as the public address

---

## 10. Cleanup

**Delete resources in this exact order** (reverse dependency order):

```bash
# ── Step 1: Terminate EC2 instances first ────────────────────────────────────
aws ec2 terminate-instances --instance-ids <bastion-id> <private-app-id>
aws ec2 wait instance-terminated --instance-ids <bastion-id> <private-app-id>

# ── Step 2: Delete NAT Gateway (stops hourly billing immediately) ─────────────
aws ec2 delete-nat-gateway --nat-gateway-id $NAT_GW_ID

# Wait for NAT GW to be deleted (takes ~60 seconds)
echo "Waiting for NAT Gateway deletion..."
aws ec2 wait nat-gateway-deleted --nat-gateway-ids $NAT_GW_ID 2>/dev/null || \
  sleep 60  # fallback wait

# ── Step 3: Release Elastic IP ────────────────────────────────────────────────
# (leaving it allocated incurs cost)
aws ec2 release-address --allocation-id $EIP_ALLOC_ID

# ── Step 4: Detach and delete Internet Gateway ────────────────────────────────
aws ec2 detach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID

# ── Step 5: Delete Route Tables (cannot delete main route table) ──────────────
aws ec2 delete-route-table --route-table-id $PUBLIC_RT_ID
aws ec2 delete-route-table --route-table-id $PRIVATE_RT_ID

# ── Step 6: Delete Subnets ────────────────────────────────────────────────────
aws ec2 delete-subnet --subnet-id $PUBLIC_SUBNET_ID
aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_ID

# ── Step 7: Delete Security Groups (except default) ──────────────────────────
# aws ec2 delete-security-group --group-id <your-sg-id>

# ── Step 8: Delete VPC ────────────────────────────────────────────────────────
aws ec2 delete-vpc --vpc-id $VPC_ID

echo "Cleanup complete. Verify no resources remain:"
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=handson-vpc" --output text
aws ec2 describe-nat-gateways --filter "Name=state,Values=available,pending" --output text
aws ec2 describe-addresses --query 'Addresses[*].PublicIp' --output text
```

**Cost Check After Cleanup:**
```bash
# Confirm no lingering Elastic IPs (each costs $0.005/hr when unattached)
aws ec2 describe-addresses --output table

# Confirm no running NAT Gateways
aws ec2 describe-nat-gateways \
  --filter "Name=state,Values=available,pending,deleting" \
  --output table
```

---

*Guide generated for Stage 02 — AWS Networking Hands-on. Uses AWS CLI v2 and AWS Console. No Terraform.*
