# Steps — Project 11.12 Site-to-Site VPN Connection

## Phase 1 — Console

### 1.1 Create AWS VPC (cloud side)
- VPC: `vpc-aws-11-12`, CIDR: `10.0.0.0/16`
- Private subnet: `private-aws-11-12`, `10.0.1.0/24`
- No IGW needed for private subnet (VPN provides connectivity)

### 1.2 Create "On-Premises" VPC (simulation)
- VPC: `vpc-onprem-11-12`, CIDR: `192.168.0.0/16`
- Public subnet: `public-onprem-11-12`, `192.168.1.0/24`
- IGW + route table (strongSwan needs internet to reach AWS VPN endpoint)
- Launch EC2: `ec2-strongswan-11-12`, Amazon Linux 2023, t3.micro, public IP

### 1.3 Create Virtual Private Gateway
1. **VPC** → **Virtual Private Gateways** → **Create**
2. Name: `vgw-11-12`
3. ASN: Amazon default (64512)
4. Create → **Actions** → **Attach to VPC** → `vpc-aws-11-12`

### 1.4 Create Customer Gateway
1. **VPC** → **Customer Gateways** → **Create**
2. Name: `cgw-11-12`
3. Routing: Static
4. IP address: `<strongSwan EC2 public IP>`
5. Create

### 1.5 Create VPN Connection
1. **VPC** → **Site-to-Site VPN Connections** → **Create**
2. Name: `vpn-11-12`
3. Virtual Private Gateway: `vgw-11-12`
4. Customer Gateway: `cgw-11-12`
5. Routing: Static
6. Static IP prefixes: `192.168.0.0/16` (on-premises CIDR)
7. Create (takes ~5 minutes)
8. Download configuration: Vendor=Generic, Platform=Generic, Software=Vendor Agnostic

### 1.6 Enable Route Propagation
1. Go to private subnet's route table
2. **Route propagation** tab → **Edit** → Enable for `vgw-11-12`
3. This auto-adds `192.168.0.0/16 → vgw-11-12`

### 1.7 Configure strongSwan on EC2
```bash
# SSH to strongSwan EC2
ssh -i key.pem ec2-user@<STRONGSWAN_PUBLIC_IP>

# Install strongSwan
sudo yum install -y strongswan

# Enable IP forwarding
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Phase 2 — strongSwan Configuration

Get tunnel details from the downloaded VPN config file, then:

```bash
# /etc/strongswan/ipsec.conf
sudo tee /etc/strongswan/ipsec.conf << 'CONF'
config setup
    charondebug="ike 1, knl 1, cfg 0"

conn aws-tunnel-1
    authby=secret
    left=%defaultroute
    leftid=<STRONGSWAN_PUBLIC_IP>
    leftsubnet=192.168.0.0/16
    right=<AWS_TUNNEL_1_OUTSIDE_IP>
    rightsubnet=10.0.0.0/16
    ike=aes128-sha1-modp1024
    esp=aes128-sha1
    keyingtries=%forever
    ikelifetime=28800s
    lifetime=3600s
    dpddelay=10s
    dpdtimeout=30s
    dpdaction=restart
    auto=start
CONF

# /etc/strongswan/ipsec.secrets
echo "<STRONGSWAN_PUBLIC_IP> <AWS_TUNNEL_1_OUTSIDE_IP> : PSK \"<PRE_SHARED_KEY>\"" \
  | sudo tee /etc/strongswan/ipsec.secrets

# Start strongSwan
sudo systemctl enable strongswan
sudo systemctl start strongswan
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
# Note: strongSwan config must be applied manually after getting tunnel IPs
```

---

## Phase 4 — Verify

```bash
# 1. Check VPN connection status
aws ec2 describe-vpn-connections \
  --filters "Name=tag:Name,Values=vpn-11-12" \
  --query "VpnConnections[*].{ID:VpnConnectionId,State:State,Tunnels:VgwTelemetry[*].{Outside:OutsideIpAddress,Status:Status}}"
# Expected: at least 1 tunnel UP

# 2. Check VGW attachment
aws ec2 describe-vpn-gateways \
  --filters "Name=tag:Name,Values=vgw-11-12" \
  --query "VpnGateways[*].{ID:VpnGatewayId,State:State,Attachments:VpcAttachments}"

# 3. Check route propagation worked
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<AWS_VPC_ID>" \
  --query "RouteTables[*].Routes[?GatewayId!=null]"
# Should show 192.168.0.0/16 → vgw-xxx

# 4. Check strongSwan tunnel status
ssh -i key.pem ec2-user@<STRONGSWAN_PUBLIC_IP>
sudo strongswan status
# Expected: ESTABLISHED, INSTALLED
```

---

## Phase 5 — Test

```bash
# From strongSwan EC2 (simulated on-premises):

# Test 1: Ping AWS private EC2 via VPN tunnel
ping -c 5 <AWS_PRIVATE_EC2_IP>
# Expected: success — traffic goes through IPSec tunnel

# Test 2: SSH to AWS private EC2 via VPN
ssh -i key.pem ec2-user@<AWS_PRIVATE_EC2_IP>
# Expected: success — no public IP needed on AWS side

# Test 3: Verify traffic goes through tunnel (not internet)
traceroute <AWS_PRIVATE_EC2_IP>
# Should show 1-2 hops (tunnel is transparent)

# Test 4: Check tunnel is using IPSec (encrypted)
sudo tcpdump -i eth0 esp
# Should show ESP (Encapsulating Security Payload) packets

# Test 5: Simulate tunnel failure — stop strongSwan, verify DPD kicks in
sudo systemctl stop strongswan
# AWS console: tunnel should show DOWN after ~30s
sudo systemctl start strongswan
# Tunnel should re-establish automatically

# Test 6: From AWS private EC2, reach on-premises
ping -c 5 <STRONGSWAN_PRIVATE_IP>   # 192.168.1.x
# Expected: success

# Run automated checker
python code/vpn_checker.py --vpn-name vpn-11-12
```

### Verification Checklist
- [ ] VGW created and attached to AWS VPC
- [ ] CGW created with strongSwan public IP
- [ ] VPN connection created, at least 1 tunnel UP
- [ ] Route propagation enabled — `192.168.0.0/16 → vgw` in AWS route table
- [ ] strongSwan shows ESTABLISHED
- [ ] Ping from on-prem EC2 to AWS private EC2 succeeds
- [ ] SSH from on-prem EC2 to AWS private EC2 succeeds
- [ ] Ping from AWS private EC2 to on-prem EC2 succeeds
- [ ] Traffic confirmed as ESP (encrypted) via tcpdump
- [ ] Tunnel auto-recovers after strongSwan restart

---

## Teardown
```bash
terraform destroy
# Order: VPN connection → CGW → VGW detach → VGW → EC2
```
