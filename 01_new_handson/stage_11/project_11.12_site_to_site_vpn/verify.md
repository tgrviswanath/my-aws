# Verification & Validation — Project 11.12 Site-to-Site VPN Connection

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Virtual Private Gateway | VPC → Virtual Private Gateways | `vgw-11-12`, State = **attached** to AWS VPC |
| Customer Gateway | VPC → Customer Gateways | `cgw-11-12`, IP = strongSwan public IP |
| VPN Connection | VPC → Site-to-Site VPN | `vpn-11-12`, State = **available**, Tunnel 1 = **UP** |
| Route Propagation | Route Tables → Route propagation tab | Enabled for `vgw-11-12` |
| Propagated Route | Route Tables → Routes | `192.168.0.0/16 → vgw-11-12` (auto-propagated) |

📸 Screenshot: VPN connection showing at least 1 tunnel UP (green)  
📸 Screenshot: Route table showing propagated route `192.168.0.0/16 → vgw-xxx`  
📸 Screenshot: strongSwan `sudo strongswan status` showing ESTABLISHED

---

## 2. AWS CLI Verification

```bash
# 2.1 VPN connection and tunnel status
aws ec2 describe-vpn-connections \
  --filters "Name=tag:Name,Values=vpn-11-12" \
  --query "VpnConnections[*].{ID:VpnConnectionId,State:State,Tunnels:VgwTelemetry[*].{IP:OutsideIpAddress,Status:Status}}"
# Expected: State=available, at least 1 tunnel Status=UP

# 2.2 VGW attachment
aws ec2 describe-vpn-gateways \
  --filters "Name=tag:Name,Values=vgw-11-12" \
  --query "VpnGateways[*].{ID:VpnGatewayId,State:State,VPC:VpcAttachments[0].VpcId}"
# Expected: State=available, VPC attached

# 2.3 Route propagation — on-premises CIDR auto-added
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<AWS_VPC_ID>" \
  --query "RouteTables[*].Routes[?GatewayId!=null && starts_with(GatewayId,'vgw-')].{Dest:DestinationCidrBlock,GW:GatewayId,Origin:Origin}"
# Expected: Dest=192.168.0.0/16, Origin=EnableVgwRoutePropagation

# 2.4 strongSwan tunnel status
ssh -i key.pem ec2-user@<STRONGSWAN_PUBLIC_IP>
sudo strongswan status
# Expected: ESTABLISHED, INSTALLED

# 2.5 Connectivity test
ping -c 5 <AWS_PRIVATE_EC2_IP>   # from strongSwan EC2 — succeeds via tunnel
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpn_gateway.main
# aws_customer_gateway.main
# aws_vpn_connection.main
# aws_vpn_gateway_route_propagation.main
# aws_vpc.aws_side
# aws_vpc.onprem_sim

terraform state show aws_vpn_connection.main
# Shows: id, vpn_gateway_id, customer_gateway_id, type=ipsec.1, tunnel1_address, tunnel1_preshared_key

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Confirm IPSec encryption — traffic must be ESP packets
ssh -i key.pem ec2-user@<STRONGSWAN_PUBLIC_IP>
sudo tcpdump -i eth0 esp -c 5
# Expected: ESP (Encapsulating Security Payload) packets visible during active traffic

# Tunnel auto-recovery test
sudo systemctl stop strongswan
# AWS console: tunnel shows DOWN after ~30s
sudo systemctl start strongswan
# Tunnel re-establishes automatically within ~30s
aws ec2 describe-vpn-connections \
  --filters "Name=tag:Name,Values=vpn-11-12" \
  --query "VpnConnections[0].VgwTelemetry[*].Status"
# Expected: UP again
```

---

## 5. Expected Successful Outputs

**CLI — VPN tunnels:**
```json
[{
  "ID": "vpn-0abc123",
  "State": "available",
  "Tunnels": [
    { "IP": "52.x.x.x", "Status": "UP" },
    { "IP": "52.x.x.x", "Status": "DOWN" }
  ]
}]
```

**strongSwan status:**
```
Security Associations (1 up, 0 connecting):
aws-tunnel-1[1]: ESTABLISHED 5 minutes ago
aws-tunnel-1{1}: INSTALLED, TUNNEL
aws-tunnel-1{1}: 192.168.0.0/16 === 10.0.0.0/16
```

**Propagated route:**
```json
[{ "Dest": "192.168.0.0/16", "GW": "vgw-0abc123", "Origin": "EnableVgwRoutePropagation" }]
```

---

## 6. Verification Checklist

- [ ] VGW created and attached to AWS VPC
- [ ] CGW created with strongSwan public IP
- [ ] VPN connection state = available, at least 1 tunnel UP
- [ ] Route propagation enabled on private subnet route table
- [ ] `192.168.0.0/16 → vgw-xxx` auto-propagated in AWS route table
- [ ] strongSwan shows ESTABLISHED
- [ ] Ping from on-prem EC2 to AWS private EC2 succeeds
- [ ] SSH from on-prem EC2 to AWS private EC2 succeeds
- [ ] Traffic confirmed as ESP (encrypted) via tcpdump
- [ ] Tunnel auto-recovers after strongSwan restart
- [ ] `terraform plan` shows no changes
