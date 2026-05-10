# Cost Optimization — Real-World Use Cases

## Use Case 1: Find and Eliminate Waste

**Business Problem**: AWS bill is $50K/month. Find unused resources and cut costs by 20%.

```bash
# 1. Unattached EBS volumes (paying for storage with no instance)
echo "=== Unattached EBS Volumes ==="
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].{ID:VolumeId,Size:Size,Type:VolumeType,Created:CreateTime}' \
  --output table
# Each 100GB gp3 volume = $8/month wasted

# 2. Unassociated Elastic IPs ($3.60/month each)
echo "=== Unassociated Elastic IPs ==="
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null].{IP:PublicIp,AllocationId:AllocationId}' \
  --output table

# 3. Stopped EC2 instances (still paying for EBS)
echo "=== Stopped EC2 Instances ==="
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=stopped \
  --query 'Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,Name:Tags[?Key==`Name`]|[0].Value,Stopped:StateTransitionReason}' \
  --output table

# 4. Idle load balancers (no targets or all unhealthy)
echo "=== Load Balancers with No Healthy Targets ==="
for ALB_ARN in $(aws elbv2 describe-load-balancers --query 'LoadBalancers[*].LoadBalancerArn' --output text); do
  HEALTHY=$(aws elbv2 describe-target-health \
    --target-group-arn $(aws elbv2 describe-target-groups \
      --load-balancer-arn $ALB_ARN \
      --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null) \
    --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`] | length(@)' \
    --output text 2>/dev/null || echo "0")
  if [ "$HEALTHY" = "0" ]; then
    echo "Idle ALB: $ALB_ARN"
  fi
done

# 5. Old snapshots (> 90 days)
echo "=== EBS Snapshots Older Than 90 Days ==="
CUTOFF=$(date -d '90 days ago' +%Y-%m-%d 2>/dev/null || date -v-90d +%Y-%m-%d)
aws ec2 describe-snapshots \
  --owner-ids self \
  --query "Snapshots[?StartTime<='${CUTOFF}'].{ID:SnapshotId,Size:VolumeSize,Date:StartTime}" \
  --output table

# 6. Lambda functions not invoked in 30 days
echo "=== Unused Lambda Functions ==="
aws lambda list-functions \
  --query 'Functions[*].FunctionName' \
  --output text | tr '\t' '\n' | while read FUNC; do
  INVOCATIONS=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=$FUNC \
    --start-time $(date -d '30 days ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -v-30d +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date +%Y-%m-%dT%H:%M:%S) \
    --period 2592000 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text 2>/dev/null || echo "0")
  if [ "$INVOCATIONS" = "None" ] || [ "$INVOCATIONS" = "0" ]; then
    echo "Unused Lambda: $FUNC"
  fi
done
```

**What you learn**: Resource audit, identifying waste, cost per resource type.

---

## Use Case 2: Right-Size EC2 Instances

**Business Problem**: 20 EC2 instances running at 5% CPU average. They're massively over-provisioned.

```bash
# 1. Get Compute Optimizer recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --filters Name=Finding,Values=OVER_PROVISIONED \
  --query 'instanceRecommendations[*].{
    Instance:instanceArn,
    CurrentType:currentInstanceType,
    RecommendedType:recommendationOptions[0].instanceType,
    SavingsPct:recommendationOptions[0].estimatedMonthlySavings.value
  }' \
  --output table

# 2. Check actual CPU utilization for a specific instance
INSTANCE_ID="i-1234567890abcdef0"
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -v-14d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average Maximum \
  --query 'Datapoints[*].{Date:Timestamp,Avg:Average,Max:Maximum}' \
  --output table

# 3. Resize instance (requires stop/start)
aws ec2 stop-instances --instance-ids $INSTANCE_ID
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID

aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --instance-type Value=t3.small  # Downsize from m5.large

aws ec2 start-instances --instance-ids $INSTANCE_ID

# 4. For ASG: update launch template
aws ec2 create-launch-template-version \
  --launch-template-id $LT_ID \
  --source-version '$Latest' \
  --launch-template-data '{"InstanceType": "t3.small"}'

aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name "my-asg" \
  --launch-template LaunchTemplateId=$LT_ID,Version='$Latest'

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name "my-asg" \
  --preferences '{"MinHealthyPercentage": 90, "InstanceWarmup": 300}'
```

**What you learn**: Compute Optimizer, right-sizing workflow, instance refresh for zero-downtime resize.

---

## Use Case 3: Spot Instances for Batch Workloads

**Business Problem**: Nightly data processing job runs on 10 m5.xlarge instances for 4 hours. Cost: $7.68/night. Reduce by 70%.

```bash
# On-Demand: 10 × m5.xlarge × 4hr × $0.192/hr = $7.68/night
# Spot:      10 × m5.xlarge × 4hr × $0.058/hr = $2.32/night (70% savings)

# 1. Check Spot price history
aws ec2 describe-spot-price-history \
  --instance-types m5.xlarge m5a.xlarge m4.xlarge \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --query 'SpotPriceHistory[*].{Type:InstanceType,AZ:AvailabilityZone,Price:SpotPrice,Time:Timestamp}' \
  --output table

# 2. Create Spot fleet with multiple instance types (capacity-optimized)
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "IamFleetRole": "arn:aws:iam::123456789:role/AmazonEC2SpotFleetRole",
    "TargetCapacity": 10,
    "AllocationStrategy": "capacityOptimized",
    "InstanceInterruptionBehavior": "terminate",
    "LaunchSpecifications": [
      {
        "ImageId": "ami-0c02fb55956c7d316",
        "InstanceType": "m5.xlarge",
        "SubnetId": "subnet-aaa",
        "UserData": "'"$(base64 -w0 process_data.sh)"'"
      },
      {
        "ImageId": "ami-0c02fb55956c7d316",
        "InstanceType": "m5a.xlarge",
        "SubnetId": "subnet-bbb"
      },
      {
        "ImageId": "ami-0c02fb55956c7d316",
        "InstanceType": "m4.xlarge",
        "SubnetId": "subnet-ccc"
      }
    ]
  }'

# 3. Handle Spot interruption in your script
cat > process_data.sh << 'EOF'
#!/bin/bash
# Poll for interruption notice every 5 seconds
check_interruption() {
  TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/spot/termination-time)
  echo $STATUS
}

# Save progress to S3 so we can resume
save_checkpoint() {
  aws s3 cp /tmp/progress.json s3://my-bucket/checkpoints/$(hostname).json
}

# Main processing loop
while IFS= read -r line; do
  process_line "$line"
  # Check for interruption every 100 lines
  if (( COUNTER % 100 == 0 )); then
    if [ "$(check_interruption)" = "200" ]; then
      echo "Spot interruption imminent! Saving checkpoint..."
      save_checkpoint
      exit 0
    fi
  fi
  ((COUNTER++))
done < /data/input.csv
EOF
```

**What you learn**: Spot fleet, capacity-optimized strategy, interruption handling, checkpoint pattern.

---

## Use Case 4: S3 Lifecycle Policies for Storage Cost

**Business Problem**: S3 bucket has 50TB of data. 90% hasn't been accessed in 6 months. Reduce storage cost by 80%.

```bash
# Current cost: 50TB × $0.023/GB = $1,150/month (Standard)
# After lifecycle: ~$230/month (mix of IA + Glacier)

aws s3api put-bucket-lifecycle-configuration \
  --bucket "company-data" \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "intelligent-tiering-for-unknown-access",
        "Status": "Enabled",
        "Filter": {"Prefix": "user-uploads/"},
        "Transitions": [
          {"Days": 0, "StorageClass": "INTELLIGENT_TIERING"}
        ]
      },
      {
        "ID": "archive-old-logs",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Transitions": [
          {"Days": 30,  "StorageClass": "STANDARD_IA"},
          {"Days": 90,  "StorageClass": "GLACIER"},
          {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
        ],
        "Expiration": {"Days": 2555}
      },
      {
        "ID": "delete-temp-files",
        "Status": "Enabled",
        "Filter": {"Prefix": "temp/"},
        "Expiration": {"Days": 7}
      },
      {
        "ID": "cleanup-old-versions",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "NoncurrentVersionTransitions": [
          {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"},
          {"NoncurrentDays": 90, "StorageClass": "GLACIER"}
        ],
        "NoncurrentVersionExpiration": {"NoncurrentDays": 365}
      },
      {
        "ID": "abort-incomplete-multipart",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  }'

# Check storage class distribution
aws s3api list-objects-v2 \
  --bucket "company-data" \
  --query 'Contents[*].StorageClass' \
  --output text | sort | uniq -c | sort -rn
```

**What you learn**: Lifecycle policies, storage class transitions, Intelligent-Tiering, version cleanup.

---

## Use Case 5: Reserved Instances vs Savings Plans

```bash
# 1. Get RI recommendations from Cost Explorer
aws ce get-reservation-purchase-recommendation \
  --service "Amazon EC2" \
  --lookback-period-in-days SIXTY_DAYS \
  --term-in-years ONE_YEAR \
  --payment-option PARTIAL_UPFRONT \
  --query 'Recommendations[*].{
    InstanceType:RecommendationDetails[0].InstanceDetails.EC2InstanceDetails.InstanceType,
    Region:RecommendationDetails[0].InstanceDetails.EC2InstanceDetails.Region,
    MonthlySavings:RecommendationSummary.EstimatedMonthlySavingsAmount,
    SavingsPct:RecommendationSummary.EstimatedSavingsPercentage
  }' \
  --output table

# 2. Get Savings Plans recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option PARTIAL_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS \
  --query 'SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0].{
    HourlyCommitment:HourlyCommitmentToPurchase,
    MonthlySavings:EstimatedMonthlySavingsAmount,
    SavingsPct:EstimatedSavingsPercentage
  }'

# Decision guide:
# Reserved Instances: specific instance type/region/OS — up to 72% savings
# Savings Plans (Compute): any instance family/region/OS — up to 66% savings, more flexible
# Savings Plans (EC2): specific instance family — up to 72% savings, less flexible than Compute SP
# Rule: Use Compute Savings Plans for flexibility, RI for known stable workloads
```

**What you learn**: RI vs Savings Plans trade-offs, Cost Explorer recommendations, commitment strategies.

---

## Monthly Cost Optimization Checklist

```bash
#!/bin/bash
# Run monthly to find savings opportunities

echo "=== Monthly AWS Cost Audit ==="
echo "Date: $(date)"
echo ""

# 1. Unattached EBS volumes
echo "1. Unattached EBS volumes:"
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query 'length(Volumes)' --output text

# 2. Unassociated EIPs
echo "2. Unassociated Elastic IPs:"
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null] | length(@)' --output text

# 3. Stopped instances > 7 days
echo "3. Long-stopped instances:"
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=stopped \
  --query 'length(Reservations[*].Instances[*])' --output text

# 4. Trusted Advisor cost checks
echo "4. Trusted Advisor cost recommendations:"
aws support describe-trusted-advisor-checks --language en \
  --query 'checks[?category==`cost_optimizing`].name' --output table

# 5. Budget status
echo "5. Budget alerts:"
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --query 'Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Actual:CalculatedSpend.ActualSpend.Amount}' \
  --output table
```

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No budget alerts | Surprise bills | Set budgets at 50%, 80%, 100% |
| On-Demand for stable workloads | 40-72% overpaying | Buy Reserved Instances or Savings Plans |
| Not using Spot for batch | 4× higher cost | Use Spot for fault-tolerant batch jobs |
| Ignoring data transfer costs | Hidden costs | Use VPC endpoints, CloudFront, same-region transfers |
| No lifecycle policies on S3 | Storage grows unbounded | Add lifecycle rules from day 1 |
| Over-provisioned instances | Paying for unused capacity | Use Compute Optimizer recommendations |
