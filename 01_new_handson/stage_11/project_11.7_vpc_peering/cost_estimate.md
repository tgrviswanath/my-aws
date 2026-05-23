# Cost Estimate — Project 11.7 VPC Peering

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| VPC x2 | 2 | $0 |
| VPC Peering Connection | 1 | $0 |
| Data transfer (same region) | ~1 MB | ~$0.01 |
| EC2 t3.micro x2 | ~2 hrs | ~$0.04 |
| **Total** | | **~$0.05** |

## Notes
VPC Peering itself is free. You only pay for data transfer across the peering connection.
Same-region: $0.01/GB. Cross-region: varies by region pair (~$0.02–0.09/GB).
