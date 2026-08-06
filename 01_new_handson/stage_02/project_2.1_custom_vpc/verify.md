# Verification & Validation — Project 2.1 Custom VPC Architecture

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC | VPC → Your VPCs | `handson-vpc`, CIDR `10.0.0.0/16`, State = available |
| 6 Subnets | VPC → Subnets | All 6 listed with correct CIDRs and AZs |
| Public subnets | Subnets → Auto-assign public IP | `public-subnet-a/b` = **Yes** |
| Private subnets | Subnets → Auto-assign public IP | All 4 private subnets = **No** |
| Internet Gateway | VPC → Internet Gateways | `handson-igw`, State = **attached** to `handson-vpc` |
| NAT Gateway | VPC → NAT Gateways | `handson-nat`, State = **available**, in public subnet |
| Elastic IP | EC2 → Elastic IPs | Allocated and associated with NAT Gateway |
| Public Route Table | Route Tables → Routes | `0.0.0.0/0 → handson-igw` |
| Private Route Table | Route Tables → Routes | `0.0.0.0/0 → handson-nat` |

📸 Screenshot: VPC with CIDR `10.0.0.0/16` in available state  
📸 Screenshot: All 6 subnets with correct CIDRs and AZs  
📸 Screenshot: NAT Gateway in available state with Elastic IP  
📸 Screenshot: Public RT showing `0.0.0.0/0 → igw-xxx`

---

## 2. AWS CLI Verification

```bash
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=handson-vpc" \
  --query "Vpcs[0].VpcId" --output text)

# 2.1 VPC state and DNS
aws ec2 describe-vpcs --vpc-ids $VPC_ID \
  --query "Vpcs[0].{CIDR:CidrBlock,State:State,DNS:EnableDnsHostnames}"
# Expected: CIDR=10.0.0.0/16, State=available, DNS=true

# 2.2 All 6 subnets with correct CIDRs
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,CIDR:CidrBlock,AZ:AvailabilityZone}" \
  --output table
# Expected: 6 rows — public-a/b, private-app-a/b, private-db-a/b

# 2.3 IGW attached
aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
  --query "InternetGateways[0].{ID:InternetGatewayId,State:Attachments[0].State}"
# Expected: State=available

# 2.4 NAT Gateway available in public subnet
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query "NatGateways[0].{ID:NatGatewayId,State:State,EIP:NatGatewayAddresses[0].PublicIp}"
# Expected: State=available, EIP not null

# 2.5 Public RT has IGW route
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=public-rt" \
  --query "RouteTables[0].Routes[?GatewayId!=null && starts_with(GatewayId,'igw-')].{Dest:DestinationCidrBlock,GW:GatewayId}"
# Expected: Dest=0.0.0.0/0, GW=igw-xxx

# 2.6 Private RT has NAT route
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=private-rt" \
  --query "RouteTables[0].Routes[?NatGatewayId!=null].{Dest:DestinationCidrBlock,NAT:NatGatewayId}"
# Expected: Dest=0.0.0.0/0, NAT=nat-xxx

# 2.7 Run Python checker
python code/vpc_checker.py --vpc-id $VPC_ID
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpc.main
# aws_subnet.public_a / aws_subnet.public_b
# aws_subnet.private_app_a / aws_subnet.private_app_b
# aws_subnet.private_db_a / aws_subnet.private_db_b
# aws_internet_gateway.main
# aws_eip.nat
# aws_nat_gateway.main
# aws_route_table.public / aws_route_table.private
# aws_route_table_association.public_a / .public_b
# aws_route_table_association.private_app_a / .private_app_b
# aws_route_table_association.private_db_a / .private_db_b

terraform state show aws_nat_gateway.main
# Shows: subnet_id (must be public), allocation_id, public_ip

terraform output
# Expected: vpc_id, public_subnet_ids, private_app_subnet_ids, private_db_subnet_ids

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Private Subnet Internet Access via NAT

```bash
# Launch a test EC2 in a private subnet, then via SSM:
aws ssm start-session --target <PRIVATE_INSTANCE_ID>

# From inside private EC2:
curl -s https://checkip.amazonaws.com
# Expected: NAT Gateway's Elastic IP (not the private EC2's IP)

ping -c 3 8.8.8.8
# Expected: success — outbound via NAT

# Confirm no public IP on private EC2
aws ec2 describe-instances --instance-ids <PRIVATE_INSTANCE_ID> \
  --query "Reservations[0].Instances[0].PublicIpAddress"
# Expected: null
```

---

## 5. Expected Successful Outputs

**Subnet table:**
```
Name              CIDR           AZ
public-subnet-a   10.0.1.0/24    us-east-1a
public-subnet-b   10.0.2.0/24    us-east-1b
private-app-a     10.0.3.0/24    us-east-1a
private-app-b     10.0.4.0/24    us-east-1b
private-db-a      10.0.5.0/24    us-east-1a
private-db-b      10.0.6.0/24    us-east-1b
```

**vpc_checker.py output:**
```
✅ VPC: vpc-0abc123  CIDR=10.0.0.0/16  State=available
✅ Internet Gateway: igw-0abc123  Attached=True
✅ NAT Gateway: nat-0abc123  State=available
✅ Public RT: 0.0.0.0/0 → igw-xxx
✅ Private RT: 0.0.0.0/0 → nat-xxx
✅ 6 subnets found (2 public, 4 private)
```

---

## 6. Verification Checklist

- [ ] VPC `handson-vpc` CIDR = `10.0.0.0/16`, state = available
- [ ] DNS hostnames enabled on VPC
- [ ] 6 subnets across 2 AZs with correct CIDRs
- [ ] Public subnets: auto-assign public IP = enabled
- [ ] Private subnets: auto-assign public IP = disabled
- [ ] IGW `handson-igw` attached to VPC
- [ ] NAT Gateway `handson-nat` in public subnet, state = available
- [ ] NAT Gateway has Elastic IP
- [ ] Public RT: `0.0.0.0/0 → igw-xxx`
- [ ] Private RT: `0.0.0.0/0 → nat-xxx`
- [ ] All 4 private subnets associated with private RT
- [ ] Private EC2 can reach internet via NAT (checkip returns NAT EIP)
- [ ] `terraform plan` shows no changes
- [ ] `vpc_checker.py` shows all ✅

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
