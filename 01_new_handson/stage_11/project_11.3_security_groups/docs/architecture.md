# Architecture Notes — Project 11.3

## SG Chain
```
Internet → alb-sg (80/443 open)
               ↓
           web-sg (80 from alb-sg only)
               ↓
           app-sg (8080 from web-sg only)
               ↓
           db-sg  (3306 from app-sg only)
```

## Stateful Behavior
SGs are stateful. If you allow inbound TCP 80, the response packets are
automatically allowed outbound — you don't need an explicit outbound rule for port 80.

## SG vs NACL
| | Security Group | NACL |
|--|--|--|
| Level | Instance | Subnet |
| Stateful | Yes | No |
| Rules | Allow only | Allow + Deny |
| Evaluation | All rules | In order (numbered) |
