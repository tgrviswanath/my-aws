# Steps — Project 11.11 AWS Transit Gateway Hub

## Phase 1 — Console

### 1.1 Create Three VPCs
| Name | CIDR | Subnet |
|------|------|--------|
| vpc-a-11-11 | 10.0.0.0/16 | 10.0.1.0/24 (us-east-1a) |
| vpc-b-11-11 | 10.1.0.0/16 | 10.1.1.0/24 (us-east-1b) |
| vpc-c-11-11 | 10.2.0.0/16 | 10.2.1.0/24 (us-east-1c) |

### 1.2 Create Transit Gateway
1. **VPC** → **Transit Gateways** → **Create transit gateway**
2. Name: `tgw-11-11`
3. ASN: 64512 (default)
4. DNS support: Enable
5. VPN ECMP support: Enable
6. Default route table association: Enable
7. Default route table propagation: Enable
8. Create (takes ~5 minutes)

### 1.3 Create TGW Attachments (one per VPC)
For each VPC:
1. **VPC** → **Transit Gateway Attachments** → **Create**
2. Transit Gateway: `tgw-11-11`
3. Attachment type: VPC
4. VPC: select the VPC
5. Subnet: select the subnet in that VPC
6. Name: `tgw-attach-a-11-11` (etc.)
7. Create

### 1.4 Update VPC Route Tables
For each VPC, add routes to the other two VPCs via TGW:

**VPC-A route table:**
- `10.1.0.0/16 → tgw-11-11`
- `10.2.0.0/16 → tgw-11-11`

**VPC-B route table:**
- `10.0.0.0/16 → tgw-11-11`
- `10.2.0.0/16 → tgw-11-11`

**VPC-C route table:**
- `10.0.0.0/16 → tgw-11-11`
- `10.1.0.0/16 → tgw-11-11`

---

## Phase 2 — AWS CLI

```bash
# Create TGW
TGW=$(aws ec2 create-transit-gateway \
  --description "TGW for project 11.11" \
  --options "AmazonSideAsn=64512,DnsSupport=enable,VpnEcmpSupport=enable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable" \
  --query "TransitGateway.TransitGatewayId" --output text)
aws ec2 create-tags --resources $TGW --tags Key=Name,Value=tgw-11-11
echo "Waiting for TGW to be available..."
aws ec2 wait transit-gateway-available --transit-gateway-ids $TGW 2>/dev/null || sleep 60

# Create attachments (repeat for each VPC/subnet)
ATTACH_A=$(aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id $TGW \
  --vpc-id $VPC_A \
  --subnet-ids $SUBNET_A \
  --query "TransitGatewayVpcAttachment.TransitGatewayAttachmentId" --output text)
aws ec2 create-tags --resources $ATTACH_A --tags Key=Name,Value=tgw-attach-a-11-11

# Add routes in each VPC route table
aws ec2 create-route --route-table-id $RT_A \
  --destination-cidr-block 10.1.0.0/16 --transit-gateway-id $TGW
aws ec2 create-route --route-table-id $RT_A \
  --destination-cidr-block 10.2.0.0/16 --transit-gateway-id $TGW
# Repeat for VPC-B and VPC-C

echo "TGW: $TGW"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check TGW state
aws ec2 describe-transit-gateways \
  --filters "Name=tag:Name,Values=tgw-11-11" \
  --query "TransitGateways[*].{ID:TransitGatewayId,State:State}"
# Expected: available

# 2. Check all attachments are available
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=transit-gateway-id,Values=$TGW" \
  --query "TransitGatewayVpcAttachments[*].{Name:Tags[?Key=='Name']|[0].Value,State:State,VPC:VpcId}"
# Expected: all available

# 3. Check TGW route table has all 3 VPC CIDRs
aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=$TGW"
TGW_RT=$(aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=$TGW" \
  --query "TransitGatewayRouteTables[0].TransitGatewayRouteTableId" --output text)
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RT \
  --filters "Name=state,Values=active" \
  --query "Routes[*].{CIDR:DestinationCidrBlock,State:State}"
```

---

## Phase 5 — Test

```bash
# Launch EC2 in each VPC (private subnets, no public IP — use SSM or bastion)

# Test 1: A → B (direct hop via TGW)
# From EC2-A:
ping -c 5 <EC2_B_PRIVATE_IP>   # should succeed (~1ms — same region)
ssh ec2-user@<EC2_B_PRIVATE_IP>

# Test 2: A → C (transitive via TGW — this would FAIL with peering)
ping -c 5 <EC2_C_PRIVATE_IP>   # should succeed (TGW is transitive)

# Test 3: B → C
ping -c 5 <EC2_C_PRIVATE_IP>   # should succeed

# Test 4: Segmentation — add a second TGW route table for isolation
# Create route table "isolated-rt", associate VPC-C, no propagation from A/B
# VPC-C should then be unreachable from A and B

# Test 5: Traceroute to see TGW hop
traceroute <EC2_B_PRIVATE_IP>
# Should show 1 hop (TGW is transparent — no visible hop in traceroute)

# Run automated checker
python code/tgw_checker.py --tgw-id $TGW
```

### Verification Checklist
- [ ] Transit Gateway state = available
- [ ] 3 VPC attachments, all state = available
- [ ] TGW route table has all 3 VPC CIDRs propagated
- [ ] VPC route tables have routes to other VPCs via TGW
- [ ] EC2-A can ping EC2-B (direct)
- [ ] EC2-A can ping EC2-C (transitive — proves TGW advantage over peering)
- [ ] EC2-B can ping EC2-C
- [ ] All 3 VPCs can communicate with each other

---

## Teardown
```bash
terraform destroy
# TGW costs $0.05/hr — destroy immediately after lab
```
