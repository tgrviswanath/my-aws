# Architecture Notes — Project 11.10

## Traffic Path
```
EC2-East (10.0.1.x)
    → Route table: 10.1.0.0/16 → pcx-xxx
    → AWS backbone (inter-region)
    → Route table in West: 10.0.0.0/16 → pcx-xxx
    → EC2-West (10.1.1.x)
```

## Latency Expectations
| Region Pair | Typical RTT |
|-------------|-------------|
| us-east-1 ↔ us-west-2 | 60-80ms |
| us-east-1 ↔ eu-west-1 | 80-100ms |
| us-east-1 ↔ ap-southeast-1 | 200-250ms |

## When to Use Inter-Region Peering
- Private connectivity between regions for internal services
- Disaster recovery replication
- Multi-region active-active architectures

## Alternatives
- AWS Global Accelerator: better for end-user latency
- CloudFront: for content delivery
- Transit Gateway + inter-region peering: for complex multi-region topologies
