# Verification & Validation — Project 11.5 Three-Tier Web Application

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC | VPC → Your VPCs | `vpc-11-5`, State = available |
| 6 Subnets | VPC → Subnets | web-a/b (public IP=Yes), app-a/b and db-a/b (public IP=No) |
| 2 NAT Gateways | VPC → NAT Gateways | `nat-11-5-a` and `nat-11-5-b`, both State = available |
| Public RT | Route Tables → Routes | `0.0.0.0/0 → igw-11-5` |
| Private RT-a | Route Tables → Routes | `0.0.0.0/0 → nat-11-5-a` |
| Private RT-b | Route Tables → Routes | `0.0.0.0/0 → nat-11-5-b` |
| SG chaining | EC2 → Security Groups | app-sg source = web-sg; db-sg source = app-sg |

📸 Screenshot: Subnets list showing all 6 with correct AZ and public IP settings  
📸 Screenshot: Both NAT Gateways in available state  
📸 Screenshot: Private RT-a routes showing `0.0.0.0/0 → nat-a`

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm all 6 subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,CIDR:CidrBlock,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}" \
  --output table
# Expected: 6 rows, web subnets PublicIP=true, app/db subnets PublicIP=false

# 2.2 Confirm both NAT Gateways available
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query "NatGateways[*].{ID:NatGatewayId,State:State,Subnet:SubnetId}"
# Expected: 2 entries, both State=available

# 2.3 Confirm AZ-affinity — private-rt-a routes to nat-a, private-rt-b routes to nat-b
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,NATTarget:Routes[?NatGatewayId!=null].NatGatewayId}"

# 2.4 Connectivity tests
# From app EC2 (private): outbound internet via NAT
curl -s https://checkip.amazonaws.com   # returns NAT EIP

# From web EC2: cannot reach DB directly
nc -zv <DB_PRIVATE_IP> 3306   # timeout
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected (key resources):
# aws_vpc.main
# aws_subnet.web_a / aws_subnet.web_b
# aws_subnet.app_a / aws_subnet.app_b
# aws_subnet.db_a  / aws_subnet.db_b
# aws_eip.nat_a / aws_eip.nat_b
# aws_nat_gateway.nat_a / aws_nat_gateway.nat_b
# aws_route_table.public
# aws_route_table.private_a / aws_route_table.private_b

terraform output
# Expected: vpc_id, nat_a_ip, nat_b_ip, all subnet IDs

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# AZ failure simulation — stop nat-a, verify app-a traffic fails but app-b still works
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" \
  --query "NatGateways[*].{ID:NatGatewayId,State:State}"
# Both must be available before running the lab
```

---

## 5. Expected Successful Outputs

**Subnet table:**
```
Name           CIDR          AZ          PublicIP
web-public-a   10.0.1.0/24   us-east-1a  true
web-public-b   10.0.2.0/24   us-east-1b  true
app-private-a  10.0.3.0/24   us-east-1a  false
app-private-b  10.0.4.0/24   us-east-1b  false
db-private-a   10.0.5.0/24   us-east-1a  false
db-private-b   10.0.6.0/24   us-east-1b  false
```

---

## 6. Verification Checklist

- [ ] VPC with 6 subnets across 2 AZs
- [ ] Web subnets: auto-assign public IP = enabled
- [ ] App/DB subnets: auto-assign public IP = disabled
- [ ] 2 NAT Gateways, one per AZ, both available
- [ ] Public RT: `0.0.0.0/0 → igw`
- [ ] Private RT-a: `0.0.0.0/0 → nat-a`
- [ ] Private RT-b: `0.0.0.0/0 → nat-b`
- [ ] SG chaining: web → app → db
- [ ] App EC2 can reach internet via NAT
- [ ] DB EC2 unreachable from internet
- [ ] `terraform plan` shows no changes
