# Architecture Notes — Project 11.13

## BGP Session Inside the Tunnel
```
EC2 (Bird BGP, ASN 65000)
    ↕ IPSec tunnel (encrypted)
AWS VGW (ASN 64512)
    ↕ BGP session (inside tunnel, using tunnel inside IPs)
    AWS advertises: 10.0.0.0/16
    EC2 advertises: 192.168.0.0/16
```

## Direct Connect vs VPN+BGP Simulation
| | Direct Connect | VPN + BGP (this project) |
|--|--|--|
| Physical path | Dedicated fiber | Internet |
| Latency | Consistent, low | Variable |
| Bandwidth | Up to 100 Gbps | Up to 1.25 Gbps |
| Routing | BGP | BGP (same protocol) |
| Cost | High | Low |
| Learning value | Same BGP concepts | ✅ |

## Direct Connect Gateway
Allows one DX connection to reach multiple VPCs across regions.
Concept: DX → DX Gateway → VGW (in each VPC)
Same as TGW but for Direct Connect.
