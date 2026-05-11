# Cost Estimate — Project 2.5 Failure Simulation Lab

| Resource | Monthly Cost |
|----------|-------------|
| VPC Flow Logs (CloudWatch) | ~$0.50 (minimal data) |
| CloudWatch Logs storage | ~$0.03/GB |
| Systems Manager Session Manager | $0 |
| CloudTrail (management events) | $0 (first trail free) |
| EC2/RDS/ALB (from Project 2.2) | Already running |
| **Total (additional)** | **~$0.50–1.00** |

## Notes
- This lab uses existing infrastructure from Projects 2.1 and 2.2
- VPC Flow Logs are the only new cost — worth it for the learning
- Disable Flow Logs after completing the lab to stop charges
- Systems Manager Session Manager is free — use it instead of SSH bastion hosts
