# Project 10.3 — AWS Cost Optimization
## Trusted Advisor, Compute Optimizer, Spot Instances, Savings Plans, Auto-Stop Idle EC2

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `ce:*`, `compute-optimizer:*`, `ec2:*`, `lambda:*`, `events:*`
- [ ] Region: `us-east-1` (Cost Explorer is global)
- [ ] AWS Support plan: Business or Enterprise for full Trusted Advisor
- [ ] EC2 instances running (for Compute Optimizer recommendations)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
```

---

## Decision Point 1

**Pricing models — which to use for which workloads?**

| Model | Discount vs On-Demand | Commitment | Best For |
|-------|----------------------|-----------|----------|
| **On-Demand** | Baseline | None | Unpredictable, short-term |
| **Spot** ✅ 70% savings | Up to 90% | None | Non-critical, stateless, batch |
| **Reserved Instances (RI)** ✅ | 30-60% | 1-3 years | Predictable, steady-state |
| **Savings Plans** ✅ | 20-66% | 1-3 years | Flexible across instance families |
| **Dedicated Hosts** | Premium | 1-3 years | Licensing, compliance |

**Spot for this project:**
- Dev/test workloads: 100% Spot
- Batch jobs, data processing: 100% Spot
- Web servers behind ALB: Mix (Spot + On-Demand base)
- Production databases: On-Demand or Reserved

**Savings Plans for this project:**
- Compute Savings Plans: 66% savings, flexible across EC2, Fargate, Lambda
- EC2 Instance Savings Plans: Up to 72%, locked to family+region

---

## 1. Architecture Overview

```
Cost Optimization Stack:

Trusted Advisor ──────────────────────────────────────────────→ Recommendations
    └── Idle EC2, underutilized RDS, unattached EBS, etc.

Compute Optimizer ─────────────────────────────────────────────→ Right-size
    └── EC2, ECS, Lambda, RDS — ML-based recommendations

EventBridge (cron: every 15 min) ─────────────────────────────→ Lambda
    └── Lambda checks CPU < 5% for 30 min → stops EC2 instance

Spot Fleet (dev/test EC2 workloads) ──────────────────────────→ 70% savings
    └── Multiple instance types → auto-replacement on interruption

Savings Plans (committed usage) ──────────────────────────────→ 20-66% savings
    └── Compute Savings Plan: 66% off Fargate+Lambda+EC2
```

---

## 2. Analyze with Trusted Advisor

```bash
# Trusted Advisor checks (requires Business or Enterprise support)
# Free tier: only 7 core checks

# List all Trusted Advisor checks
aws support describe-trusted-advisor-checks \
  --language en \
  --query 'checks[?category==`cost_optimizing`].{Id:id,Name:name}' \
  --output table

# Get results for a specific check
# Check ID for "Low Utilization Amazon EC2 Instances": r3Wyizknxk
aws support describe-trusted-advisor-check-result \
  --check-id r3Wyizknxk \
  --language en \
  --query 'result.flaggedResources[].{Region:region,InstanceId:metadata[1],DailyCost:metadata[3],AvgCPU:metadata[4]}'

# Refresh a check
aws support refresh-trusted-advisor-check --check-id r3Wyizknxk

# Summary of all cost optimization checks
aws support describe-trusted-advisor-checks \
  --language en \
  --query 'checks[?category==`cost_optimizing`].id' \
  --output text | tr '\t' '\n' | \
  xargs -I{} aws support describe-trusted-advisor-check-summary \
  --check-ids {} \
  --query 'summaries[0].{Check:checkId,Status:status,CostOptimizing:categorySpecificSummary.costOptimizing}'
```

---

## 3. Get Compute Optimizer Recommendations

```bash
# Enable Compute Optimizer (opt-in required)
aws compute-optimizer update-enrollment-status \
  --status Active \
  --include-member-accounts  # If Organizations member

# Get EC2 instance recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --query 'instanceRecommendations[*].{
    Instance:instanceArn,
    CurrentType:currentInstanceType,
    Finding:finding,
    RecommendedType:recommendationOptions[0].instanceType,
    Savings:recommendationOptions[0].estimatedMonthlySavings.value
  }' \
  --output table

# Get Lambda recommendations
aws compute-optimizer get-lambda-function-recommendations \
  --query 'lambdaFunctionRecommendations[*].{
    Function:functionArn,
    Finding:finding,
    CurrentMemory:memorySizeRecommendationOptions[0].memorySize
  }'

# Get ECS Fargate recommendations
aws compute-optimizer get-ecs-service-recommendations \
  --query 'ecsServiceRecommendations[*].{
    Service:serviceArn,
    Finding:finding,
    CurrentCPU:currentServiceConfiguration.cpu,
    CurrentMem:currentServiceConfiguration.memory
  }'

# Get RDS recommendations
aws compute-optimizer get-rds-database-recommendations \
  --query 'rdsDBRecommendations[*].{
    DB:resourceArn,
    Finding:finding,
    CurrentClass:currentDBInstanceClass
  }'
```

---

## 4. Launch Spot Instances for Dev Workloads

```bash
# Option A: EC2 Fleet (multiple instance types = higher availability)
cat > /tmp/spot-fleet.json << 'EOF'
{
  "IamFleetRole": "arn:aws:iam::ACCOUNT:role/AmazonEC2SpotFleetTaggingRole",
  "AllocationStrategy": "capacityOptimized",
  "TargetCapacity": 4,
  "Type": "maintain",
  "LaunchTemplateConfigs": [
    {
      "LaunchTemplateSpecification": {
        "LaunchTemplateName": "dev-instance-template",
        "Version": "$Latest"
      },
      "Overrides": [
        {"InstanceType": "m5.large", "SubnetId": "subnet-aaa"},
        {"InstanceType": "m5a.large", "SubnetId": "subnet-aaa"},
        {"InstanceType": "m4.large", "SubnetId": "subnet-aaa"},
        {"InstanceType": "m5.xlarge", "SubnetId": "subnet-bbb"},
        {"InstanceType": "c5.large", "SubnetId": "subnet-bbb"}
      ]
    }
  ]
}
EOF

# Replace ACCOUNT with your account ID
sed -i "s/ACCOUNT/$ACCOUNT_ID/g" /tmp/spot-fleet.json

FLEET_ID=$(aws ec2 request-spot-fleet \
  --spot-fleet-request-config file:///tmp/spot-fleet.json \
  --query 'SpotFleetRequestId' \
  --output text)

echo "Spot Fleet: $FLEET_ID"

# Option B: Simple Spot instance (testing)
SPOT_INSTANCE=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"one-time","InstanceInterruptionBehavior":"terminate"}}' \
  --key-name my-key \
  --security-group-ids sg-xxxx \
  --subnet-id subnet-xxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Environment,Value=dev},{Key=SpotInstance,Value=true}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Spot Instance: $SPOT_INSTANCE"
```

---

## 5A. Console: View Trusted Advisor Cost Recommendations

1. Navigate to **AWS Trusted Advisor**
2. Click **Cost Optimization** tab
3. Review checks:
   - **Low utilization Amazon EC2 instances** — instances with < 10% CPU
   - **Idle RDS DB instances** — no connections for 7 days
   - **Underutilized EBS volumes** — volumes with < 1 IOPS/day
   - **Unassociated Elastic IP addresses** — unused EIPs ($3.65/month each)
4. Click on each finding to see affected resources and estimated savings

---

## 5B. CLI: Purchase Savings Plans

```bash
# Get savings plan recommendations from Cost Explorer
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days THIRTY_DAYS \
  --query '{
    EstimatedSavings:SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0].EstimatedMonthlySavingsAmount,
    RecommendedCommitment:SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0].HourlyCommitmentToDeploy,
    CurrentOnDemand:SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0].CurrentMinimumHourlyOnDemandSpend
  }'

# View existing Savings Plans
aws savingsplans describe-savings-plans \
  --states active \
  --query 'savingsPlans[].{Type:savingsPlansType,Commitment:commitment,Savings:recurringPaymentAmount,Expiry:end}'

# Purchase Savings Plan (use console for actual purchase — safer)
# aws savingsplans create-savings-plan \
#   --savings-plan-offering-id "xxxxx" \
#   --commitment 1.00 \
#   --purchase-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## 6. Auto-Stop Idle EC2 with Lambda + EventBridge

```bash
# Create Lambda to stop idle EC2 instances
cat > /tmp/auto_stop_ec2.py << 'PYEOF'
import boto3
import json
import os
from datetime import datetime, timezone, timedelta

ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')

CPU_THRESHOLD = float(os.environ.get('CPU_THRESHOLD', '5.0'))
IDLE_MINUTES = int(os.environ.get('IDLE_MINUTES', '30'))
TAG_KEY = os.environ.get('TAG_KEY', 'AutoStop')
TAG_VALUE = os.environ.get('TAG_VALUE', 'true')

def lambda_handler(event, context):
    """Stop EC2 instances with low CPU that have the AutoStop=true tag."""
    
    # Find running instances with AutoStop tag
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}
        ]
    )
    
    stopped = []
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=IDLE_MINUTES)
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            
            # Get CPU utilization for past IDLE_MINUTES
            metrics = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=IDLE_MINUTES * 60,
                Statistics=['Average']
            )
            
            if not metrics['Datapoints']:
                print(f"No metrics for {instance_id} — skipping")
                continue
            
            avg_cpu = metrics['Datapoints'][0]['Average']
            
            if avg_cpu < CPU_THRESHOLD:
                print(f"Stopping {instance_id}: CPU={avg_cpu:.2f}% < {CPU_THRESHOLD}%")
                ec2.stop_instances(InstanceIds=[instance_id])
                stopped.append({'instance': instance_id, 'cpu': avg_cpu})
    
    return {'stopped': stopped, 'count': len(stopped)}
PYEOF

zip /tmp/auto_stop_ec2.zip /tmp/auto_stop_ec2.py

# Create Lambda
LAMBDA_ARN=$(aws lambda create-function \
  --function-name auto-stop-idle-ec2 \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/lambda-ec2-autostop-role" \
  --handler auto_stop_ec2.lambda_handler \
  --zip-file fileb:///tmp/auto_stop_ec2.zip \
  --environment "Variables={CPU_THRESHOLD=5.0,IDLE_MINUTES=30,TAG_KEY=AutoStop,TAG_VALUE=true}" \
  --timeout 300 \
  --description "Auto-stop idle EC2 instances to reduce costs" \
  --query 'FunctionArn' \
  --output text)

# EventBridge rule: run every 15 minutes
aws events put-rule \
  --name "auto-stop-idle-ec2-schedule" \
  --schedule-expression "rate(15 minutes)" \
  --state ENABLED \
  --description "Check for idle EC2 every 15 minutes"

aws events put-targets \
  --rule "auto-stop-idle-ec2-schedule" \
  --targets "[{\"Id\": \"1\", \"Arn\": \"$LAMBDA_ARN\"}]"

aws lambda add-permission \
  --function-name auto-stop-idle-ec2 \
  --statement-id EventBridgeSchedule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com

# Tag EC2 instances to be managed
aws ec2 create-tags \
  --resources i-xxxx1 i-xxxx2 \
  --tags Key=AutoStop,Value=true
```

---

## 7. Use Cost Explorer for Analysis

```bash
# Get monthly costs by service
aws ce get-cost-and-usage \
  --time-period "Start=$(date -d 'first day of last month' +%Y-%m-01),End=$(date +%Y-%m-01)" \
  --granularity MONTHLY \
  --metrics UNBLENDED_COST \
  --group-by '[{"Type":"DIMENSION","Key":"SERVICE"}]' \
  --query 'ResultsByTime[0].Groups[*].{Service:Keys[0],Cost:Metrics.UnblendedCost.Amount}' \
  --output table

# Get EC2 cost breakdown by usage type
aws ce get-cost-and-usage \
  --time-period "Start=$(date -d 'first day of last month' +%Y-%m-01),End=$(date +%Y-%m-01)" \
  --granularity MONTHLY \
  --metrics UNBLENDED_COST \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Compute Cloud - Compute"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"USAGE_TYPE"}]' \
  --query 'ResultsByTime[0].Groups[*].{UsageType:Keys[0],Cost:Metrics.UnblendedCost.Amount}' \
  --output table
```

---

## 8. Create Cost Anomaly Detection

```bash
# Create cost anomaly monitor
MONITOR_ARN=$(aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "myapp-cost-monitor",
    "MonitorType": "DIMENSIONAL",
    "MonitorDimension": "SERVICE"
  }' \
  --query 'MonitorArn' \
  --output text)

# Create SNS subscription for anomaly alerts
SNS_ARN=$(aws sns create-topic \
  --name cost-anomaly-alerts \
  --query TopicArn --output text)

aws sns subscribe \
  --topic-arn $SNS_ARN \
  --protocol email \
  --notification-endpoint finops@yourcompany.com

# Create anomaly subscription
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "cost-spike-alert",
    "Subscribers": [{"Address": "'"$SNS_ARN"'", "Type": "SNS"}],
    "Threshold": 20.0,
    "Frequency": "DAILY",
    "MonitorArnList": ["'"$MONITOR_ARN"'"]
  }'
```

---

## 9. Right-Size Specific Resources

```bash
# Find and stop unattached EBS volumes
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query 'Volumes[].{Id:VolumeId,Size:Size,Type:VolumeType,Monthly:Size}' \
  --output table

# Delete unattached volumes (CAUTION — verify they are not needed)
# aws ec2 delete-volume --volume-id vol-xxxx

# Find unassociated Elastic IPs
aws ec2 describe-addresses \
  --query 'Addresses[?!InstanceId].{AllocationId:AllocationId,IP:PublicIp}' \
  --output table

# Release unused Elastic IPs
# aws ec2 release-address --allocation-id eipalloc-xxxx

# Find old snapshots (older than 30 days)
aws ec2 describe-snapshots \
  --owner-ids self \
  --query 'Snapshots[?StartTime<=`2024-01-01T00:00:00Z`].{Id:SnapshotId,Size:VolumeSize,Date:StartTime}' \
  --output table
```

---

## 10. Verify Cost Optimization Setup

```bash
echo "=== Cost Optimization Verification ==="

# 1. Compute Optimizer enabled
aws compute-optimizer get-enrollment-status \
  --query 'status'

# 2. Auto-stop Lambda running
aws lambda get-function \
  --function-name auto-stop-idle-ec2 \
  --query 'Configuration.{State:State,LastModified:LastModified}'

# 3. EventBridge rule active
aws events describe-rule \
  --name "auto-stop-idle-ec2-schedule" \
  --query '{State:State,Schedule:ScheduleExpression}'

# 4. Current month spend
aws ce get-cost-and-usage \
  --time-period "Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d)" \
  --granularity MONTHLY \
  --metrics UNBLENDED_COST \
  --query 'ResultsByTime[0].Total.UnblendedCost.Amount'

# 5. Savings Plans coverage
aws ce get-savings-plans-coverage \
  --time-period "Start=$(date -d 'first day of last month' +%Y-%m-01),End=$(date +%Y-%m-01)" \
  --granularity MONTHLY \
  --query 'SavingsPlansCoverages[0].Coverage.CoverageHoursPercentage'

echo "=== Cost Optimization Active ==="
```

---

## Troubleshooting

**Trusted Advisor checks not showing:**
```bash
# Requires Business or Enterprise support plan
aws support describe-severity-levels  # If no error, Business+ plan active
```

**Auto-stop Lambda not stopping instances:**
```bash
# Check Lambda execution logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/auto-stop-idle-ec2 \
  --filter-pattern "Stopping"
# Verify instances have AutoStop=true tag
```

**Compute Optimizer no recommendations:**
```bash
# Must be opted in for > 30 hours
aws compute-optimizer get-enrollment-status
# Wait 24-48 hours after opting in
```

---

## Expected Outcome

- ✅ Trusted Advisor reviewing cost optimization checks
- ✅ Compute Optimizer providing right-size recommendations
- ✅ Spot Fleet running dev workloads at 70% discount
- ✅ Auto-stop Lambda stopping idle EC2 every 15 minutes
- ✅ Cost Anomaly Detection alerting on unusual spending
- ✅ Cost Explorer showing per-service breakdown
- ✅ Unattached EBS and unused EIPs identified and removed

---

## Cleanup

```bash
# Delete auto-stop Lambda and EventBridge rule
aws events remove-targets --rule "auto-stop-idle-ec2-schedule" --ids "1"
aws events delete-rule --name "auto-stop-idle-ec2-schedule"
aws lambda delete-function --function-name auto-stop-idle-ec2

# Cancel Spot Fleet
aws ec2 cancel-spot-fleet-requests \
  --spot-fleet-request-ids $FLEET_ID \
  --terminate-instances

# Delete cost anomaly monitor
aws ce delete-anomaly-monitor --monitor-arn $MONITOR_ARN

# Delete SNS topic
aws sns delete-topic --topic-arn $SNS_ARN

echo "Cost optimization cleanup complete"
echo "Savings Plans: cannot cancel — run until expiry"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
