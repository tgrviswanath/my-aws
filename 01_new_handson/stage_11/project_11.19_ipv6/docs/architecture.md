# Architecture Notes — Project 11.19

## IPv4 vs IPv6 in AWS VPC
```
IPv4:                              IPv6:
Private: 10.0.0.0/16              Global unicast: 2600::/56
NAT Gateway for private outbound   Egress-Only IGW for private outbound
Elastic IP for public static       No static IPv6 (changes on stop/start)
$0.005/hr per public IPv4          FREE
```

## Egress-Only IGW vs NAT Gateway
```
NAT Gateway (IPv4):                Egress-Only IGW (IPv6):
Private EC2 → NAT → IGW → Internet  Private EC2 → EIGW → Internet
Inbound: BLOCKED                     Inbound: BLOCKED
Cost: ~$32/month                     Cost: FREE
```

## IPv6 Address Types
| Type | Range | Scope |
|------|-------|-------|
| Global unicast | 2000::/3 | Internet-routable |
| Link-local | fe80::/10 | Same link only |
| Loopback | ::1/128 | Local only |
| Multicast | ff00::/8 | Group communication |

## cidrsubnet() in Terraform
```hcl
# VPC gets /56 from AWS, e.g. 2600:1f18:xxxx:xx00::/56
# cidrsubnet(vpc_ipv6_cidr, 8, 0) → first /64:  2600:1f18:xxxx:xx00::/64
# cidrsubnet(vpc_ipv6_cidr, 8, 1) → second /64: 2600:1f18:xxxx:xx01::/64
```
