# Architecture — Project 2.5 Failure Simulation Lab

## Failure Points Map

```
Internet
    │
    ▼
Route53 ──────────────────────────────── FAILURE: wrong DNS record
    │
    ▼
CloudFront ────────────────────────────── FAILURE: origin unreachable
    │
    ▼
ALB ───────────────────────────────────── FAILURE: SG blocks port 80
    │
    ▼
EC2 (Auto Scaling Group) ──────────────── FAILURE: instance terminated
    │                                               SG blocks SSH
    │                                               disk full
    ▼
NAT Gateway ───────────────────────────── FAILURE: route deleted
    │                                               NAT deleted
    ▼
RDS MySQL ─────────────────────────────── FAILURE: SG blocks 3306
    │                                               wrong endpoint
    ▼
S3 / Other AWS Services ───────────────── FAILURE: IAM permission denied
```

## Diagnosis Decision Tree

```
App not responding?
  │
  ├── Can you reach the ALB DNS?
  │     NO  → Check Route53 records, CloudFront origin
  │     YES → Continue
  │
  ├── Is ALB showing healthy targets?
  │     NO  → Check EC2 security group (port 80 from ALB SG)
  │           Check EC2 instance state (running?)
  │           Check health check path (/health returns 200?)
  │     YES → Continue
  │
  ├── Can EC2 reach RDS?
  │     NO  → Check RDS security group (port 3306 from app SG)
  │           Check RDS subnet group (same VPC?)
  │           Check RDS endpoint in app config
  │     YES → Continue
  │
  └── Can EC2 reach internet?
        NO  → Check route table (0.0.0.0/0 → NAT GW)
              Check NAT Gateway status (available?)
              Check Elastic IP attached to NAT
        YES → Check application logs
```

## VPC Flow Log Format

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status

Example REJECT entry:
2 123456789 eni-abc123 10.0.3.5 10.0.5.10 54321 3306 6 1 40 1620000000 1620000060 REJECT OK
                                                              ^^^^
                                                         Port 3306 blocked
```
