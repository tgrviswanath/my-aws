# Architecture Notes — Project 11.12

## Two Tunnels for HA
AWS always creates 2 IPSec tunnels per VPN connection.
Each tunnel terminates on a different AWS endpoint in different AZs.
Configure both tunnels in strongSwan for full redundancy.

## Traffic Flow
```
On-Prem EC2 (192.168.1.x)
    → strongSwan (IPSec encrypt)
    → Internet → AWS VPN endpoint (Tunnel 1 or 2)
    → VGW → VPC route table
    → AWS Private EC2 (10.0.1.x)
```

## Static vs BGP Routing
| | Static | BGP |
|--|--|--|
| Setup | Simple | Complex |
| Auto-failover | No | Yes |
| Route updates | Manual | Automatic |
| Use case | Learning, simple | Production |

## DPD (Dead Peer Detection)
AWS uses DPD to detect tunnel failures.
Configure `dpddelay=10s dpdtimeout=30s dpdaction=restart` in strongSwan
to ensure automatic tunnel re-establishment.
