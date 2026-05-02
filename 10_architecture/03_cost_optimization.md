# Cost Optimization on AWS — FinOps Basics

## AWS Cost Optimization Pillars

```
1. Right-sizing        → Use the right resource size
2. Pricing models      → Reserved, Savings Plans, Spot
3. Storage tiering     → Move data to cheaper tiers
4. Eliminate waste     → Delete unused resources
5. Architecture        → Serverless, managed services
6. Monitoring          → Visibility into spending
```

---

## Cost Visibility Tools

### AWS Cost Explorer

```bash
# Monthly cost by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost UnblendedCost UsageQuantity \
  --group-by Type=DIMENSION,Key=SERVICE

# Cost by tag (requires tag cost allocation)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Environment

# Forecast next month
aws ce get-cost-forecast \
  --time-period Start=2024-02-01,End=2024-03-01 \
  --granularity MONTHLY \
  --metric BLENDED_COST
```

### AWS Budgets

```bash
# Create monthly budget with alert
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "monthly-production",
    "BudgetLimit": {"Amount": "5000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKeyValue": ["user:Environment$production"]
    }
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "EMAIL",
        "Address": "team@company.com"
      }]
    },
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-east-1:123456789:cost-alerts"
      }]
    }
  ]'
```

---

## EC2 Cost Optimization

### Pricing Model Selection

```
Workload Type                    → Recommended Pricing
─────────────────────────────────────────────────────
Steady-state production          → Reserved (1yr) or Savings Plans
Variable but predictable         → Savings Plans
Dev/test (off nights/weekends)   → Scheduled Reserved or On-Demand
Batch, fault-tolerant            → Spot Instances
Short-lived, unpredictable       → On-Demand
```

### Spot Instances Best Practices

```bash
# Use Spot with Auto Scaling (capacity-optimized strategy)
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name spot-asg \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {
        "LaunchTemplateName": "web-lt",
        "Version": "$Latest"
      },
      "Overrides": [
        {"InstanceType": "m5.large"},
        {"InstanceType": "m5a.large"},
        {"InstanceType": "m4.large"},
        {"InstanceType": "m5d.large"}
      ]
    },
    "InstancesDistribution": {
      "OnDemandBaseCapacity": 2,
      "OnDemandPercentageAboveBaseCapacity": 20,
      "SpotAllocationStrategy": "capacity-optimized"
    }
  }' \
  --min-size 2 --max-size 20 --desired-capacity 6

# Handle Spot interruption (2-min warning)
# In your application, listen for interruption notice:
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/spot/interruption-action
```

### Right-Sizing with Compute Optimizer

```bash
# Get EC2 recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --account-ids 123456789012 \
  --filters Name=Finding,Values=OVER_PROVISIONED

# Get Lambda recommendations
aws compute-optimizer get-lambda-function-recommendations \
  --account-ids 123456789012

# Get EBS recommendations
aws compute-optimizer get-ebs-volume-recommendations \
  --account-ids 123456789012
```

### Scheduled Scaling (Dev/Test)

```bash
# Scale down at night and weekends
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name dev-asg \
  --scheduled-action-name scale-down-night \
  --recurrence "0 20 * * MON-FRI" \
  --desired-capacity 0 --min-size 0

aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name dev-asg \
  --scheduled-action-name scale-up-morning \
  --recurrence "0 8 * * MON-FRI" \
  --desired-capacity 2 --min-size 1
```

---

## S3 Cost Optimization

```bash
# Enable Intelligent-Tiering for unknown access patterns
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket my-bucket \
  --id entire-bucket \
  --intelligent-tiering-configuration '{
    "Id": "entire-bucket",
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'

# Lifecycle policy to move old data
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "cost-optimization",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"},
        {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 2555},
      "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
    }]
  }'

# Analyze storage costs
aws s3api get-bucket-analytics-configuration \
  --bucket my-bucket \
  --id storage-analysis
```

---

## RDS Cost Optimization

```bash
# Use Aurora Serverless for variable workloads
# Scales to 0 when idle (dev/test)
aws rds create-db-cluster \
  --db-cluster-identifier dev-aurora \
  --engine aurora-postgresql \
  --serverless-v2-scaling-configuration MinCapacity=0,MaxCapacity=4

# Stop RDS instance (dev/test) — saves ~60% vs running
aws rds stop-db-instance --db-instance-identifier dev-mysql
# Note: AWS auto-starts after 7 days

# Use gp3 instead of gp2 (same performance, 20% cheaper)
aws rds modify-db-instance \
  --db-instance-identifier prod-mysql \
  --storage-type gp3 \
  --iops 3000 \
  --apply-immediately

# Reserved instances for production
aws rds purchase-reserved-db-instances-offering \
  --reserved-db-instances-offering-id <offering-id> \
  --reserved-db-instance-id prod-mysql-reserved \
  --db-instance-count 1
```

---

## Lambda Cost Optimization

```bash
# Use ARM/Graviton2 (20% cheaper, up to 34% better price-performance)
aws lambda update-function-configuration \
  --function-name my-function \
  --architectures arm64

# Right-size memory (use Lambda Power Tuning)
# https://github.com/alexcasalboni/aws-lambda-power-tuning

# Use provisioned concurrency only for latency-sensitive functions
# Remove it for batch/async functions

# Optimize code to reduce duration
# - Initialize SDK clients outside handler
# - Use connection pooling
# - Minimize cold start time
```

---

## NAT Gateway Cost Optimization

NAT Gateway is often a surprise cost: $0.045/hr + $0.045/GB processed.

```bash
# Use VPC Endpoints instead of NAT for AWS services (free for Gateway endpoints)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-private-aaa \
  --vpc-endpoint-type Gateway

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --route-table-ids rtb-private-aaa \
  --vpc-endpoint-type Gateway

# For Lambda in VPC: use VPC endpoints for all AWS services
# This eliminates NAT Gateway costs for Lambda → AWS service calls
```

---

## Cost Tagging Strategy

```bash
# Enforce tagging with SCP
# Required tags: Environment, Team, Project, CostCenter

# Tag all resources
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags \
    Key=Environment,Value=production \
    Key=Team,Value=platform \
    Key=Project,Value=web-app \
    Key=CostCenter,Value=engineering

# AWS Config rule to detect untagged resources
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "REQUIRED_TAGS"
    },
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Team\",\"tag3Key\":\"Project\"}"
  }'
```

---

## Cost Optimization Checklist

```
EC2:
□ Right-size instances (Compute Optimizer)
□ Use Reserved Instances or Savings Plans for steady workloads
□ Use Spot for batch/fault-tolerant workloads
□ Schedule dev/test instances to stop nights/weekends
□ Delete unattached EBS volumes and old snapshots
□ Release unused Elastic IPs

S3:
□ Enable Intelligent-Tiering or lifecycle policies
□ Delete incomplete multipart uploads
□ Enable S3 Analytics to understand access patterns
□ Use S3 Glacier for archives

Database:
□ Right-size RDS instances
□ Use Aurora Serverless for variable workloads
□ Stop dev/test RDS instances when not in use
□ Use gp3 instead of gp2
□ Delete unused RDS snapshots

Networking:
□ Use VPC Endpoints for S3/DynamoDB (eliminate NAT costs)
□ Use CloudFront to reduce data transfer costs
□ Review NAT Gateway data processing costs

Lambda:
□ Use ARM/Graviton2 architecture
□ Right-size memory
□ Optimize code to reduce duration

General:
□ Enable Cost Explorer and set up budgets
□ Tag all resources for cost allocation
□ Review Trusted Advisor cost recommendations
□ Use AWS Cost Anomaly Detection
```

---

## Interview Q&A

### Q1: How would you reduce AWS costs by 30% for a production workload?
1. Purchase Reserved Instances or Savings Plans for EC2 and RDS (40-72% savings)
2. Right-size over-provisioned instances using Compute Optimizer
3. Use Spot Instances for non-critical workloads (up to 90% savings)
4. Implement S3 lifecycle policies to move old data to cheaper tiers
5. Add VPC Endpoints for S3/DynamoDB to eliminate NAT Gateway costs
6. Schedule dev/test environments to stop nights and weekends
7. Delete unused resources (unattached EBS, old snapshots, idle load balancers)

### Q2: What is the difference between Reserved Instances and Savings Plans?
**Reserved Instances**: Commit to specific instance type, region, OS, tenancy. Up to 72% savings. Less flexible — changing instance type requires selling on marketplace.
**Savings Plans**: Commit to $/hour spend. Applies automatically to any EC2 instance family, region, OS. More flexible. Up to 66% savings. Compute Savings Plans apply to Lambda and Fargate too. Prefer Savings Plans for flexibility.

### Q3: How do you identify and eliminate AWS waste?
1. AWS Trusted Advisor: Low utilization EC2, idle load balancers, unassociated EIPs
2. Compute Optimizer: Over-provisioned EC2, Lambda, EBS
3. Cost Explorer: Identify services with unexpected growth
4. AWS Config: Find untagged resources, non-compliant configurations
5. CloudWatch: Find EC2 instances with <5% CPU for 2 weeks
6. S3 Storage Lens: Identify buckets with no access
7. Manual review: Unused RDS instances, old snapshots, orphaned EBS volumes

### Q4: What is AWS Cost Anomaly Detection?
Cost Anomaly Detection uses ML to identify unusual spending patterns. It learns your normal spending baseline and alerts when costs deviate significantly. Set up monitors by service, account, or cost category. Sends alerts via SNS when anomalies are detected. Helps catch runaway costs early (e.g., someone accidentally left a large EC2 instance running, or a DDoS attack causing data transfer costs).

### Q5: How do you implement FinOps in an organization?
1. **Visibility**: Enable Cost Explorer, set up cost allocation tags, create dashboards per team/project
2. **Accountability**: Chargeback/showback — teams see their own costs
3. **Optimization**: Regular reviews, Trusted Advisor, Compute Optimizer
4. **Governance**: Budgets with alerts, SCPs to prevent expensive resources in dev
5. **Culture**: Engineers understand cost implications of their architecture decisions
6. **Automation**: Auto-stop dev resources, auto-delete old snapshots, rightsizing automation
