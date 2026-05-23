# Verification & Validation — Project 2.5 Failure Simulation Lab

---

## 1. Pre-Lab Setup Verification

```bash
# VPC Flow Logs enabled
aws ec2 describe-flow-logs \
  --filter "Name=resource-id,Values=$VPC_ID" \
  --query "FlowLogs[*].{ID:FlowLogId,Status:FlowLogStatus,Dest:LogDestinationType}"
# Expected: FlowLogStatus=ACTIVE

# CloudWatch log group exists
aws logs describe-log-groups \
  --log-group-name-prefix /vpc/flow-logs \
  --query "logGroups[*].logGroupName"
# Expected: /vpc/flow-logs listed

# SSM agent running on EC2 instances
aws ssm describe-instance-information \
  --query "InstanceInformationList[*].{ID:InstanceId,Status:PingStatus}"
# Expected: PingStatus=Online for all instances
```

📸 Screenshot: VPC Flow Logs showing ACTIVE status  
📸 Screenshot: SSM Session Manager showing instances as Online

---

## 2. Scenario 1 — EC2 Crash & ASG Recovery

```bash
# Before: 2 healthy instances
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: 2 healthy

# Break: terminate one instance
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-asg \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# Observe: ASG activity log shows replacement
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name app-asg \
  --query "Activities[0].{Status:StatusCode,Cause:Cause,Start:StartTime}"
# Expected: Cause mentions "unhealthy" and "Launching a new EC2 instance"

# After: back to 2 healthy (takes ~3-5 min)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: 2 healthy again (different instance ID)
```

📸 Screenshot: ASG activity log showing termination + replacement event  
📸 Screenshot: Target group back to 2 healthy after recovery

---

## 3. Scenario 2 — Security Group Lockout

```bash
# Break: remove SSH and HTTP rules from app-sg
aws ec2 revoke-security-group-ingress \
  --group-id $APP_SG_ID --protocol tcp --port 22 --cidr YOUR_IP/32
aws ec2 revoke-security-group-ingress \
  --group-id $APP_SG_ID --protocol tcp --port 80 --source-group $ALB_SG_ID

# Observe: SSH fails
ssh -i key.pem -o ConnectTimeout=5 ec2-user@EC2_IP
# Expected: Connection timed out

# Observe: ALB targets unhealthy
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].TargetHealth.State"
# Expected: unhealthy

# Fix without SSH — use SSM
aws ssm start-session --target $INSTANCE_ID
# Expected: shell access without SSH

# Restore rules
aws ec2 authorize-security-group-ingress \
  --group-id $APP_SG_ID --protocol tcp --port 22 --cidr YOUR_IP/32
aws ec2 authorize-security-group-ingress \
  --group-id $APP_SG_ID --protocol tcp --port 80 --source-group $ALB_SG_ID

# Verify restored
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].TargetHealth.State"
# Expected: healthy again
```

📸 Screenshot: SSH timeout when SG rule removed  
📸 Screenshot: SSM Session Manager connecting without SSH

---

## 4. Scenario 3 — Wrong Route Table

```bash
# Break: remove NAT route from private RT
aws ec2 delete-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0

# Observe: private EC2 loses internet
aws ssm start-session --target PRIVATE_INSTANCE_ID
# Inside EC2:
curl --max-time 5 https://example.com
# Expected: curl: (28) Operation timed out

# Diagnose: VPC Flow Logs show REJECT
aws logs filter-log-events \
  --log-group-name /vpc/flow-logs \
  --filter-pattern "REJECT" \
  --start-time $(date -d '5 minutes ago' +%s000 2>/dev/null || date -v-5M +%s000)
# Expected: REJECT entries for outbound traffic

# Fix: restore NAT route
aws ec2 create-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_ID

# Verify restored
# Inside EC2:
curl -s https://checkip.amazonaws.com
# Expected: NAT Gateway EIP returned
```

📸 Screenshot: VPC Flow Logs showing REJECT entries  
📸 Screenshot: curl timeout (broken) vs success (fixed)

---

## 5. Scenario 4 — RDS Connection Failure

```bash
# Break: remove app-sg from RDS SG
aws ec2 revoke-security-group-ingress \
  --group-id $RDS_SG_ID --protocol tcp --port 3306 --source-group $APP_SG_ID

# Observe: MySQL connection fails
# From EC2:
nc -zv $RDS_ENDPOINT 3306
# Expected: Connection timed out

# Diagnose: Flow Logs show REJECT on 3306
aws logs filter-log-events \
  --log-group-name /vpc/flow-logs \
  --filter-pattern "3306 REJECT"
# Expected: REJECT entries for port 3306

# Fix
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID --protocol tcp --port 3306 --source-group $APP_SG_ID

# Verify
nc -zv $RDS_ENDPOINT 3306
# Expected: Connection succeeded
```

---

## 6. Scenario 5 — IAM Permission Denied

```bash
# Break: detach S3 policy from EC2 role
aws iam detach-role-policy \
  --role-name ec2-s3-read-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/S3ReadSpecificBucket

# Observe: S3 access denied from EC2
# From EC2 (using instance role):
aws s3 ls s3://your-bucket
# Expected: An error occurred (AccessDenied)

# Diagnose: CloudTrail shows AccessDenied
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ListObjects \
  --query "Events[?contains(CloudTrailEvent,'AccessDenied')].{Time:EventTime,User:Username}"
# Expected: AccessDenied event visible

# Fix
aws iam attach-role-policy \
  --role-name ec2-s3-read-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/S3ReadSpecificBucket

# Verify
aws s3 ls s3://your-bucket
# Expected: bucket contents listed
```

📸 Screenshot: CloudTrail showing AccessDenied event  
📸 Screenshot: S3 access working after policy restored

---

## 7. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected: VPC, ASG, ALB, RDS, SGs, flow log resources

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 8. Verification Checklist

**Pre-lab:**
- [ ] VPC Flow Logs active
- [ ] SSM agent online on all instances

**Scenario 1 — EC2 Crash:**
- [ ] ASG detects terminated instance and launches replacement
- [ ] ALB returns to 2 healthy targets within ~5 minutes
- [ ] ASG activity log shows replacement event

**Scenario 2 — SG Lockout:**
- [ ] SSH times out when rule removed
- [ ] ALB targets become unhealthy
- [ ] SSM Session Manager connects without SSH
- [ ] Targets healthy again after rules restored

**Scenario 3 — Route Table:**
- [ ] Private EC2 loses internet when NAT route removed
- [ ] VPC Flow Logs show REJECT entries
- [ ] Internet restored after NAT route re-added

**Scenario 4 — RDS Connection:**
- [ ] MySQL connection fails when SG rule removed
- [ ] Flow Logs show REJECT on port 3306
- [ ] Connection restored after SG rule re-added

**Scenario 5 — IAM:**
- [ ] S3 access denied when policy detached
- [ ] CloudTrail shows AccessDenied event
- [ ] S3 access restored after policy re-attached
