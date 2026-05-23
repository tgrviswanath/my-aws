# Verification & Validation — Project 11.19 IPv6 Implementation

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VPC | VPC → Your VPCs | `vpc-11-19`, both IPv4 (`10.0.0.0/16`) and IPv6 (`2600::/56`) CIDRs |
| Public Subnet | VPC → Subnets | IPv4 + IPv6 /64 CIDR, auto-assign IPv6 = **Yes** |
| Private Subnet | VPC → Subnets | IPv4 + IPv6 /64 CIDR, auto-assign IPv6 = **Yes** |
| Egress-Only IGW | VPC → Egress-only internet gateways | `eigw-11-19`, State = **attached** |
| Public RT | Route Tables → Routes | `::/0 → igw-11-19` (bidirectional IPv6) |
| Private RT | Route Tables → Routes | `::/0 → eigw-11-19` (outbound-only IPv6) |
| Public EC2 | EC2 → Instances | Has both IPv4 and IPv6 addresses |
| Private EC2 | EC2 → Instances | Has IPv6 address, no public IPv4 |

📸 Screenshot: VPC details showing both IPv4 and IPv6 CIDR blocks  
📸 Screenshot: Public EC2 instance showing IPv6 address assigned  
📸 Screenshot: `ping6 ipv6.google.com` succeeding from private EC2 (via EIGW)

---

## 2. AWS CLI Verification

```bash
# 2.1 VPC has IPv6 CIDR
aws ec2 describe-vpcs --vpc-ids $VPC_ID \
  --query "Vpcs[0].{IPv4:CidrBlock,IPv6:Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock,State:Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlockState.State}"
# Expected: IPv6 CIDR assigned, State=associated

# 2.2 Subnets have IPv6 /64 CIDRs
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,IPv4:CidrBlock,IPv6:Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock,AutoIPv6:AssignIpv6AddressOnCreation}"
# Expected: both subnets have /64 IPv6 CIDRs, AutoIPv6=true

# 2.3 Egress-Only IGW exists and attached
aws ec2 describe-egress-only-internet-gateways \
  --query "EgressOnlyInternetGateways[*].{ID:EgressOnlyInternetGatewayId,State:Attachments[0].State,VPC:Attachments[0].VpcId}"
# Expected: State=attached, VPC=vpc-11-19

# 2.4 Route tables have ::/0 routes
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,IPv6Routes:Routes[?DestinationIpv6CidrBlock!=null].{Dest:DestinationIpv6CidrBlock,Target:GatewayId}}"
# Public RT: ::/0 → igw-xxx
# Private RT: ::/0 → eigw-xxx

# 2.5 EC2 instances have IPv6 addresses
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,IPv4:PrivateIpAddress,IPv6:NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address}"
# Expected: both instances have IPv6 addresses
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpc.main                          (with amazon_provided_ipv6_cidr_block=true)
# aws_subnet.public                     (with ipv6_cidr_block)
# aws_subnet.private                    (with ipv6_cidr_block)
# aws_egress_only_internet_gateway.main
# aws_route.public_ipv6
# aws_route.private_ipv6

terraform state show aws_vpc.main
# Shows: ipv6_cidr_block assigned, amazon_provided_ipv6_cidr_block=true

terraform state show aws_egress_only_internet_gateway.main
# Shows: id, vpc_id

terraform output
# Expected: vpc_ipv6_cidr, public_subnet_ipv6, private_subnet_ipv6

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — IPv6 Connectivity Tests

```bash
# From public EC2:
ping6 -c 5 ipv6.google.com          # outbound IPv6 via IGW — succeeds
ping6 -c 5 <PRIVATE_EC2_IPV6>       # intra-VPC IPv6 — succeeds
ssh -6 -i key.pem ec2-user@<PUB_IPV6_ADDR>  # SSH via IPv6 — succeeds

# From private EC2:
ping6 -c 5 ipv6.google.com          # outbound via EIGW — succeeds
# From internet to private EC2:
ping6 <PRIV_IPV6_ADDR>              # must FAIL — EIGW blocks inbound
```

---

## 5. Expected Successful Outputs

**VPC IPv6 CIDR:**
```json
{ "IPv4": "10.0.0.0/16", "IPv6": "2600:1f18:xxxx:xx00::/56", "State": "associated" }
```

**Subnet IPv6 CIDRs:**
```
public-ipv6-11-19:  10.0.1.0/24  +  2600:1f18:xxxx:xx00::/64  AutoIPv6=true
private-ipv6-11-19: 10.0.2.0/24  +  2600:1f18:xxxx:xx01::/64  AutoIPv6=true
```

**Route tables:**
```
Public RT:  ::/0 → igw-xxx   (bidirectional)
Private RT: ::/0 → eigw-xxx  (outbound only)
```

**IPv6 connectivity:**
```
ping6 ipv6.google.com from public EC2:  ✅ success
ping6 ipv6.google.com from private EC2: ✅ success (via EIGW)
ping6 <private-ipv6> from internet:     ❌ no response (EIGW blocks inbound)
```

---

## 6. Verification Checklist

- [ ] VPC has both IPv4 (`10.0.0.0/16`) and IPv6 (`2600::/56`) CIDRs
- [ ] Public subnet has IPv6 /64 CIDR, auto-assign IPv6 = enabled
- [ ] Private subnet has IPv6 /64 CIDR, auto-assign IPv6 = enabled
- [ ] Egress-Only IGW created and attached to VPC
- [ ] Public RT: `::/0 → igw` (bidirectional IPv6)
- [ ] Private RT: `::/0 → eigw` (outbound-only IPv6)
- [ ] Public EC2 has both IPv4 and IPv6 addresses
- [ ] Private EC2 has IPv6 address (no public IPv4)
- [ ] SSH to public EC2 via IPv6 succeeds
- [ ] `ping6 ipv6.google.com` from public EC2 succeeds
- [ ] `ping6 ipv6.google.com` from private EC2 succeeds (via EIGW)
- [ ] Inbound ping6 to private EC2 from internet is blocked
- [ ] `terraform plan` shows no changes
