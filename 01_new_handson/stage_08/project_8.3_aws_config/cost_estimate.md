# Cost Estimate — Project 8.3: AWS Config

## Pricing Model (us-east-1, as of 2024)

| Resource | Unit Price | Notes |
|----------|-----------|-------|
| Configuration items recorded | $0.003 / item | Each resource change recorded |
| Custom rule evaluations | $0.001 / evaluation | Per evaluation triggered |
| Conformance pack evaluations | $0.001 / evaluation | Per pack per rule evaluation |
| Config snapshots to S3 | Free (S3 charges apply) | Storage at S3 rates |

---

## Free Tier

- First **30 days free** for configuration items per resource type (for some services)
- AWS Config **proactive** evaluations (new feature): First 1,000 evaluations/month free
- S3 Standard storage: First 5 GB/month free (12 months)

**No free tier for ongoing Config recording after trial period.**

---

## Estimated Configuration Items Per Month

A typical AWS account with moderate resources generates:

| Resource Type | Estimated Resources | Changes/Day | Items/Month |
|--------------|--------------------|-----------:|----------:|
| EC2 Instances | 20 | 2 | 1,200 |
| Security Groups | 30 | 1 | 900 |
| S3 Buckets | 15 | 0.5 | 225 |
| IAM Roles | 50 | 0.5 | 750 |
| RDS Instances | 5 | 0.5 | 75 |
| EBS Volumes | 40 | 1 | 1,200 |
| VPC Resources | 20 | 0.2 | 120 |
| **Total** | | | **~4,470/month** |

---

## Scenario Estimates

### Small Account (minimal recording)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Configuration items (selective) | 1,000 | $3.00 |
| Config rule evaluations (5 rules) | 5,000 | $5.00 |
| S3 storage (10 MB/month) | 10 MB | $0.00 |
| **Total** | | **~$8/month** |

### Medium Account (all resources, CIS pack)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Configuration items | 5,000 | $15.00 |
| Custom rule evaluations | 10,000 | $10.00 |
| Conformance pack evaluations (30 rules × 200 resources) | 6,000 | $6.00 |
| S3 storage (100 MB) | 100 MB | $0.02 |
| **Total** | | **~$31/month** |

### Large Account (enterprise, multi-region)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| Configuration items (5 regions) | 50,000 | $150.00 |
| Rule evaluations | 100,000 | $100.00 |
| Conformance pack evaluations | 50,000 | $50.00 |
| Config aggregator | included | $0.00 |
| **Total** | | **~$300/month** |

---

## Cost Optimization Tips

1. **Record specific resource types only** — exclude rarely-changed resources
2. **Increase evaluation frequency** only for critical rules
3. **Use periodic evaluations** instead of change-triggered for stable resources
4. **Clean up old snapshots** in S3 using lifecycle policies

```bash
# Selective recording to reduce cost
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "recordingGroup": {
      "allSupported": false,
      "resourceTypes": [
        "AWS::EC2::Instance",
        "AWS::EC2::SecurityGroup",
        "AWS::S3::Bucket",
        "AWS::IAM::Role",
        "AWS::RDS::DBInstance"
      ]
    }
  }'
```

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Small (learning/dev) | ~$8 | ~$96 |
| Medium (production) | ~$31 | ~$372 |
| Large (enterprise) | ~$300 | ~$3,600 |

**For this learning project:** ~$5-15/month (short-term use, limited resources)

---

## Cleanup

```bash
# 1. Stop the recorder immediately (stops per-item charges)
aws configservice stop-configuration-recorder \
  --configuration-recorder-name default

# 2. Delete conformance pack
aws configservice delete-conformance-pack \
  --conformance-pack-name "CIS-Level1-Benchmark"

# 3. Delete all Config rules
for RULE in $(aws configservice describe-config-rules \
  --query 'ConfigRules[].ConfigRuleName' --output text); do
  aws configservice delete-config-rule --config-rule-name "$RULE"
  echo "Deleted rule: $RULE"
done

# 4. Delete delivery channel (must stop recorder first)
aws configservice delete-delivery-channel \
  --delivery-channel-name default

# 5. Delete recorder
aws configservice delete-configuration-recorder \
  --configuration-recorder-name default

# 6. Empty and delete S3 bucket
CONFIG_BUCKET="aws-config-delivery-$(aws sts get-caller-identity --query Account --output text)"
aws s3 rm s3://${CONFIG_BUCKET} --recursive
aws s3 rb s3://${CONFIG_BUCKET}

echo "Config cleanup complete — charges stop immediately after recorder is stopped"
```

**Important:** Charges stop as soon as the recorder is stopped, not when the full cleanup completes.
