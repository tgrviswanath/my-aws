# Verification & Validation — Project 11.1 Basic VPC with Public Subnet

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC | VPC → Your VPCs | `vpc-11-1` listed, State = **available** |
| Subnet | VPC → Subnets | `public-subnet-11-1`, CIDR `10.0.1.0/24`, Auto-assign public IP = **Yes** |
| Internet Gateway | VPC → Internet Gateways | `igw-11-1`, State = **attached**, VPC = `vpc-11-1` |
| Route Table | VPC → Route Tables → Routes tab | `0.0.0.0/0 → igw-11-1` present |
| Route Table | Subnet Associations tab | `public-subnet-11-1` listed |
| Security Group | EC2 → Security Groups | `sg-web-11-1`, Inbound: SSH 22 + HTTP 80 |
| EC2 Instance | EC2 → Instances | Running, Public IPv4 assigned |

📸 Screenshot: VPC dashboard showing `vpc-11-1` with State = available  
📸 Screenshot: Route table Routes tab showing `0.0.0.0/0 → igw-11-1`  
📸 Screenshot: EC2 instance with public IP assigned

---

## 2. AWS CLI Verification

```bash
# 2.1 VPC — confirm state and DNS settings
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=vpc-11-1" \
  --query "Vpcs[*].{ID:VpcId,CIDR:CidrBlock,State:State,DNS:EnableDnsHostnames}"
# Expected: State=available, DNS=true

# 2.2 Subnet — confirm public IP auto-assign
aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values=public-subnet-11-1" \
  --query "Subnets[*].{ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}"
# Expected: PublicIP=true

# 2.3 Internet Gateway — confirm attached
aws ec2 describe-internet-gateways \
  --filters "Name=tag:Name,Values=igw-11-1" \
  --query "InternetGateways[*].{ID:InternetGatewayId,State:Attachments[0].State,VPC:Attachments[0].VpcId}"
# Expected: State=available

# 2.4 Route table — confirm 0.0.0.0/0 → IGW
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=public-rt-11-1" \
  --query "RouteTables[*].Routes[*].{Dest:DestinationCidrBlock,Target:GatewayId}"
# Expected: Dest=0.0.0.0/0, Target=igw-xxx

# 2.5 EC2 — confirm public IP assigned
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ec2-web-11-1" "Name=instance-state-name,Values=running" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,PublicIP:PublicIpAddress,State:State.Name}"
# Expected: PublicIP is not null

# 2.6 Connectivity test from inside EC2
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
curl -s https://checkip.amazonaws.com   # returns the instance's public IP
ping -c 3 8.8.8.8                        # succeeds
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources tracked in state
terraform state list
# Expected output:
# aws_vpc.main
# aws_subnet.public
# aws_internet_gateway.main
# aws_route_table.public
# aws_route_table_association.public
# aws_security_group.web

# 3.2 Inspect a specific resource
terraform state show aws_vpc.main
# Shows: id, cidr_block, enable_dns_hostnames, tags

terraform state show aws_internet_gateway.main
# Shows: id, vpc_id, tags

# 3.3 Confirm outputs match deployed resources
terraform output
# Expected:
# vpc_id     = "vpc-xxxxxxxxxxxxxxxxx"
# subnet_id  = "subnet-xxxxxxxxxxxxxxxxx"
# igw_id     = "igw-xxxxxxxxxxxxxxxxx"

# 3.4 Confirm no drift (plan should show no changes)
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check

```bash
# From inside the EC2 instance:
curl -s https://checkip.amazonaws.com   # returns public IP — confirms internet egress
curl -s http://169.254.169.254/latest/meta-data/instance-id  # confirms metadata service works
ping -c 3 8.8.8.8                        # confirms ICMP outbound
```

---

## 5. Expected Successful Outputs

**CLI — describe-vpcs:**
```json
[{ "ID": "vpc-0abc123", "CIDR": "10.0.0.0/16", "State": "available", "DNS": true }]
```

**CLI — describe-route-tables:**
```json
[[{ "Dest": "0.0.0.0/0", "Target": "igw-0abc123" }, { "Dest": "10.0.0.0/16", "Target": "local" }]]
```

**terraform output:**
```
vpc_id    = "vpc-0abc123"
subnet_id = "subnet-0abc123"
igw_id    = "igw-0abc123"
```

**Python checker:**
```
=======================================================
  VPC Checker — Project 11.1
  VPC ID: vpc-0abc123
=======================================================
✅  VPC: vpc-0abc123  CIDR=10.0.0.0/16  State=available
  Subnets (1 found):
    ✅  public-subnet-11-1  10.0.1.0/24  us-east-1a  [PUBLIC]
✅  Internet Gateway: igw-0abc123  Name=igw-11-1  Attached=True
  Route Tables (2 found):
    ✅  rtb-0abc123  Name=public-rt-11-1  IGW-route=True
```

---

## 6. Verification Checklist

- [ ] VPC `vpc-11-1` state = available
- [ ] Subnet `10.0.1.0/24` in us-east-1a, auto-assign public IP = enabled
- [ ] IGW `igw-11-1` attached to VPC
- [ ] Route table has `0.0.0.0/0 → igw-xxx`
- [ ] Route table associated with public subnet
- [ ] EC2 has a public IP
- [ ] SSH to EC2 succeeds
- [ ] `curl https://checkip.amazonaws.com` returns public IP
- [ ] `ping 8.8.8.8` succeeds from EC2
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows all 6 resources
- [ ] Python checker shows all ✅
