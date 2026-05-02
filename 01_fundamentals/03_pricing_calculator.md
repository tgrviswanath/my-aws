# AWS Pricing — Calculator, Models & Cost Estimation

## Common Service Pricing (Approximate, us-east-1, 2024)

### Compute
```
EC2 Instances (Linux, On-Demand):
  t3.micro  (2 vCPU, 1GB):   ~$0.0104/hr  (~$7.59/mo)
  t3.small  (2 vCPU, 2GB):   ~$0.0208/hr  (~$15.18/mo)
  t3.medium (2 vCPU, 4GB):   ~$0.0416/hr  (~$30.37/mo)
  m5.large  (2 vCPU, 8GB):   ~$0.096/hr   (~$70.08/mo)
  m5.xlarge (4 vCPU, 16GB):  ~$0.192/hr   (~$140.16/mo)

Lambda:
  First 1M requests/month: FREE
  Additional: $0.20 per million requests
  Compute: $0.0000166667 per GB-second
```

### Storage
```
S3 Standard:          $0.023/GB/month
S3 Standard-IA:       $0.0125/GB/month
S3 Glacier Instant:   $0.004/GB/month
S3 Glacier Flexible:  $0.0036/GB/month
S3 Glacier Deep:      $0.00099/GB/month

EBS gp3:              $0.08/GB/month
EBS io2:              $0.125/GB/month + $0.065/IOPS
```

### Databases
```
RDS MySQL db.t3.micro:    ~$0.017/hr  (~$12.41/mo)
RDS MySQL db.m5.large:    ~$0.171/hr  (~$124.83/mo)
Aurora MySQL (per ACU):   ~$0.06/hr
DynamoDB On-Demand:       $1.25 per million write RCUs
                          $0.25 per million read RCUs
ElastiCache cache.t3.micro: ~$0.017/hr
```

### Networking
```
Data Transfer OUT (first 100GB/mo): $0.09/GB
Data Transfer OUT (next 9.9TB):     $0.085/GB
CloudFront (first 10TB/mo):         $0.0085/GB
VPN Connection:                     $0.05/hr
NAT Gateway:                        $0.045/hr + $0.045/GB
```

## Cost Estimation Examples

### Small Web App (Dev/Test)
```
EC2 t3.micro (1 instance):    $7.59/month
RDS db.t3.micro:              $12.41/month
S3 (10GB):                    $0.23/month
Data transfer (10GB):         $0.90/month
Total:                        ~$21/month
```

### Medium Production Web App
```
EC2 m5.large (2 instances):   $140/month
RDS db.m5.large Multi-AZ:     $250/month
ElastiCache cache.t3.medium:  $50/month
ALB:                          $20/month
S3 (100GB):                   $2.30/month
CloudFront (1TB):             $85/month
Total:                        ~$547/month
With Reserved Instances (1yr): ~$350/month
```

## Cost Optimization Tools

```bash
# AWS Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# AWS Budgets
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json

# Trusted Advisor (cost checks)
aws support describe-trusted-advisor-checks --language en
aws support describe-trusted-advisor-check-result \
  --check-id Qch7DwouX1  # Low utilization EC2 instances
```

## Interview Questions

### Q1: How do you reduce AWS costs for a predictable workload?
1. **Reserved Instances**: 1-year = ~40% savings, 3-year = ~60-72%
2. **Savings Plans**: Commit to $/hour, flexible instance family
3. **Right-sizing**: Use AWS Compute Optimizer recommendations
4. **Auto Scaling**: Scale down during off-peak hours
5. **S3 Lifecycle policies**: Move data to cheaper storage tiers
6. **Spot Instances**: For fault-tolerant batch workloads

### Q2: What is the difference between Reserved Instances and Savings Plans?
- **Reserved Instances**: Commit to specific instance type, region, OS. Up to 72% savings.
- **Savings Plans**: Commit to $/hour spend. Applies to any instance family/region/OS. More flexible. Up to 66% savings.
Use RI for: stable, predictable workloads with known configuration.
Use Savings Plans for: variable workloads, multiple regions, mixed instance types.
