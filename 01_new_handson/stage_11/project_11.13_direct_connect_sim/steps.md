# Steps — Project 11.13 Direct Connect Simulation (BGP over VPN)

## Phase 1 — Console

### 1.1 Create AWS VPC
- VPC: `vpc-aws-11-13`, CIDR: `10.0.0.0/16`
- Private subnet: `10.0.1.0/24`

### 1.2 Create "On-Premises" VPC
- VPC: `vpc-onprem-11-13`, CIDR: `192.168.0.0/16`
- Public subnet: `192.168.1.0/24` with IGW
- Launch EC2: `ec2-bgp-11-13`, Amazon Linux 2023, t3.micro, public IP

### 1.3 Create VGW with Custom ASN
1. **VPC** → **Virtual Private Gateways** → **Create**
2. Name: `vgw-11-13`
3. ASN: Custom → `64512`
4. Attach to `vpc-aws-11-13`

### 1.4 Create Customer Gateway with BGP ASN
1. **VPC** → **Customer Gateways** → **Create**
2. Name: `cgw-bgp-11-13`
3. Routing: **Dynamic (BGP)**
4. BGP ASN: `65000`
5. IP address: `<EC2 BGP public IP>`

### 1.5 Create VPN Connection (Dynamic/BGP)
1. VGW: `vgw-11-13`, CGW: `cgw-bgp-11-13`
2. Routing: **Dynamic (BGP)**
3. Download configuration after creation

### 1.6 Enable Route Propagation
- Private subnet route table → Route propagation → Enable for `vgw-11-13`

### 1.7 Install and Configure Bird BGP on EC2
```bash
sudo yum install -y bird
```

---

## Phase 2 — Bird BGP Configuration

```bash
# /etc/bird.conf
sudo tee /etc/bird.conf << 'CONF'
router id <EC2_PRIVATE_IP>;

protocol kernel {
    export all;
    import all;
}

protocol device {
    scan time 10;
}

protocol static {
    route 192.168.0.0/16 via <EC2_PRIVATE_IP>;
}

protocol bgp aws_tunnel1 {
    local as 65000;
    neighbor <AWS_TUNNEL1_INSIDE_IP> as 64512;
    export all;
    import all;
    hold time 30;
    keepalive time 10;
}
CONF

sudo systemctl enable bird
sudo systemctl start bird
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check VPN connection and BGP status
aws ec2 describe-vpn-connections \
  --filters "Name=tag:Name,Values=vpn-bgp-11-13" \
  --query "VpnConnections[*].{State:State,Tunnels:VgwTelemetry[*].{IP:OutsideIpAddress,Status:Status,Routes:AcceptedRouteCount}}"

# 2. Check BGP session on EC2
ssh -i key.pem ec2-user@<EC2_PUBLIC_IP>
sudo birdc show protocols
# Expected: aws_tunnel1  BGP  up  Established

# 3. Check BGP routes received from AWS
sudo birdc show route
# Should show 10.0.0.0/16 learned via BGP

# 4. Check AWS route table has on-premises route via BGP propagation
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<AWS_VPC_ID>" \
  --query "RouteTables[*].Routes[?Origin=='EnableVgwRoutePropagation']"
# Should show 192.168.0.0/16 → vgw-xxx (BGP propagated)
```

---

## Phase 5 — Test

```bash
# From BGP EC2 (on-premises simulation):

# Test 1: Ping AWS private EC2 (BGP-routed path)
ping -c 5 <AWS_PRIVATE_EC2_IP>
# Expected: success — route learned via BGP

# Test 2: Verify BGP route details
sudo birdc show route detail
# Shows: 10.0.0.0/16 via BGP, AS path: 64512

# Test 3: Simulate route withdrawal (Direct Connect failover concept)
# Remove the static route from Bird config, reload
sudo birdc configure
# AWS route table should remove 192.168.0.0/16 within ~30s (BGP hold timer)

# Test 4: Re-advertise route
# Add route back to Bird config
sudo birdc configure
# AWS route table should re-add 192.168.0.0/16 within ~10s

# Test 5: Check BGP session stays up with keepalives
sudo birdc show protocols all aws_tunnel1
# Look for: Hold timer, Keepalive timer, Last error: none

# Test 6: Compare with Direct Connect concepts
# BGP over VPN = same routing protocol as Direct Connect
# Difference: VPN uses internet; DX uses dedicated fiber
# Both use BGP for route exchange

# Run automated checker
python code/bgp_checker.py --vpn-name vpn-bgp-11-13
```

### Verification Checklist
- [ ] VGW created with ASN 64512
- [ ] CGW created with BGP ASN 65000
- [ ] VPN connection type = dynamic (BGP)
- [ ] At least 1 tunnel UP
- [ ] Bird BGP session shows Established
- [ ] Bird shows AWS route `10.0.0.0/16` learned via BGP
- [ ] AWS route table shows `192.168.0.0/16` via BGP propagation
- [ ] Ping from on-prem EC2 to AWS private EC2 succeeds
- [ ] Route withdrawal removes route from AWS table within 30s
- [ ] Route re-advertisement restores route within 10s

---

## Teardown
```bash
terraform destroy
```
