# Cost Estimate — Project 8.4: GuardDuty + Security Hub

## GuardDuty Pricing (after 30-day free trial)

| Data Source | Pricing Tier | Unit |
|------------|-------------|------|
| CloudTrail Management Events | $4.00/million events | Per event analyzed |
| CloudTrail S3 Data Events | $0.80/million events | Per event analyzed |
| VPC Flow Logs | $1.00/GB | First 500 GB/month |
| VPC Flow Logs | $0.50/GB | 500 GB – 2 TB/month |
| DNS Logs | $1.00/GB | First 500 GB/month |
| S3 Protection | Included | No extra charge (as of 2023) |

## Security Hub Pricing (after 30-day free trial)

| Resource | Price | Notes |
|----------|-------|-------|
| Security findings | $0.0010/finding | Per finding ingested |
| Compliance checks | $0.0010/check | Per control evaluation |

---

## Free Tier

- **GuardDuty**: 30-day free trial (full functionality, no limits)
- **Security Hub**: 30-day free trial
- After trial: per-usage pricing as above

---

## Scenario Estimates (Post-Trial)

### Small Account (low API activity)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| GuardDuty — CloudTrail events | 500K/month | $2.00 |
| GuardDuty — VPC Flow Logs | 5 GB/month | $5.00 |
| GuardDuty — DNS | 2 GB/month | $2.00 |
| Security Hub — findings | 1,000/month | $1.00 |
| Security Hub — compliance checks | 5,000/month | $5.00 |
| **Total** | | **~$15/month** |

### Medium Account (moderate activity)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| GuardDuty — CloudTrail events | 5M/month | $20.00 |
| GuardDuty — VPC Flow Logs | 50 GB/month | $50.00 |
| GuardDuty — DNS | 20 GB/month | $20.00 |
| Security Hub — findings | 10,000/month | $10.00 |
| Security Hub — compliance checks | 50,000/month | $50.00 |
| **Total** | | **~$150/month** |

### Large Account (high traffic, multi-region)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| GuardDuty (all sources, 4 regions) | — | ~$500 |
| Security Hub (4 regions) | — | ~$200 |
| **Total** | | **~$700/month** |

---

## Cost Comparison: GuardDuty vs Alternatives

| Option | Monthly Cost | Coverage |
|--------|-------------|---------|
| GuardDuty alone | ~$15-150 | Threat detection |
| GuardDuty + Security Hub | ~$20-165 | Threat + compliance |
| Third-party SIEM (Splunk) | $500+ | Full SIEM |
| ManageD security service | $2,000+ | Full SOC |

**GuardDuty is very cost-effective** for managed threat detection.

---

## Total

| Phase | Duration | Cost |
|-------|---------|------|
| Free trial | 30 days | $0.00 |
| Post-trial, small account | Per month | ~$15-20 |
| Post-trial, medium account | Per month | ~$150 |

**Recommendation:** Enable during free trial, evaluate findings, decide if justified.

---

## Cleanup

```bash
# Get detector ID
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# Delete GuardDuty detector (stops all analysis and charges)
aws guardduty delete-detector --detector-id $DETECTOR_ID

# Disable Security Hub (stops finding ingestion and check charges)
aws securityhub disable-security-hub

# Remove EventBridge rule
aws events remove-targets --rule "guardduty-high-severity-response" --ids "1"
aws events delete-rule --name "guardduty-high-severity-response"

# Delete Lambda
aws lambda delete-function --function-name guardduty-auto-remediate

# Delete SNS
SNS_ARN=$(aws sns list-topics --query 'Topics[?contains(TopicArn,`guardduty`)].TopicArn' --output text)
aws sns delete-topic --topic-arn $SNS_ARN

# Verify GuardDuty disabled
aws guardduty list-detectors --query 'DetectorIds'
# Should return empty list

echo "Charges stop within 1 hour of disabling both services"
```

**Note:** Disabling GuardDuty deletes all findings permanently. Export findings to S3 first if you need to retain them.

```bash
# Export findings to S3 before disabling (optional)
aws guardduty list-findings --detector-id $DETECTOR_ID \
  --query 'FindingIds[]' --output text | tr '\t' '\n' | \
  xargs -I{} aws guardduty get-findings --detector-id $DETECTOR_ID --finding-ids {} \
  >> /tmp/guardduty-findings-export.json
```
