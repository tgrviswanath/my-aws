# Cost Estimate — Project 5.6 AWS App Runner

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| App Runner (active) | 0.25 vCPU × 730 hrs | ~$18 |
| App Runner (memory) | 0.5 GB × 730 hrs | ~$4 |
| App Runner (requests) | 10K requests | ~$0.01 |
| **Total** | | **~$22/month** |

## Notes
- App Runner charges for provisioned compute even when idle (unlike Lambda)
- Pause the service when not using: `aws apprunner pause-service --service-arn ARN`
- Paused services cost ~$0 but resume in seconds
- Destroy after learning: `terraform destroy`
