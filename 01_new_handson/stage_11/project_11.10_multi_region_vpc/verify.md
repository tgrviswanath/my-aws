# Verification & Validation — Project 11.10 Multi-Region VPC Architecture

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC us-east-1 | VPC console (us-east-1) | `vpc-east-11-10`, CIDR `10.0.0.0/16` |
| VPC us-west-2 | VPC console (us-west-2) | `vpc-west-11-10`, CIDR `10.1.0.0/16` |
| Peering Connection | VPC → Peering Connections (either region) | `pcx-east-west-11-10`, Status = **active** |
| us-east-1 Route Table | Route Tables → Routes | `10.1.0.0/16 → pcx-xxx` |
| us-west-2 Route Table | Route Tables → Routes | `10.0.0.0/16 → pcx-xxx` |

📸 Screenshot: Peering connection showing inter-region (us-east-1 ↔ us-west-2) with status = active  
📸 Screenshot: us-east-1 route table showing `10.1.0.0/16 → pcx-xxx`  
📸 Screenshot: Ping output showing ~60-80ms RTT (cross-region latency)

---

## 2. AWS CLI Verification

```bash
# 2.1 Peering status from us-east-1
aws ec2 describe-vpc-peering-connections \
  --filters "Name=tag:Name,Values=pcx-east-west-11-10" \
  --region us-east-1 \
  --query "VpcPeeringConnections[*].{ID:VpcPeeringConnectionId,Status:Status.Code,RequesterRegion:RequesterVpcInfo.Region,AccepterRegion:AccepterVpcInfo.Region}"
# Expected: Status=active, regions show us-east-1 and us-west-2

# 2.2 Routes in us-east-1
aws ec2 describe-route-tables --route-table-ids $RT_EAST --region us-east-1 \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null].{Dest:DestinationCidrBlock,PCX:VpcPeeringConnectionId}"
# Expected: Dest=10.1.0.0/16

# 2.3 Routes in us-west-2
aws ec2 describe-route-tables --route-table-ids $RT_WEST --region us-west-2 \
  --query "RouteTables[0].Routes[?VpcPeeringConnectionId!=null].{Dest:DestinationCidrBlock,PCX:VpcPeeringConnectionId}"
# Expected: Dest=10.0.0.0/16

# 2.4 Cross-region connectivity
ssh -i key.pem ec2-user@<EC2_EAST_PUBLIC_IP>
ping -c 10 <EC2_WEST_PRIVATE_IP>   # ~60-80ms RTT
ssh ec2-user@<EC2_WEST_PRIVATE_IP>  # succeeds via private IP
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpc.east
# aws_vpc.west
# aws_subnet.east
# aws_subnet.west
# aws_vpc_peering_connection.east_to_west
# aws_vpc_peering_connection_accepter.west
# aws_route.east_to_west
# aws_route.west_to_east

terraform state show aws_vpc_peering_connection.east_to_west
# Shows: id, vpc_id, peer_vpc_id, peer_region=us-west-2, accept_status=active

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Measure and record cross-region latency
ping -c 20 <EC2_WEST_PRIVATE_IP> | tail -1
# Expected: avg ~60-80ms (us-east-1 to us-west-2 over AWS backbone)

# Compare private (peering) vs public (internet) latency
ping -c 5 <EC2_WEST_PRIVATE_IP>   # via peering
ping -c 5 <EC2_WEST_PUBLIC_IP>    # via internet
# Both should be similar — peering uses AWS backbone, not public internet
```

---

## 5. Expected Successful Outputs

**CLI — peering connection:**
```json
[{
  "ID": "pcx-0abc123",
  "Status": "active",
  "RequesterRegion": "us-east-1",
  "AccepterRegion": "us-west-2"
}]
```

**Cross-region ping:**
```
PING 10.1.1.x: 56 data bytes
64 bytes from 10.1.1.x: icmp_seq=0 ttl=63 time=67.4 ms
--- 10.1.1.x ping statistics ---
10 packets transmitted, 10 received, 0% packet loss
round-trip min/avg/max = 65.2/67.4/70.1 ms
```

---

## 6. Verification Checklist

- [ ] VPC in us-east-1 with CIDR `10.0.0.0/16`
- [ ] VPC in us-west-2 with CIDR `10.1.0.0/16`
- [ ] Inter-region peering status = active
- [ ] us-east-1 route table: `10.1.0.0/16 → pcx`
- [ ] us-west-2 route table: `10.0.0.0/16 → pcx`
- [ ] Ping from EC2-East to EC2-West private IP succeeds
- [ ] Latency ~60-80ms (cross-region over AWS backbone)
- [ ] SSH from EC2-East to EC2-West private IP succeeds
- [ ] Resources in both regions destroyed on `terraform destroy`
- [ ] `terraform plan` shows no changes
