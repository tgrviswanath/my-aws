# Route 53, VPN & Direct Connect — DNS and Hybrid Connectivity

## Route 53 — DNS Service

Route 53 is AWS's highly available DNS service. It also provides health checking and traffic routing policies.

### Record Types

| Record | Purpose | Example |
|--------|---------|---------|
| A | IPv4 address | example.com → 1.2.3.4 |
| AAAA | IPv6 address | example.com → 2001:db8::1 |
| CNAME | Alias to another name | www → example.com |
| Alias | AWS resource alias (free queries) | example.com → ALB DNS |
| MX | Mail server | example.com → mail.example.com |
| TXT | Text (SPF, DKIM, verification) | "v=spf1 include:..." |
| NS | Name servers | Delegation |
| SOA | Start of authority | Zone metadata |

**Alias vs CNAME**: Alias records are AWS-specific, work at zone apex (example.com), free queries, auto-update when resource IP changes. Use Alias for AWS resources (ALB, CloudFront, S3 website, API Gateway).

### Routing Policies

```bash
# Simple routing
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "my-alb-123.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### Routing Policy Comparison

| Policy | Use Case | How it works |
|--------|---------|-------------|
| Simple | Single resource | Returns one value |
| Weighted | A/B testing, gradual migration | Split traffic by weight (e.g., 90/10) |
| Latency | Multi-region | Route to lowest latency region |
| Failover | Active-passive DR | Primary until health check fails |
| Geolocation | Compliance, localization | Route by user's country/continent |
| Geoproximity | Traffic shifting by location | Route by distance + bias |
| Multi-value | Simple load balancing | Return up to 8 healthy records |

```bash
# Weighted routing (blue/green deployment)
# Blue: weight 90
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "A",
        "SetIdentifier": "blue",
        "Weight": 90,
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "blue-alb.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# Failover routing
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "HealthCheckId": "health-check-id",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "primary-alb.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### Health Checks

```bash
# Create health check
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "api.example.com",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "EnableSNI": true
  }'

# Calculated health check (combines multiple)
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '{
    "Type": "CALCULATED",
    "HealthThreshold": 2,
    "ChildHealthChecks": ["hc-id-1", "hc-id-2", "hc-id-3"]
  }'
```

### Private Hosted Zones

```bash
# Create private hosted zone (internal DNS)
aws route53 create-hosted-zone \
  --name internal.example.com \
  --caller-reference "$(date +%s)" \
  --hosted-zone-config PrivateZone=true \
  --vpc VPCRegion=us-east-1,VPCId=vpc-12345678

# Associate with additional VPCs
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890 \
  --vpc VPCRegion=us-east-1,VPCId=vpc-87654321
```

---

## AWS VPN — Site-to-Site

Encrypted IPSec tunnel between on-premises and AWS VPC over the internet.

```
On-Premises Network ←→ [Internet] ←→ Virtual Private Gateway ←→ VPC
                         IPSec tunnel
```

### Setup

```bash
# Create Customer Gateway (your on-prem router)
CGW_ID=$(aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.1 \
  --bgp-asn 65000 \
  --query 'CustomerGateway.CustomerGatewayId' --output text)

# Create Virtual Private Gateway
VGW_ID=$(aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --query 'VpnGateway.VpnGatewayId' --output text)

# Attach to VPC
aws ec2 attach-vpn-gateway \
  --vpn-gateway-id $VGW_ID \
  --vpc-id $VPC_ID

# Create VPN connection
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id $CGW_ID \
  --vpn-gateway-id $VGW_ID \
  --options StaticRoutesOnly=false

# Enable route propagation
aws ec2 enable-vgw-route-propagation \
  --route-table-id rtb-private-aaa \
  --gateway-id $VGW_ID
```

**Specs**: Up to 1.25 Gbps per tunnel, 2 tunnels per connection (HA). Cost: $0.05/hr + data transfer.

---

## AWS Direct Connect

Dedicated private network connection from on-premises to AWS. Bypasses the internet.

```
On-Premises ←→ [Dedicated Fiber] ←→ Direct Connect Location ←→ AWS Region
                                      (colocation facility)
```

### Connection Types

| Type | Speed | Setup Time | Use Case |
|------|-------|-----------|---------|
| Dedicated | 1, 10, 100 Gbps | Weeks | Large enterprises |
| Hosted | 50Mbps–10Gbps | Days | Smaller needs, faster setup |

### Direct Connect vs VPN

| Feature | Direct Connect | Site-to-Site VPN |
|---------|---------------|-----------------|
| Bandwidth | Up to 100 Gbps | Up to 1.25 Gbps |
| Latency | Consistent, low | Variable (internet) |
| Encryption | Not by default | IPSec encrypted |
| Cost | High ($0.30/hr + port) | Low ($0.05/hr) |
| Setup time | Weeks | Hours |
| Reliability | High (SLA) | Internet-dependent |

**Best practice**: Use Direct Connect + VPN as backup for critical workloads.

### Virtual Interfaces (VIFs)

```
Private VIF → Connect to VPC via VGW or Direct Connect Gateway
Public VIF  → Connect to AWS public services (S3, DynamoDB)
Transit VIF → Connect to Transit Gateway (multiple VPCs)
```

---

## Transit Gateway

Hub-and-spoke network topology for connecting multiple VPCs and on-premises networks.

```
                    Transit Gateway
                   /       |        \
              VPC-A      VPC-B      VPC-C
                              |
                         On-Premises (VPN/DX)
```

```bash
# Create Transit Gateway
TGW_ID=$(aws ec2 create-transit-gateway \
  --description "Central hub" \
  --options '{
    "AmazonSideAsn": 64512,
    "AutoAcceptSharedAttachments": "disable",
    "DefaultRouteTableAssociation": "enable",
    "DefaultRouteTablePropagation": "enable",
    "VpnEcmpSupport": "enable",
    "DnsSupport": "enable"
  }' \
  --query 'TransitGateway.TransitGatewayId' --output text)

# Attach VPC
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id $TGW_ID \
  --vpc-id vpc-aaa \
  --subnet-ids subnet-private-aaa subnet-private-bbb

# Add route in VPC route table
aws ec2 create-route \
  --route-table-id rtb-private-aaa \
  --destination-cidr-block 10.0.0.0/8 \
  --transit-gateway-id $TGW_ID
```

---

## Interview Q&A

### Q1: What is the difference between Route 53 Alias and CNAME records?
**CNAME**: Standard DNS, cannot be used at zone apex (example.com), charges for queries, points to another hostname.
**Alias**: AWS-specific, works at zone apex, free queries for AWS resources, automatically resolves to current IP of AWS resource (ALB, CloudFront, S3). Always use Alias for AWS resources.

### Q2: How does Route 53 failover routing work?
Configure primary and secondary records with health checks. Route 53 monitors the primary endpoint. If health check fails (3 consecutive failures by default), Route 53 automatically routes traffic to the secondary. Recovery is automatic when primary becomes healthy again. Use for active-passive disaster recovery.

### Q3: What is the difference between Direct Connect and VPN?
**VPN**: Encrypted IPSec over internet. Quick setup (hours), low cost ($0.05/hr), up to 1.25 Gbps, variable latency. Good for: dev/test, backup connectivity, smaller bandwidth needs.
**Direct Connect**: Dedicated private fiber. Weeks to set up, higher cost, up to 100 Gbps, consistent low latency. Good for: production workloads, large data transfers, compliance requirements, latency-sensitive applications.

### Q4: What is Transit Gateway and when would you use it over VPC Peering?
Transit Gateway is a hub-and-spoke network hub. Use when: connecting more than 3-4 VPCs (peering doesn't scale), need transitive routing, connecting VPCs + on-premises, need centralized network monitoring. VPC Peering is simpler and cheaper for 2-3 VPCs with no transitive routing needs.

### Q5: How do you implement DNS for a multi-VPC architecture?
Use Route 53 Resolver: (1) Private hosted zones associated with multiple VPCs for internal service discovery, (2) Resolver inbound endpoints for on-premises DNS queries to resolve AWS names, (3) Resolver outbound endpoints for EC2 instances to query on-premises DNS, (4) Resolver rules to forward specific domains to on-premises DNS servers.
