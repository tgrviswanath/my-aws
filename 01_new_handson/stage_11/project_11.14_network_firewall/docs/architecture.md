# Architecture Notes — Project 11.14

## Traffic Flow (Ingress + Egress)
```
Egress (private EC2 → internet):
  Private EC2 → private-rt (0.0.0.0/0 → firewall endpoint)
             → Firewall (inspect) → firewall-rt (0.0.0.0/0 → igw)
             → IGW → Internet

Ingress (internet → private EC2):
  Internet → IGW → igw-rt (10.0.3.0/24 → firewall endpoint)
           → Firewall (inspect) → private subnet → EC2
```

## Route Table Summary
| Route Table | Attached To | Key Route |
|-------------|-------------|-----------|
| igw-rt | IGW (edge association) | 10.0.3.0/24 → vpce-xxx |
| firewall-rt | Firewall subnet | 0.0.0.0/0 → igw |
| private-rt | Private subnet | 0.0.0.0/0 → vpce-xxx |

## Rule Evaluation Order
1. Stateless rules (fast, no state) — match → forward to stateful or drop/pass
2. Stateful rules (connection-aware) — domain lists, Suricata IDS rules
3. Default action — drop everything not explicitly allowed
