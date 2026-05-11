# Steps — Project 10.3 Cost Optimization Automation

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -var="alert_email=your@email.com" -auto-approve
```

---

## Phase 2 — Run Cost Optimizer (Dry Run)

```bash
pip install boto3

# Dry run — report only, no changes
python3 src/cost_optimizer.py

# Apply changes (stops idle EC2, etc.)
python3 src/cost_optimizer.py --apply
```

---

## Phase 3 — Enable Compute Optimizer

```bash
# Enable Compute Optimizer (free)
aws compute-optimizer update-enrollment-status --status Active

# Wait 24-48 hours for recommendations
# Then get EC2 recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --query "instanceRecommendations[*].{Instance:instanceArn,Finding:finding,Recommendation:recommendationOptions[0].instanceType}" \
  --output table
```

---

## Phase 4 — Set Up S3 Intelligent-Tiering

```bash
# Enable Intelligent-Tiering on data lake bucket
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket your-data-lake-bucket \
  --id "EntireBucket" \
  --intelligent-tiering-configuration '{
    "Id": "EntireBucket",
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'
```

---

## Phase 5 — Review Cost Explorer

```
1. AWS Console → Cost Explorer → Enable
2. View: Cost by service (last 30 days)
3. View: Cost by tag (Project, Environment)
4. Identify: top 3 cost drivers
5. Set up: Savings Plans recommendations
```

---

## Screenshots to Take
- [ ] Cost optimizer report showing idle resources
- [ ] Compute Optimizer recommendations
- [ ] Cost anomaly detection configured
- [ ] S3 Intelligent-Tiering enabled
- [ ] Cost Explorer showing cost by tag
- [ ] Lambda running daily (CloudWatch logs)
