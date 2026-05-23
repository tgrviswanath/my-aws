# Verification & Validation — Project 11.2 Two-Tier Architecture with NAT Gateway

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC | VPC → Your VPCs | `vpc-11-2`, State = **available** |
| Public Subnet | VPC → Subnets | `public-subnet-11-2`, Auto-assign public IP = **Yes** |
| Private Subnet | VPC → Subnets | `private-subnet-11-2`, Auto-assign public IP = **No** |
| NAT Gateway | VPC → NAT Gateways | `nat-11-2`, State = **available**, Subnet = public |
| Elastic IP | EC2 → Elastic IPs | Allocated and associated with NAT Gateway |
| Public Route Table | Routes tab | `0.0.0.0/0 → igw-11-2` |
| Private Route Table | Routes tab | `0.0.0.0/0 → nat-11-2` |
| Web EC2 | EC2 → Instances | Running, Public IP assigned |
| DB EC2 | EC2 → Instances | Running, **no** Public IP |

📸 Screenshot: NAT Gateway showing State = available with Elastic IP  
📸 Screenshot: Private route table showing `0.0.0.0/0 → nat-xxx`  
📸 Screenshot: DB EC2 instance with no public IP address

---

## 2. AWS CLI Verification

```bash
# 2.1 NAT Gateway — confirm available and in public subnet
aws ec2 describe-nat-gateways \
  --filter "Name=tag:Name,Values=nat-11-2" \
  --query "NatGateways[*].{ID:NatGatewayId,State:State,Subnet:SubnetId,EIP:NatGatewayAddresses[0].PublicIp}"
# Expected: State=available, EIP is not null

# 2.2 Private route table — confirm routes to NAT
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=private-rt-11-2" \
  --query "RouteTables[*].Routes[*].{Dest:DestinationCidrBlock,Target:NatGatewayId}"
# Expected: Dest=0.0.0.0/0, Target=nat-xxx

# 2.3 DB EC2 — confirm no public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ec2-db-11-2" "Name=instance-state-name,Values=running" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress}"
# Expected: PublicIP = null

# 2.4 From private EC2 — confirm outbound internet via NAT
# SSH to web EC2, then hop to private EC2:
ssh -i key.pem ec2-user@<WEB_PUBLIC_IP>
ssh -i key.pem ec2-user@<PRIVATE_EC2_IP>
curl -s https://checkip.amazonaws.com   # returns NAT Gateway's EIP, not EC2's IP
ping -c 3 8.8.8.8                        # succeeds

# 2.5 Confirm private EC2 is NOT reachable from internet
curl --max-time 5 http://<PRIVATE_EC2_IP>   # should timeout
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_vpc.main
# aws_subnet.public
# aws_subnet.private
# aws_internet_gateway.main
# aws_eip.nat
# aws_nat_gateway.main
# aws_route_table.public
# aws_route_table.private
# aws_route_table_association.public
# aws_route_table_association.private

# 3.2 Inspect NAT Gateway state
terraform state show aws_nat_gateway.main
# Shows: id, subnet_id, allocation_id, public_ip

# 3.3 Confirm outputs
terraform output
# Expected:
# vpc_id          = "vpc-xxx"
# nat_gateway_id  = "nat-xxx"
# nat_public_ip   = "x.x.x.x"

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check

```bash
# From private EC2 (via SSH hop through web EC2):
curl -s https://checkip.amazonaws.com   # must return NAT EIP, not private IP
ping -c 3 8.8.8.8                        # confirms outbound via NAT

# Confirm private EC2 has no direct inbound path:
# From your local machine:
nc -zv <PRIVATE_EC2_IP> 22   # must timeout — no direct SSH from internet
```

---

## 5. Expected Successful Outputs

**CLI — describe-nat-gateways:**
```json
[{ "ID": "nat-0abc123", "State": "available", "Subnet": "subnet-0abc123", "EIP": "54.x.x.x" }]
```

**CLI — private route table:**
```json
[[{ "Dest": "0.0.0.0/0", "Target": "nat-0abc123" }, { "Dest": "10.0.0.0/16", "Target": null }]]
```

**From private EC2 — checkip:**
```
54.x.x.x   ← NAT Gateway's Elastic IP (not the private EC2's IP)
```

**terraform output:**
```
vpc_id         = "vpc-0abc123"
nat_gateway_id = "nat-0abc123"
nat_public_ip  = "54.x.x.x"
```

---

## 6. Verification Checklist

- [ ] VPC with 2 subnets (public + private)
- [ ] NAT Gateway in public subnet, state = available
- [ ] NAT Gateway has an Elastic IP
- [ ] Public RT: `0.0.0.0/0 → igw`
- [ ] Private RT: `0.0.0.0/0 → nat`
- [ ] Web EC2 has public IP; DB EC2 has no public IP
- [ ] SSH to web EC2 succeeds
- [ ] From private EC2: `curl checkip.amazonaws.com` returns NAT's EIP
- [ ] Direct SSH to private EC2 from internet fails (timeout)
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows all 10 resources
