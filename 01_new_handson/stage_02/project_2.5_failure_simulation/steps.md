# Steps — Project 2.5 Failure Simulation Lab

## Setup: Enable VPC Flow Logs First

```bash
# Create CloudWatch log group for flow logs
aws logs create-log-group --log-group-name /vpc/flow-logs

# Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /vpc/flow-logs \
  --deliver-logs-permission-arn arn:aws:iam::ACCOUNT_ID:role/flow-logs-role
```

---

## Scenario 1 — EC2 Crash & ASG Recovery

### Break It
```bash
# Terminate one of the ASG instances directly
aws ec2 terminate-instances --instance-ids i-XXXXXXXXXX
```

### Observe
```bash
# Watch ASG detect the failure and launch a replacement
watch -n 10 "aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-asg \
  --query 'AutoScalingGroups[0].Instances[*].{ID:InstanceId,State:LifecycleState,Health:HealthStatus}'"

# Watch ALB target group — unhealthy then replaced
watch -n 10 "aws elbv2 describe-target-health --target-group-arn $TG_ARN"
```

### What to Document
- Time from termination to new instance healthy: _____ minutes
- ASG activity log showing the replacement event

---

## Scenario 2 — Security Group Lockout

### Break It
```bash
# Remove SSH inbound rule from app-sg
aws ec2 revoke-security-group-ingress \
  --group-id $APP_SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32

# Also remove HTTP from ALB
aws ec2 revoke-security-group-ingress \
  --group-id $APP_SG_ID \
  --protocol tcp \
  --port 80 \
  --source-group $ALB_SG_ID
```

### Observe
```bash
# SSH should now fail
ssh -i key.pem ec2-user@EC2_IP
# Expected: Connection timed out

# ALB health checks should fail
aws elbv2 describe-target-health --target-group-arn $TG_ARN
# Expected: unhealthy
```

### Fix Without SSH — Use Systems Manager
```bash
# Connect via SSM Session Manager (no SSH needed)
aws ssm start-session --target i-XXXXXXXXXX

# From inside the instance, verify Nginx is running
systemctl status nginx
curl http://localhost
```

### Restore
```bash
# Re-add the security group rules
aws ec2 authorize-security-group-ingress \
  --group-id $APP_SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32

aws ec2 authorize-security-group-ingress \
  --group-id $APP_SG_ID \
  --protocol tcp \
  --port 80 \
  --source-group $ALB_SG_ID
```

---

## Scenario 3 — Wrong Route Table (Private Subnet Loses Internet)

### Break It
```bash
# Remove the NAT Gateway route from private route table
aws ec2 delete-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0
```

### Observe
```bash
# SSH into a private EC2 instance via SSM
aws ssm start-session --target PRIVATE_INSTANCE_ID

# Try to reach internet — should fail
curl https://example.com
# Expected: curl: (6) Could not resolve host

# Try to reach AWS services — should also fail
aws s3 ls
# Expected: timeout or connection refused
```

### Diagnose with VPC Flow Logs
```bash
# Check flow logs for REJECT entries
aws logs filter-log-events \
  --log-group-name /vpc/flow-logs \
  --filter-pattern "REJECT" \
  --start-time $(date -d '5 minutes ago' +%s000)
```

### Fix
```bash
aws ec2 create-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_ID
```

---

## Scenario 4 — RDS Connection Failure

### Break It
```bash
# Remove app-sg from RDS security group inbound rules
aws ec2 revoke-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 3306 \
  --source-group $APP_SG_ID
```

### Observe
```bash
# From EC2, try to connect to RDS
mysql -h $RDS_ENDPOINT -u admin -p
# Expected: ERROR 2003 (HY000): Can't connect to MySQL server

# Check if port is reachable
nc -zv $RDS_ENDPOINT 3306
# Expected: Connection refused or timed out
```

### Diagnose
```bash
# Check VPC Flow Logs for REJECT on port 3306
aws logs filter-log-events \
  --log-group-name /vpc/flow-logs \
  --filter-pattern "3306 REJECT"

# Verify RDS security group
aws ec2 describe-security-groups --group-ids $RDS_SG_ID
```

### Fix
```bash
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 3306 \
  --source-group $APP_SG_ID
```

---

## Scenario 5 — IAM Permission Denied

### Break It
```bash
# Remove S3 read permission from EC2 role
aws iam detach-role-policy \
  --role-name ec2-s3-read-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/S3ReadSpecificBucket
```

### Observe
```bash
# From EC2 instance (using instance role)
aws s3 ls s3://your-bucket
# Expected: An error occurred (AccessDenied)
```

### Diagnose with CloudTrail
```bash
# Find the AccessDenied event in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ListObjects \
  --start-time $(date -d '10 minutes ago' --iso-8601=seconds) \
  --query "Events[?contains(CloudTrailEvent, 'AccessDenied')]"
```

### Fix
```bash
aws iam attach-role-policy \
  --role-name ec2-s3-read-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/S3ReadSpecificBucket
```

---

## Diagnosis Toolkit

```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids $SG_ID

# Check route tables
aws ec2 describe-route-tables --route-table-ids $RT_ID

# Check VPC Flow Logs for blocked traffic
aws logs filter-log-events \
  --log-group-name /vpc/flow-logs \
  --filter-pattern "REJECT"

# Check CloudTrail for API errors
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AccessDenied

# Test connectivity from EC2
ping 8.8.8.8
curl -v http://example.com
nc -zv RDS_ENDPOINT 3306
telnet RDS_ENDPOINT 3306
```

---

## Screenshots to Take
- [ ] ASG replacing terminated instance (activity log)
- [ ] SSH timeout when SG rule removed
- [ ] SSM Session Manager connecting without SSH
- [ ] VPC Flow Logs showing REJECT entries
- [ ] RDS connection error message
- [ ] CloudTrail showing AccessDenied event
- [ ] Each scenario: before (broken) and after (fixed)
