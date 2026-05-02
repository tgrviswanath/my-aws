#!/bin/bash
# AWS Unused Resources Cleanup Script
# WARNING: Review output before deleting anything
# Run with DRY_RUN=true to preview without deleting

set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
DRY_RUN="${DRY_RUN:-true}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=== AWS Unused Resources Audit ==="
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Dry Run: $DRY_RUN"
echo ""

# ── Unattached EBS Volumes ────────────────────────────────────────────────────
echo "=== Unattached EBS Volumes ==="
UNATTACHED_VOLUMES=$(aws ec2 describe-volumes \
  --region $REGION \
  --filters Name=status,Values=available \
  --query 'Volumes[*].{ID:VolumeId,Size:Size,Type:VolumeType,Created:CreateTime}' \
  --output table)

echo "$UNATTACHED_VOLUMES"

if [ "$DRY_RUN" = "false" ]; then
  VOLUME_IDS=$(aws ec2 describe-volumes \
    --region $REGION \
    --filters Name=status,Values=available \
    --query 'Volumes[*].VolumeId' \
    --output text)
  
  for VOL_ID in $VOLUME_IDS; do
    echo "Deleting volume: $VOL_ID"
    aws ec2 delete-volume --volume-id $VOL_ID --region $REGION
  done
fi

# ── Unassociated Elastic IPs ──────────────────────────────────────────────────
echo ""
echo "=== Unassociated Elastic IPs ==="
UNASSOC_EIPS=$(aws ec2 describe-addresses \
  --region $REGION \
  --filters Name=association-id,Values="" \
  --query 'Addresses[*].{IP:PublicIp,AllocationId:AllocationId}' \
  --output table)

echo "$UNASSOC_EIPS"

if [ "$DRY_RUN" = "false" ]; then
  ALLOC_IDS=$(aws ec2 describe-addresses \
    --region $REGION \
    --filters Name=association-id,Values="" \
    --query 'Addresses[*].AllocationId' \
    --output text)
  
  for ALLOC_ID in $ALLOC_IDS; do
    echo "Releasing EIP: $ALLOC_ID"
    aws ec2 release-address --allocation-id $ALLOC_ID --region $REGION
  done
fi

# ── Stopped EC2 Instances (> 7 days) ─────────────────────────────────────────
echo ""
echo "=== Stopped EC2 Instances (stopped > 7 days) ==="
CUTOFF_DATE=$(date -d '7 days ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null || \
              date -v-7d +%Y-%m-%dT%H:%M:%S)

aws ec2 describe-instances \
  --region $REGION \
  --filters Name=instance-state-name,Values=stopped \
  --query "Reservations[*].Instances[?StateTransitionReason!=null].{ID:InstanceId,Type:InstanceType,Name:Tags[?Key=='Name']|[0].Value,Stopped:StateTransitionReason}" \
  --output table

# ── Old EBS Snapshots (> 90 days) ─────────────────────────────────────────────
echo ""
echo "=== EBS Snapshots older than 90 days ==="
CUTOFF=$(date -d '90 days ago' +%Y-%m-%d 2>/dev/null || date -v-90d +%Y-%m-%d)

OLD_SNAPSHOTS=$(aws ec2 describe-snapshots \
  --region $REGION \
  --owner-ids $ACCOUNT_ID \
  --query "Snapshots[?StartTime<='${CUTOFF}'].{ID:SnapshotId,Size:VolumeSize,Date:StartTime,Desc:Description}" \
  --output table)

echo "$OLD_SNAPSHOTS"

# ── Unused Load Balancers ─────────────────────────────────────────────────────
echo ""
echo "=== Load Balancers with no targets ==="
aws elbv2 describe-load-balancers \
  --region $REGION \
  --query 'LoadBalancers[*].{Name:LoadBalancerName,DNS:DNSName,State:State.Code}' \
  --output table

# Check each ALB for empty target groups
ALB_ARNS=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query 'LoadBalancers[*].LoadBalancerArn' \
  --output text)

for ALB_ARN in $ALB_ARNS; do
  TG_ARNS=$(aws elbv2 describe-target-groups \
    --load-balancer-arn $ALB_ARN \
    --query 'TargetGroups[*].TargetGroupArn' \
    --output text 2>/dev/null || echo "")
  
  for TG_ARN in $TG_ARNS; do
    TARGET_COUNT=$(aws elbv2 describe-target-health \
      --target-group-arn $TG_ARN \
      --query 'length(TargetHealthDescriptions)' \
      --output text)
    
    if [ "$TARGET_COUNT" = "0" ]; then
      ALB_NAME=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $ALB_ARN \
        --query 'LoadBalancers[0].LoadBalancerName' \
        --output text)
      echo "WARNING: ALB $ALB_NAME has empty target group: $TG_ARN"
    fi
  done
done

# ── Unused Security Groups ────────────────────────────────────────────────────
echo ""
echo "=== Potentially unused Security Groups ==="
# Get all SGs
ALL_SGS=$(aws ec2 describe-security-groups \
  --region $REGION \
  --query 'SecurityGroups[*].GroupId' \
  --output text)

# Get SGs in use by EC2
USED_BY_EC2=$(aws ec2 describe-instances \
  --region $REGION \
  --query 'Reservations[*].Instances[*].SecurityGroups[*].GroupId' \
  --output text | tr '\t' '\n' | sort -u)

# Get SGs in use by RDS
USED_BY_RDS=$(aws rds describe-db-instances \
  --region $REGION \
  --query 'DBInstances[*].VpcSecurityGroups[*].VpcSecurityGroupId' \
  --output text | tr '\t' '\n' | sort -u)

echo "Total SGs: $(echo $ALL_SGS | wc -w)"
echo "Used by EC2: $(echo $USED_BY_EC2 | wc -w)"

# ── Lambda Functions not invoked in 30 days ───────────────────────────────────
echo ""
echo "=== Lambda Functions with no invocations in 30 days ==="
CUTOFF_EPOCH=$(date -d '30 days ago' +%s 2>/dev/null || date -v-30d +%s)

aws lambda list-functions \
  --region $REGION \
  --query 'Functions[*].FunctionName' \
  --output text | tr '\t' '\n' | while read FUNC_NAME; do
  
  INVOCATIONS=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=$FUNC_NAME \
    --start-time $(date -d '30 days ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -v-30d +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date +%Y-%m-%dT%H:%M:%S) \
    --period 2592000 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text 2>/dev/null || echo "0")
  
  if [ "$INVOCATIONS" = "None" ] || [ "$INVOCATIONS" = "0" ]; then
    echo "No invocations: $FUNC_NAME"
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Summary ==="
echo "Review the above resources and set DRY_RUN=false to delete."
echo "IMPORTANT: Always verify before deleting production resources!"
echo ""
echo "Estimated monthly savings from cleanup:"
echo "- Each unattached EBS gp3 100GB: ~\$8/month"
echo "- Each unassociated EIP: ~\$3.60/month"
echo "- Each idle ALB: ~\$16/month"
