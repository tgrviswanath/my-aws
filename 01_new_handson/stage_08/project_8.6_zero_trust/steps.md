# Steps — Project 8.6 Zero Trust Security Lab

## Phase 1 — Enable IAM Identity Center (SSO)

```
1. AWS Console → IAM Identity Center → Enable
2. Choose identity source: Identity Center directory (built-in)
3. Create users:
   - admin@yourcompany.com (admin group)
   - dev@yourcompany.com (developers group)
4. Create permission sets:
   - AdministratorAccess → admin group
   - ReadOnlyAccess → developers group
5. Assign to AWS account
6. Test SSO login: https://YOUR_PORTAL.awsapps.com/start
```

---

## Phase 2 — Enforce MFA for All Users

```
1. IAM Identity Center → Settings → Authentication
2. MFA → Require MFA for all users
3. MFA types: Authenticator app, Security key
4. Test: log in → prompted for MFA
```

---

## Phase 3 — Micro-segmentation with Security Groups

```bash
# Each service gets its own security group
# Services only allow traffic from specific other services

# Example: API service can only talk to DB service
# NOT: "private subnet can talk to private subnet"

# Create per-service security groups
aws ec2 create-security-group \
  --group-name "api-service-sg" \
  --description "API service — only accepts from ALB"

aws ec2 create-security-group \
  --group-name "db-service-sg" \
  --description "DB service — only accepts from API service"

# DB only allows traffic from API service SG
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 3306 \
  --source-group $API_SG_ID
```

---

## Phase 4 — VPC Flow Logs for All Traffic

```bash
# Enable flow logs on all ENIs (not just VPC level)
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /vpc/flow-logs/handson \
  --deliver-logs-permission-arn $FLOW_LOGS_ROLE_ARN

# Query for unexpected connections
aws logs start-query \
  --log-group-name /vpc/flow-logs/handson \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, srcAddr, dstAddr, dstPort, action
    | filter action = "REJECT"
    | stats count(*) by srcAddr, dstAddr, dstPort
    | sort count desc
    | limit 20
  '
```

---

## Phase 5 — Verify Zero Trust Checklist

```bash
# Run this checklist to verify Zero Trust posture

echo "=== Zero Trust Checklist ==="

# 1. No SSH from internet
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.from-port,Values=22" \
            "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --query "SecurityGroups[*].GroupName" --output text
# Expected: empty (no SGs allow SSH from internet)

# 2. No RDS publicly accessible
aws rds describe-db-instances \
  --query "DBInstances[?PubliclyAccessible==\`true\`].DBInstanceIdentifier" \
  --output text
# Expected: empty

# 3. No S3 buckets public
aws s3api list-buckets --query "Buckets[*].Name" --output text | \
  xargs -I{} aws s3api get-bucket-public-access-block --bucket {} 2>/dev/null
# All should show BlockPublicAcls: true

# 4. MFA enabled on all IAM users
aws iam list-users --query "Users[*].UserName" --output text | \
  xargs -I{} aws iam list-mfa-devices --user-name {}
# All users should have MFA devices

# 5. CloudTrail enabled
aws cloudtrail get-trail-status --name handson-trail \
  --query "IsLogging"
# Expected: true
```

---

## Screenshots to Take
- [ ] IAM Identity Center SSO portal
- [ ] MFA enforcement enabled
- [ ] Per-service security groups (not shared)
- [ ] VPC Flow Logs showing REJECT entries for unauthorized traffic
- [ ] Zero Trust checklist all passing
- [ ] GuardDuty + Security Hub active (from 8.4)
