# Project 2.1 — Custom VPC Design

**Stage:** 02 | **Level:** Intermediate | **Est. Time:** 2–3 hours | **Cost:** ~$32/month (NAT Gateway dominates)

Build a production-style VPC from scratch using CIDR block `10.0.0.0/16` spread across two Availability Zones. The design includes two public subnets fronted by an Internet Gateway and two private subnets that reach the internet through a managed NAT Gateway. Each subnet group gets its own route table, mirroring the isolation pattern used in real workloads where web-facing and internal tiers must never share routing rules.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| VPC | Isolated network container for all resources | Free |
| Subnets (×4) | AZ-level segmentation: 2 public, 2 private | Free |
| Internet Gateway | Inbound/outbound internet for public subnets | Free |
| NAT Gateway | Outbound-only internet for private subnets | $0.045/hr + $0.045/GB |
| Route Tables (×2) | Public table → IGW, private table → NAT GW | Free |
| Security Groups | Stateful firewall rules per EC2 instance | Free |
| Elastic IP | Static IP attached to NAT Gateway | $0.005/hr when unattached |

## Input / Output

### Input

| Parameter | Value |
|---|---|
| CIDR Block | `10.0.0.0/16` |
| Public Subnet A | `10.0.1.0/24` — us-east-1a |
| Public Subnet B | `10.0.2.0/24` — us-east-1b |
| Private Subnet A | `10.0.3.0/24` — us-east-1a |
| Private Subnet B | `10.0.4.0/24` — us-east-1b |
| NAT Gateway placement | Public Subnet A |
| Region | us-east-1 |

### Output

| Resource | Result |
|---|---|
| VPC ID | `vpc-xxxxxxxxxxxxxxxxx` |
| IGW attached | Yes — public route table has `0.0.0.0/0 → igw-xxx` |
| NAT GW active | Yes — private route table has `0.0.0.0/0 → nat-xxx` |
| EC2 in public subnet | Has public IP, reaches internet directly |
| EC2 in private subnet | No public IP, reaches internet via NAT GW |

## Architecture

```
  us-east-1
  ┌─────────────────────────────────────────────────────────┐
  │  VPC: 10.0.0.0/16                                       │
  │                                                         │
  │  ┌──────────────────────┐  ┌──────────────────────┐     │
  │  │  us-east-1a          │  │  us-east-1b          │     │
  │  │  Public 10.0.1.0/24  │  │  Public 10.0.2.0/24  │     │
  │  │  [EC2] [NAT GW+EIP]  │  │  [EC2]               │     │
  │  └──────────┬───────────┘  └──────────────────────┘     │
  │             │ public-rt: 0.0.0.0/0 → IGW                │
  │  ┌──────────┴───────────┐  ┌──────────────────────┐     │
  │  │  us-east-1a          │  │  us-east-1b          │     │
  │  │  Private 10.0.3.0/24 │  │  Private 10.0.4.0/24 │     │
  │  │  [EC2]               │  │  [EC2]               │     │
  │  └──────────────────────┘  └──────────────────────┘     │
  │             private-rt: 0.0.0.0/0 → NAT GW              │
  │                                                         │
  └──────────────────────────┬──────────────────────────────┘
                             │
                      [Internet Gateway]
                             │
                          Internet
```

## Quick Start

```cmd
REM Step 1: Create the VPC
aws ec2 create-vpc ^
  --cidr-block 10.0.0.0/16 ^
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=project-2.1-vpc}]"

REM Step 2: Create public subnets in us-east-1a and us-east-1b
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24 ^
  --availability-zone us-east-1a ^
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-1a}]"

aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.2.0/24 ^
  --availability-zone us-east-1b ^
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-1b}]"

REM Step 3: Create private subnets in us-east-1a and us-east-1b
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.3.0/24 ^
  --availability-zone us-east-1a ^
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet-1a}]"

aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.4.0/24 ^
  --availability-zone us-east-1b ^
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet-1b}]"

REM Step 4: Create and attach Internet Gateway
aws ec2 create-internet-gateway ^
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=project-2.1-igw}]"

aws ec2 attach-internet-gateway --vpc-id <VPC_ID> --internet-gateway-id <IGW_ID>

REM Step 5: Allocate EIP and create NAT Gateway in public-subnet-1a
aws ec2 allocate-address --domain vpc

aws ec2 create-nat-gateway --subnet-id <PUBLIC_SUBNET_1A_ID> ^
  --allocation-id <EIP_ALLOC_ID> ^
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=project-2.1-nat}]"

REM Step 6: Create public route table, add IGW route, associate both public subnets
aws ec2 create-route-table --vpc-id <VPC_ID> ^
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]"

aws ec2 create-route --route-table-id <PUBLIC_RT_ID> ^
  --destination-cidr-block 0.0.0.0/0 --gateway-id <IGW_ID>

aws ec2 associate-route-table --subnet-id <PUBLIC_SUBNET_1A_ID> --route-table-id <PUBLIC_RT_ID>
aws ec2 associate-route-table --subnet-id <PUBLIC_SUBNET_1B_ID> --route-table-id <PUBLIC_RT_ID>

REM Step 7: Create private route table, add NAT route, associate both private subnets
aws ec2 create-route-table --vpc-id <VPC_ID> ^
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=private-rt}]"

aws ec2 create-route --route-table-id <PRIVATE_RT_ID> ^
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id <NAT_GW_ID>

aws ec2 associate-route-table --subnet-id <PRIVATE_SUBNET_1A_ID> --route-table-id <PRIVATE_RT_ID>
aws ec2 associate-route-table --subnet-id <PRIVATE_SUBNET_1B_ID> --route-table-id <PRIVATE_RT_ID>
```

## Data Flow

1. EC2 in public subnet sends a packet to `8.8.8.8` — the subnet's route table matches `0.0.0.0/0 → igw-xxx`.
2. IGW performs NAT on the packet, replacing the private IP with the instance's public/Elastic IP, and forwards to the internet.
3. EC2 in private subnet sends a packet to `8.8.8.8` — no public IP assigned, route table matches `0.0.0.0/0 → nat-xxx`.
4. NAT Gateway receives the packet in the public subnet, replaces the source IP with its own Elastic IP, and forwards via IGW.
5. Response traffic from the internet returns to the NAT Gateway's Elastic IP; NAT GW translates it back and delivers to the private EC2.
6. Security group on each EC2 evaluates inbound rules — stateful tracking means the return packet is automatically allowed without an explicit inbound rule.
7. NACL at the subnet boundary is evaluated after the security group; default NACL allows all traffic in both directions.

## Project Files

| File | Description |
|---|---|
| `README.md` | This document |
| `vpc-setup.sh` | Sequential CLI commands to build the full VPC |
| `verify-routing.sh` | Ping tests from public and private EC2 to validate routing |
| `cleanup.sh` | Tear-down in reverse order (NAT GW first to stop billing) |
| `architecture.png` | Full subnet/AZ diagram |

## Lessons Learned

- **NAT Gateway vs NAT instance cost:** NAT GW costs ~$32/month minimum even with zero traffic (hourly charge). A t3.nano NAT instance costs ~$3/month — worth it for dev environments, not for production reliability.
- **Explicit route table association is required:** Every subnet starts associated with the VPC's default (implicit) route table. Creating a new route table does nothing until you explicitly `associate-route-table` for each subnet.
- **VPC CIDR cannot overlap:** If this VPC will ever peer with another VPC or connect to on-premises via VPN/Direct Connect, the `10.0.0.0/16` block must not conflict. Plan your CIDR ranges across all environments before you start.
- **Private EC2 has no public IP — by design:** Assigning `MapPublicIpOnLaunch=false` on private subnets ensures instances never accidentally get a routable address. Outbound traffic still works via NAT GW.
- **Security groups are stateful; NACLs are stateless:** A security group that allows outbound port 80 automatically allows the inbound response. A NACL rule for outbound port 80 requires a matching inbound rule for the ephemeral port range (1024–65535) or the response is dropped.
- **5 VPC limit per region is a soft limit:** AWS accounts default to 5 VPCs per region. This is easily increased via Service Quotas, but it signals the importance of subnet design within a single VPC over creating multiple VPCs.
- **NAT Gateway must be in the public subnet, not the private one:** A common mistake is placing the NAT GW in the private subnet. It needs an Elastic IP and IGW access, which only exist in the public subnet's route table.
