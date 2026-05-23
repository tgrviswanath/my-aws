# Verification & Validation — Project 11.13 Direct Connect Simulation (BGP over VPN)

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| VGW | VPC → Virtual Private Gateways | `vgw-11-13`, ASN = 64512, attached to AWS VPC |
| CGW | VPC → Customer Gateways | `cgw-bgp-11-13`, Routing = Dynamic (BGP), ASN = 65000 |
| VPN Connection | VPC → Site-to-Site VPN | `vpn-bgp-11-13`, Routing = Dynamic, Tunnel UP |
| Propagated Routes | Route Tables → Routes | `192.168.0.0/16` with Origin = EnableVgwRoutePropagation |
| Accepted Routes | VPN Connection → Tunnel details | AcceptedRouteCount > 0 |

📸 Screenshot: VPN connection showing Dynamic routing and tunnel UP  
📸 Screenshot: Route table showing BGP-propagated route `192.168.0.0/16`  
📸 Screenshot: Bird BGP `show protocols` output showing Established

---

## 2. AWS CLI Verification

```bash
# 2.1 VPN connection — confirm dynamic routing and accepted routes
aws ec2 describe-vpn-connections \
  --filters "Name=tag:Name,Values=vpn-bgp-11-13" \
  --query "VpnConnections[*].{State:State,Type:Type,Tunnels:VgwTelemetry[*].{IP:OutsideIpAddress,Status:Status,Routes:AcceptedRouteCount}}"
# Expected: Type=ipsec.1, tunnel UP, AcceptedRouteCount > 0

# 2.2 BGP-propagated route in AWS route table
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<AWS_VPC_ID>" \
  --query "RouteTables[*].Routes[?Origin=='EnableVgwRoutePropagation'].{Dest:DestinationCidrBlock,GW:GatewayId}"
# Expected: Dest=192.168.0.0/16 (BGP-learned from on-prem)

# 2.3 Bird BGP session on EC2
ssh -i key.pem ec2-user@<EC2_PUBLIC_IP>
sudo birdc show protocols
# Expected: aws_tunnel1  BGP  up  Established

# 2.4 BGP routes received from AWS
sudo birdc show route
# Expected: 10.0.0.0/16 via BGP (learned from AWS ASN 64512)

# 2.5 Connectivity test
ping -c 5 <AWS_PRIVATE_EC2_IP>   # succeeds via BGP-routed tunnel
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpn_gateway.main
# aws_customer_gateway.bgp
# aws_vpn_connection.bgp
# aws_vpn_gateway_route_propagation.main

terraform state show aws_customer_gateway.bgp
# Shows: bgp_asn=65000, type=ipsec.1, ip_address=<EC2_PUBLIC_IP>

terraform state show aws_vpn_connection.bgp
# Shows: type=ipsec.1, static_routes_only=false (dynamic BGP)

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — BGP Route Withdrawal

```bash
# Simulate Direct Connect failover — withdraw route and confirm AWS removes it
ssh -i key.pem ec2-user@<EC2_PUBLIC_IP>

# Remove static route from Bird config (simulates route withdrawal)
sudo birdc configure   # after editing /etc/bird.conf to remove the static route

# AWS route table should remove 192.168.0.0/16 within ~30s (BGP hold timer)
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<AWS_VPC_ID>" \
  --query "RouteTables[*].Routes[?Origin=='EnableVgwRoutePropagation']"
# Expected: empty — route withdrawn

# Re-advertise route
sudo birdc configure   # after restoring the static route in /etc/bird.conf
# Route reappears in AWS route table within ~10s
```

---

## 5. Expected Successful Outputs

**Bird BGP protocols:**
```
Name       Proto  State  Since    Info
aws_tunnel1  BGP    up     12:34:56  Established
```

**Bird routes:**
```
10.0.0.0/16  via 169.254.x.x on vti0 [aws_tunnel1 12:34:56] * (100/0) [AS64512i]
```

**AWS route table (BGP propagated):**
```json
[{ "Dest": "192.168.0.0/16", "GW": "vgw-0abc123" }]
```

**After route withdrawal:**
```json
[]   ← route removed from AWS table within 30s
```

---

## 6. Verification Checklist

- [ ] VGW created with ASN 64512
- [ ] CGW created with BGP ASN 65000, routing = Dynamic
- [ ] VPN connection type = dynamic (BGP), at least 1 tunnel UP
- [ ] AcceptedRouteCount > 0 in tunnel telemetry
- [ ] Bird BGP session shows Established
- [ ] Bird shows AWS route `10.0.0.0/16` learned via BGP
- [ ] AWS route table shows `192.168.0.0/16` via BGP propagation
- [ ] Ping from on-prem EC2 to AWS private EC2 succeeds
- [ ] Route withdrawal removes route from AWS table within 30s
- [ ] Route re-advertisement restores route within 10s
- [ ] `terraform plan` shows no changes
