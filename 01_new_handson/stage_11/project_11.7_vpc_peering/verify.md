# Verification & Validation — Project 11.7 VPC Peering Connection

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Peering Connection | VPC → Peering Connections | `pcx-11-7`, Status = **active** |
| VPC-A Route Table | Route Tables → Routes | `10.1.0.0/16 → pcx-11-7` |
| VPC-B Route Table | Route Tables → Routes | `10.0.0.0/16 → pcx-11-7` |
| EC2-A SG | EC2 → Security Groups | Inbound ICMP + SSH from `10.1.0.0/16` |
| EC2-B SG | EC2 → Security Groups | Inbound ICMP + SSH from `10.0.0.0/16` |

📸 Screenshot: Peering connection showing Status = active with both VPC IDs  
📸 Screenshot: VPC-A route table showing `10.1.0.0/16 → pcx-xxx`  
📸 Screenshot: Successful ping from EC2-A to EC2-B private IP

---

## 2. AWS CLI Verification

```bash
# 2.1 Peering connection status
aws ec2 describe-vpc-peering-connections \
  --filters "Name=tag:Name,Values=pcx-11-7" \
  --query "VpcPeeringConnections[*].{ID:VpcPeeringConnectionId,Status:Status.Code,VPC_A:RequesterVpcInfo.VpcId,VPC_B:AccepterVpcInfo.VpcId}"
# Expected: Status=active

# 2.2 Routes in VPC-A
aws ec2 describe-route-tables --route-table-ids $RT_A \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null].{Dest:DestinationCidrBlock,PCX:VpcPeeringConnectionId}"
# Expected: Dest=10.1.0.0/16

# 2.3 Routes in VPC-B
aws ec2 describe-route-tables --route-table-ids $RT_B \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null].{Dest:DestinationCidrBlock,PCX:VpcPeeringConnectionId}"
# Expected: Dest=10.0.0.0/16

# 2.4 Connectivity — from EC2-A ping EC2-B private IP
ssh -i key.pem ec2-user@<EC2_A_PUBLIC_IP>
ping -c 5 <EC2_B_PRIVATE_IP>   # succeeds
ssh ec2-user@<EC2_B_PRIVATE_IP>  # succeeds

# 2.5 Non-transitivity test — create VPC-C, peer only with VPC-B
# EC2-A should NOT reach EC2-C (no direct peering A↔C)
ping -c 3 <EC2_C_PRIVATE_IP>   # fails — non-transitive confirmed
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpc.vpc_a
# aws_vpc.vpc_b
# aws_subnet.subnet_a
# aws_subnet.subnet_b
# aws_vpc_peering_connection.main
# aws_vpc_peering_connection_accepter.main
# aws_route.vpc_a_to_b
# aws_route.vpc_b_to_a

terraform state show aws_vpc_peering_connection.main
# Shows: id, vpc_id, peer_vpc_id, accept_status=active

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Confirm both sides have routes — missing one side = one-way traffic only
aws ec2 describe-route-tables --route-table-ids $RT_A \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null]"
aws ec2 describe-route-tables --route-table-ids $RT_B \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null]"
# Both must return a result — if one is empty, traffic is one-directional
```

---

## 5. Expected Successful Outputs

**CLI — peering connection:**
```json
[{ "ID": "pcx-0abc123", "Status": "active", "VPC_A": "vpc-0abc", "VPC_B": "vpc-0def" }]
```

**Ping from EC2-A to EC2-B:**
```
PING 10.1.1.x (10.1.1.x): 56 data bytes
64 bytes from 10.1.1.x: icmp_seq=0 ttl=64 time=0.8 ms
--- 10.1.1.x ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

**Non-transitivity test:**
```
ping: connect: Network is unreachable   ← EC2-A cannot reach EC2-C via VPC-B
```

---

## 6. Verification Checklist

- [ ] VPC-A and VPC-B have non-overlapping CIDRs
- [ ] Peering connection status = active
- [ ] VPC-A route table: `10.1.0.0/16 → pcx-xxx`
- [ ] VPC-B route table: `10.0.0.0/16 → pcx-xxx`
- [ ] SGs allow ICMP from the other VPC's CIDR
- [ ] Ping from EC2-A to EC2-B private IP succeeds
- [ ] SSH from EC2-A to EC2-B private IP succeeds
- [ ] Non-transitivity confirmed (A cannot reach C via B)
- [ ] `terraform plan` shows no changes
