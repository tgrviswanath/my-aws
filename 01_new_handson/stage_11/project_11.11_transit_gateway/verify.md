# Verification & Validation — Project 11.11 AWS Transit Gateway Hub

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Transit Gateway | VPC → Transit Gateways | `tgw-11-11`, State = **available** |
| TGW Attachment A | VPC → Transit Gateway Attachments | `tgw-attach-a-11-11`, State = **available** |
| TGW Attachment B | VPC → Transit Gateway Attachments | `tgw-attach-b-11-11`, State = **available** |
| TGW Attachment C | VPC → Transit Gateway Attachments | `tgw-attach-c-11-11`, State = **available** |
| TGW Route Table | VPC → Transit Gateway Route Tables | Default RT with all 3 VPC CIDRs propagated |
| VPC-A Route Table | Route Tables → Routes | `10.1.0.0/16` and `10.2.0.0/16` → `tgw-11-11` |

📸 Screenshot: Transit Gateway showing state = available  
📸 Screenshot: All 3 TGW attachments showing state = available  
📸 Screenshot: TGW route table showing all 3 VPC CIDRs (10.0/10.1/10.2)

---

## 2. AWS CLI Verification

```bash
# 2.1 TGW state
aws ec2 describe-transit-gateways \
  --filters "Name=tag:Name,Values=tgw-11-11" \
  --query "TransitGateways[*].{ID:TransitGatewayId,State:State,ASN:Options.AmazonSideAsn}"
# Expected: State=available

# 2.2 All 3 attachments available
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=transit-gateway-id,Values=$TGW" \
  --query "TransitGatewayVpcAttachments[*].{Name:Tags[?Key=='Name']|[0].Value,State:State,VPC:VpcId}"
# Expected: 3 entries, all State=available

# 2.3 TGW route table has all 3 CIDRs
TGW_RT=$(aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=$TGW" \
  --query "TransitGatewayRouteTables[0].TransitGatewayRouteTableId" --output text)
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RT \
  --filters "Name=state,Values=active" \
  --query "Routes[*].{CIDR:DestinationCidrBlock,State:State}"
# Expected: 10.0.0.0/16, 10.1.0.0/16, 10.2.0.0/16 all active

# 2.4 Transitivity test — A can reach C (impossible with peering)
ssh -i key.pem ec2-user@<EC2_A_PUBLIC_IP>
ping -c 5 <EC2_C_PRIVATE_IP>   # succeeds — TGW is transitive
ping -c 5 <EC2_B_PRIVATE_IP>   # succeeds
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_ec2_transit_gateway.main
# aws_ec2_transit_gateway_vpc_attachment.vpc_a
# aws_ec2_transit_gateway_vpc_attachment.vpc_b
# aws_ec2_transit_gateway_vpc_attachment.vpc_c
# aws_route.vpc_a_to_b / aws_route.vpc_a_to_c
# aws_route.vpc_b_to_a / aws_route.vpc_b_to_c
# aws_route.vpc_c_to_a / aws_route.vpc_c_to_b

terraform state show aws_ec2_transit_gateway.main
# Shows: id, amazon_side_asn, default_route_table_association=enable

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Confirm all 3 VPCs can reach each other (full mesh via TGW)
# From EC2-A:
ping -c 3 <EC2_B_PRIVATE_IP>   # A → B
ping -c 3 <EC2_C_PRIVATE_IP>   # A → C (transitive — key TGW advantage)

# From EC2-B:
ping -c 3 <EC2_A_PRIVATE_IP>   # B → A
ping -c 3 <EC2_C_PRIVATE_IP>   # B → C

# All 6 directions must succeed
```

---

## 5. Expected Successful Outputs

**TGW route table:**
```json
[
  { "CIDR": "10.0.0.0/16", "State": "active" },
  { "CIDR": "10.1.0.0/16", "State": "active" },
  { "CIDR": "10.2.0.0/16", "State": "active" }
]
```

**Transitivity proof (A → C, no direct peering):**
```
PING 10.2.1.x: 56 data bytes
64 bytes from 10.2.1.x: icmp_seq=0 ttl=63 time=0.9 ms
5 packets transmitted, 5 received, 0% packet loss
```

---

## 6. Verification Checklist

- [ ] Transit Gateway state = available
- [ ] 3 VPC attachments, all state = available
- [ ] TGW route table has all 3 VPC CIDRs propagated
- [ ] VPC route tables have routes to other VPCs via TGW
- [ ] EC2-A can ping EC2-B (direct)
- [ ] EC2-A can ping EC2-C (transitive — proves TGW advantage over peering)
- [ ] EC2-B can ping EC2-C
- [ ] All 6 directional pings succeed
- [ ] `terraform plan` shows no changes
