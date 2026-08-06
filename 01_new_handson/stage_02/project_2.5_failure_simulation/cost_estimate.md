# Cost Estimate — Project 2.5: AWS Failure Simulation and Chaos Engineering

## Architecture Summary
Multi-AZ EC2 setup (2 instances in different AZs) behind ALB + RDS Multi-AZ instance + AWS FIS experiments. Chaos testing involves terminating instances, forcing RDS failover, and running FIS experiment templates.

---

## ⚠️ Free Tier Status

| Service | Free Tier? | Notes |
|---|---|---|
| AWS FIS (Fault Injection Simulator) | ❌ **No free tier** | Charged per action-minute |
| EC2 t2.micro | ✅ 750 hours/month (first 12 months) | Free for lab instances |
| RDS db.t3.micro | ✅ 750 hours/month (first 12 months) | Free tier for Multi-AZ? ❌ No — Multi-AZ doubles cost |
| ALB (from project 2.3) | ❌ No free tier | $0.0225/hr |
| CloudWatch basic metrics | ✅ Free | EC2/RDS/ALB default metrics |

---

## AWS FIS Pricing

| Metric | Rate |
|---|---|
| FIS charge unit | Per action-minute |
| Cost per action-minute | **$0.10 per action-minute** |
| Minimum charge per experiment | 1 action-minute |

### What is an "action-minute"?
```
action-minutes = (number of actions in experiment) × (duration in minutes, rounded up to nearest minute)

Example: 1 action (terminate instances), runs for 30 seconds
= 1 action × 1 minute (rounds up) = 1 action-minute = $0.10

Example: 3 actions running for 5 minutes
= 3 actions × 5 minutes = 15 action-minutes = $1.50
```

---

## Lab Session Cost Breakdown

### Scenario A: Manual Failure Simulation Only (No FIS)
| Component | Duration | Cost |
|---|---|---|
| EC2 t2.micro × 2 | 4 hours | $0.00 (Free Tier) |
| ALB (from project 2.3) | 4 hours | $0.09 |
| RDS db.t3.micro (Single-AZ) | 4 hours | $0.00 (Free Tier) |
| Replacement EC2 launch | 1 instance × 1 hour | $0.00 (Free Tier) |
| **Total — Manual only** | | **~$0.09** |

### Scenario B: FIS Experiments Included

| Component | Quantity/Duration | Cost |
|---|---|---|
| FIS experiment 1 (EC2 terminate) | 1 action × 1 min | $0.10 |
| FIS experiment 2 (re-run) | 1 action × 1 min | $0.10 |
| FIS experiment 3 (RDS failover action) | 1 action × 1 min | $0.10 |
| EC2 instances × 2 | 4 hours (Free Tier) | $0.00 |
| ALB | 4 hours | $0.09 |
| RDS Multi-AZ db.t3.micro | 4 hours | $0.08 (note below) |
| EC2 replacement instance | Free Tier | $0.00 |
| **Total — With FIS** | | **~$0.47** |

> 💡 **Bottom line:** A complete chaos engineering lab session with FIS costs less than $0.50.

---

## RDS Multi-AZ Cost Note

| RDS Configuration | Hourly Rate (db.t3.micro) | Monthly Rate |
|---|---|---|
| Single-AZ (Free Tier covered) | $0.017/hr | ~$12 |
| Single-AZ (Free Tier: 750h/month) | $0.00 | $0.00 |
| ✅ Multi-AZ (2× hourly rate) | $0.034/hr | ~$25 |
| Multi-AZ (Free Tier applies?) | Free Tier **does NOT cover Multi-AZ** | $0.034/hr |

> ⚠️ **RDS Multi-AZ is NOT covered by Free Tier.** Single-AZ db.t3.micro for 750 hours is free. The moment you enable Multi-AZ, the instance is billed at double the Single-AZ rate from the first hour.
>
> **For this lab:** Enable Multi-AZ only for the duration of the experiment (enable → run experiment → disable Multi-AZ → save ~$0.02/hr).

### RDS Multi-AZ Modification to Save Cost
```bash
# Enable Multi-AZ just before the experiment
aws rds modify-db-instance \
  --db-instance-identifier myapp-db \
  --multi-az \
  --apply-immediately

# Wait for modification to complete (~5-10 minutes)
aws rds wait db-instance-available --db-instance-identifier myapp-db

# [RUN YOUR EXPERIMENT]

# Disable Multi-AZ after experiment to return to Free Tier
aws rds modify-db-instance \
  --db-instance-identifier myapp-db \
  --no-multi-az \
  --apply-immediately
```

---

## Cost Per Experiment Type

| Experiment | FIS Cost | EC2 Cost | Total |
|---|---|---|---|
| Terminate 1 EC2 + observe ALB | $0.10 | Free Tier | **$0.10** |
| Terminate 1 EC2 + force RDS failover (2 actions) | $0.20 | Free Tier | **$0.20** |
| 5-action GameDay experiment (5 min) | $2.50 | Free Tier | **~$2.50** |
| Full chaos exercise (10 actions, 10 min each) | $10.00 | Variable | **~$10+** |

---

## Cleanup Commands

### Delete FIS Experiment Templates

```bash
# List all FIS templates
aws fis list-experiment-templates \
  --query "experimentTemplates[].{ID:id,Description:description}" \
  --output table

# Delete specific template (replace TEMPLATE_ID)
TEMPLATE_ID="EXT12345xxxxxxxxx"
aws fis delete-experiment-template --id ${TEMPLATE_ID}
echo "FIS template deleted"

# Delete all lab templates in a loop
aws fis list-experiment-templates \
  --query "experimentTemplates[?contains(description, 'chaos lab 2.5')].id" \
  --output text | \
  xargs -I{} aws fis delete-experiment-template --id {}
echo "All lab FIS templates deleted"
```

### Delete FIS IAM Role

```bash
# Detach policies from FIS role
aws iam detach-role-policy \
  --role-name FISRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess 2>/dev/null

aws iam detach-role-policy \
  --role-name FISRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonRDSFullAccess 2>/dev/null

# Delete inline policies
aws iam list-role-policies --role-name FISRole --output text | \
  xargs -I{} aws iam delete-role-policy --role-name FISRole --policy-name {}

# Delete the role
aws iam delete-role --role-name FISRole
echo "FIS IAM role deleted"
```

### Restore EC2 Environment (if terminated during experiment)

```bash
# Launch replacement EC2 in us-east-1b
SUBNET_1B="subnet-yyyyyyyy"   # Your us-east-1b subnet ID
SG_ID="sg-xxxxxxxx"
KEY_PAIR="your-key-pair"
TG_ARN="arn:aws:elasticloadbalancing:us-east-1:ACCT:targetgroup/web-tg/xxxx"

NEW_INSTANCE=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t2.micro \
  --key-name ${KEY_PAIR} \
  --subnet-id ${SUBNET_1B} \
  --security-group-ids ${SG_ID} \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server-1b},{Key=Environment,Value=lab}]' \
  --query "Instances[0].InstanceId" --output text)

echo "New instance: ${NEW_INSTANCE}"

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids ${NEW_INSTANCE}

# Register in target group
aws elbv2 register-targets \
  --target-group-arn ${TG_ARN} \
  --targets Id=${NEW_INSTANCE},Port=80

echo "Environment restored"
```

### Disable RDS Multi-AZ (Return to Free Tier)

```bash
aws rds modify-db-instance \
  --db-instance-identifier myapp-db \
  --no-multi-az \
  --apply-immediately

aws rds wait db-instance-available --db-instance-identifier myapp-db
echo "RDS Multi-AZ disabled — back to Free Tier single-AZ billing"
```

---

## Cost Summary

| Cost Driver | Rate | Per Lab Session (4h) |
|---|---|---|
| AWS FIS (experiments) | $0.10/action-minute | **$0.30–$0.50** |
| EC2 instances × 2 | Free Tier | **$0.00** |
| RDS Multi-AZ db.t3.micro | $0.034/hr | **$0.14** |
| ALB | $0.0225/hr | **$0.09** |
| CloudWatch | Free basic | **$0.00** |
| **Total per lab session** | | **~$0.50–$1.00** |
| **Total if left running 24h** | | **~$2–4** |

> FIS has no free tier — even a single-action experiment costs $0.10. For a full learning session running 5–10 experiments, budget $0.50–$2.00 total.

---

*Region: us-east-1 | Prices as of 2024 — verify at https://aws.amazon.com/fis/pricing/ and https://aws.amazon.com/rds/pricing/*
