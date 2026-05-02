# AWS Security & Cost Optimization — Scenario-Based Interview Questions

## Security Scenarios

### Scenario 1: Credential Leak
**Q: A developer accidentally committed AWS access keys to a public GitHub repo. What do you do?**

```
Immediate response (within minutes):
1. Deactivate the exposed access key immediately
   aws iam update-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --status Inactive --user-name alice

2. Check CloudTrail for unauthorized usage
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAIOSFODNN7EXAMPLE \
     --start-time 2024-01-01T00:00:00Z

3. Create new access key for the developer
   aws iam create-access-key --user-name alice

4. Delete the old key
   aws iam delete-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --user-name alice

5. Review and revoke any resources created with the compromised key

Prevention:
- Use git-secrets or truffleHog to scan commits
- Use IAM roles instead of access keys for applications
- Enable GuardDuty to detect anomalous API calls
- Set up CloudTrail alerts for unusual activity
```

---

### Scenario 2: S3 Data Breach
**Q: You discover a production S3 bucket containing customer PII is publicly accessible. What do you do?**

```
Immediate:
1. Block public access immediately
   aws s3api put-public-access-block \
     --bucket prod-customer-data \
     --public-access-block-configuration \
       BlockPublicAcls=true,IgnorePublicAcls=true,\
       BlockPublicPolicy=true,RestrictPublicBuckets=true

2. Check access logs to determine what was accessed
   aws s3api get-bucket-logging --bucket prod-customer-data

3. Notify security team and legal (potential GDPR/CCPA notification required)

Investigation:
4. Review S3 access logs and CloudTrail for who accessed what
5. Determine how bucket became public (policy change, ACL change)
6. Check CloudTrail for the change event

Remediation:
7. Enable Macie to scan for PII in all buckets
8. Implement AWS Config rule: S3_BUCKET_PUBLIC_READ_PROHIBITED
9. Enable S3 Block Public Access at account level
   aws s3control put-public-access-block \
     --account-id 123456789 \
     --public-access-block-configuration \
       BlockPublicAcls=true,IgnorePublicAcls=true,\
       BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

### Scenario 3: Ransomware on EC2
**Q: GuardDuty alerts you that an EC2 instance is communicating with a known C&C server. What do you do?**

```
Containment (immediate):
1. Isolate instance — apply restrictive security group
   aws ec2 modify-instance-attribute \
     --instance-id i-compromised \
     --groups sg-isolation  # No inbound/outbound rules

2. Create forensic snapshot before any changes
   aws ec2 create-snapshot \
     --volume-id vol-12345678 \
     --description "Forensic snapshot - incident 2024-01-15"

3. Revoke IAM role credentials
   aws iam put-role-policy \
     --role-name compromised-instance-role \
     --policy-name DenyAll \
     --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'

Investigation:
4. Analyze VPC Flow Logs for lateral movement
5. Review CloudTrail for API calls from the instance
6. Examine instance memory and disk (from snapshot)

Recovery:
7. Terminate compromised instance
8. Launch replacement from known-good AMI
9. Rotate all credentials the instance had access to
10. Patch the vulnerability that allowed compromise
```

---

### Scenario 4: IAM Privilege Escalation
**Q: How would you detect and prevent IAM privilege escalation?**

```
Detection:
- CloudTrail: monitor for iam:CreatePolicy, iam:AttachRolePolicy, iam:PutRolePolicy
- AWS Config rule: IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS
- GuardDuty: Policy:IAMUser/RootCredentialUsage
- IAM Access Analyzer: finds overly permissive policies

Prevention:
1. Permission boundaries — limit max permissions for developer-created roles
   aws iam put-role-permissions-boundary \
     --role-name developer-role \
     --permissions-boundary arn:aws:iam::123456789:policy/DeveloperBoundary

2. SCP to prevent privilege escalation
   {
     "Effect": "Deny",
     "Action": [
       "iam:CreatePolicy",
       "iam:AttachRolePolicy",
       "iam:PutRolePolicy",
       "iam:CreatePolicyVersion"
     ],
     "Resource": "*",
     "Condition": {
       "StringNotEquals": {
         "aws:PrincipalArn": "arn:aws:iam::123456789:role/SecurityAdmin"
       }
     }
   }

3. Use PIM (Privileged Identity Management) — no standing admin access
4. Regular access reviews with IAM Access Analyzer
```

---

## Cost Optimization Scenarios

### Scenario 5: Unexpected Bill Spike
**Q: Your AWS bill doubled this month. How do you investigate?**

```
Investigation steps:
1. Cost Explorer — identify which service increased
   aws ce get-cost-and-usage \
     --time-period Start=2024-01-01,End=2024-02-01 \
     --granularity MONTHLY \
     --metrics BlendedCost \
     --group-by Type=DIMENSION,Key=SERVICE

2. Drill down by resource
   aws ce get-cost-and-usage \
     --time-period Start=2024-01-01,End=2024-02-01 \
     --granularity DAILY \
     --metrics BlendedCost \
     --group-by Type=TAG,Key=Name

3. Check for anomalies
   - New large EC2 instances launched?
   - Data transfer spike (DDoS, misconfigured app)?
   - NAT Gateway processing spike?
   - S3 request spike?

Common causes:
- Forgotten dev/test resources left running
- Data transfer: large files downloaded repeatedly (fix: CloudFront)
- NAT Gateway: Lambda in VPC calling AWS services (fix: VPC endpoints)
- EC2: Auto Scaling scaled out and didn't scale back (fix: scale-in policy)
- RDS: Snapshot storage accumulation (fix: retention policy)

Prevention:
- AWS Budgets with alerts at 50%, 80%, 100%
- Cost Anomaly Detection (ML-based)
- Tag all resources for cost allocation
- Regular Trusted Advisor reviews
```

---

### Scenario 6: Reduce Production Costs by 40%
**Q: Your production environment costs $50,000/month. How do you reduce it by 40%?**

```
Analysis first:
1. Cost Explorer: identify top 5 cost drivers
2. Trusted Advisor: low utilization resources
3. Compute Optimizer: right-sizing recommendations

Typical savings breakdown:
1. Reserved Instances / Savings Plans (biggest impact)
   - Convert PAYG EC2 to 1-year RI: ~40% savings
   - Convert RDS to 1-year RI: ~40% savings
   - Estimated savings: $8,000-12,000/month

2. Right-sizing (Compute Optimizer)
   - Downsize over-provisioned EC2 instances
   - Estimated savings: $3,000-5,000/month

3. Spot Instances for non-critical workloads
   - Batch jobs, dev/test, CI/CD workers
   - Estimated savings: $2,000-4,000/month

4. Storage optimization
   - S3 lifecycle policies (move to IA/Glacier)
   - Delete old EBS snapshots
   - Estimated savings: $1,000-2,000/month

5. NAT Gateway optimization
   - VPC Endpoints for S3/DynamoDB (free)
   - Estimated savings: $500-2,000/month

6. Eliminate waste
   - Unattached EBS volumes, idle load balancers
   - Estimated savings: $500-1,000/month

Total potential savings: $15,000-26,000/month (30-52%)
```

---

### Scenario 7: Multi-Region Cost Optimization
**Q: You're running active-active in 2 regions. How do you optimize costs?**

```
1. Data transfer costs (often overlooked)
   - Cross-region data transfer: $0.02/GB
   - Use CloudFront to cache content at edge (reduces origin hits)
   - Route users to nearest region (Route 53 latency routing)
   - Minimize cross-region API calls

2. Reserved Instances per region
   - Buy RIs in each region separately
   - Regional RIs apply to any AZ in that region

3. Asymmetric sizing
   - Primary region: full capacity
   - Secondary region: reduced capacity (scale up on failover)
   - Use Aurora Global Database (one primary, read-only secondaries)

4. CloudFront for static assets
   - Serve from edge, not from both regions
   - Reduces EC2/ALB load in both regions

5. S3 Cross-Region Replication
   - Only replicate what's needed
   - Use S3 Intelligent-Tiering in secondary region
```

---

## Architecture Design Questions

### Q: Design a highly available web application for 100,000 concurrent users

```
Architecture:
├── Route 53 (latency routing + health checks)
├── CloudFront (CDN, WAF, DDoS protection)
├── ALB (across 3 AZs)
├── EC2 ASG (3 AZs, target tracking 60% CPU)
│   └── t3.large instances (2 vCPU, 8GB)
│   └── Min: 10, Max: 100
├── ElastiCache Redis (session store, query cache)
│   └── cache.r6g.large, 3 nodes
├── Aurora PostgreSQL (Multi-AZ, 2 read replicas)
│   └── db.r6g.2xlarge
└── S3 (static assets, user uploads)

Capacity calculation:
- 100,000 concurrent users
- Assume 10 req/sec per user = 1,000,000 req/sec
- Each EC2 handles ~5,000 req/sec
- Need: 200 EC2 instances at peak
- With 60% target: 333 instances max
- Cost: ~$10,000/month at peak

Optimizations:
- CloudFront caches 80% of requests → only 200,000 reach origin
- ElastiCache handles 70% of DB reads
- Aurora read replicas for remaining reads
- Actual EC2 needed: ~40 instances
- Actual cost: ~$2,000/month
```

---

### Q: Design a disaster recovery solution with RPO < 1 hour, RTO < 4 hours

```
Strategy: Pilot Light

Primary (us-east-1):
├── Full production stack
└── Automated backups to S3 (cross-region replication)

DR (eu-west-1):
├── Aurora cross-region read replica (RPO: ~1 min)
├── AMIs replicated from primary
├── ASG with 0 desired capacity
└── Route 53 failover routing (health check on primary)

Failover automation (Lambda + EventBridge):
1. Route 53 health check fails → EventBridge event
2. Lambda: promote Aurora replica to primary
3. Lambda: update ASG desired capacity to 4
4. Route 53: DNS switches to DR region
5. Total RTO: ~30-60 minutes

Cost:
- Aurora replica: ~$200/month
- S3 replication: ~$10/month
- Lambda/EventBridge: ~$0
- Total DR cost: ~$210/month
```
