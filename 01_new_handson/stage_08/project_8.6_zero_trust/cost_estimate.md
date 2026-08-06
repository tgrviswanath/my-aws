# Cost Estimate — Project 8.6: Zero Trust (VPC Endpoints + PrivateLink)

## VPC Endpoint Pricing (us-east-1)

| Endpoint Type | Services | Hourly | Data Transfer | Notes |
|--------------|---------|--------|--------------|-------|
| **Gateway Endpoint** | S3, DynamoDB | **Free** | **Free** | No hourly or data charges |
| **Interface Endpoint** | All others | $0.01/AZ/hour | $0.01/GB | Per endpoint per AZ |

## SCP and IAM Pricing

| Service | Cost | Notes |
|---------|------|-------|
| AWS Organizations (SCPs) | **Free** | Organizations service is free |
| IAM (permission boundaries) | **Free** | IAM has no cost |

---

## Free Tier

- Gateway endpoints (S3, DynamoDB): **Always free** — no time limit
- AWS Organizations: **Always free**
- IAM: **Always free**
- Interface endpoints: **No free tier** — charges start immediately

---

## Interface Endpoint Cost Breakdown

Each interface endpoint costs:
- Hourly: $0.01/AZ × 730 hours/month = **$7.30/AZ/month**
- Data: $0.01/GB processed

For high availability (2 AZs): **$14.60/endpoint/month**

### Comparison: Interface Endpoints vs NAT Gateway

| Setup | Monthly Cost | Security |
|-------|-------------|---------|
| NAT Gateway (1 AZ) | $32.85/month base + $0.045/GB | ❌ Internet-routable |
| Interface Endpoints (5 services × 2 AZs) | $73/month | ✅ Private only |
| Interface Endpoints (5 services × 1 AZ) | $36.50/month | ✅ Private (single AZ) |
| Gateway Endpoints only (S3+DynamoDB) | **$0** | ✅ Private |

**At high data volumes (>1 TB/month):**
- NAT Gateway data: $45/TB
- Interface endpoint data: $10/TB
- Interface endpoints win at scale

---

## Scenario Estimates

### Minimal Zero Trust (Gateway endpoints only)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| S3 Gateway Endpoint | 1 | $0.00 |
| DynamoDB Gateway Endpoint | 1 | $0.00 |
| SCP (Organizations) | 1 | $0.00 |
| IAM Permission Boundaries | Any | $0.00 |
| **Total** | | **$0.00/month** |

### Standard Zero Trust (+ Secrets Manager, SSM, STS)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| S3 Gateway Endpoint | 1 | $0.00 |
| DynamoDB Gateway Endpoint | 1 | $0.00 |
| Secrets Manager Interface (2 AZs) | 2 | $14.60 |
| SSM Interface (2 AZs) | 2 | $14.60 |
| SSM Messages Interface (2 AZs) | 2 | $14.60 |
| STS Interface (2 AZs) | 2 | $14.60 |
| Data transfer (10 GB/month) | 10 GB | $0.10 |
| **Total** | | **~$58.50/month** |

### Full Zero Trust (All interfaces, ECR, CloudWatch, ECS)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| S3 + DynamoDB Gateway | 2 | $0.00 |
| Interface Endpoints × 8 services (2 AZs) | 16 | $116.80 |
| Data transfer (100 GB/month) | 100 GB | $1.00 |
| NAT Gateway removed (savings) | -1 | -$32.85 |
| **Net Total** | | **~$85/month** |

---

## Cost vs NAT Gateway Analysis

```
Without Zero Trust (NAT Gateway):
  NAT: $32.85/month + $45/TB data
  Security: ❌ Internet exposure

With Zero Trust (Interface Endpoints, 8 services, 2 AZs):
  Endpoints: $116.80/month + $10/TB data
  Security: ✅ Fully private

Break-even point for data transfer:
  NAT data cost = $0.045/GB
  Endpoint data cost = $0.01/GB
  Savings per GB = $0.035/GB
  Fixed cost difference = $116.80 - $32.85 = $83.95/month
  Break-even data volume = $83.95 / $0.035 = ~2.4 TB/month

At >2.4 TB/month data transfer, endpoints are cheaper + more secure.
```

---

## Total

| Scenario | Monthly | Annual |
|----------|---------|--------|
| Minimal (gateway only) | **$0** | **$0** |
| Standard (4 interface endpoints, 2 AZs) | ~$58.50 | ~$702 |
| Full (8 interface endpoints, 2 AZs, minus NAT) | ~$85 | ~$1,020 |

**For learning:** Use 1 AZ for endpoints to halve the cost.
**For production:** Always use 2+ AZs for high availability.

---

## Cleanup

```bash
# Get all VPC endpoints in the VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=my-vpc" \
  --query 'Vpcs[0].VpcId' --output text)

ENDPOINT_IDS=$(aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
  --query 'VpcEndpoints[].VpcEndpointId' \
  --output text)

# Delete all endpoints (billing stops immediately)
if [ -n "$ENDPOINT_IDS" ]; then
  aws ec2 delete-vpc-endpoints \
    --vpc-endpoint-ids $ENDPOINT_IDS
  echo "Deleted endpoints: $ENDPOINT_IDS"
fi

# Delete endpoint security group
ENDPOINT_SG=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=vpc-endpoints-sg" \
  --query 'SecurityGroups[0].GroupId' --output text)
aws ec2 delete-security-group --group-id $ENDPOINT_SG

# SCP cleanup
SCP_ID=$(aws organizations list-policies --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[?Name==`RegionRestrictionAndSecurityControls`].Id' --output text)
OU_ID="ou-xxxx-xxxxxxxx"
aws organizations detach-policy --policy-id $SCP_ID --target-id $OU_ID
aws organizations delete-policy --policy-id $SCP_ID

# IAM permission boundary
BOUNDARY_ARN=$(aws iam list-policies --scope Local \
  --query 'Policies[?PolicyName==`AppPermissionBoundary`].Arn' --output text)
aws iam delete-policy --policy-arn "$BOUNDARY_ARN"

echo "Zero Trust cleanup complete — billing stops within 1 hour"
```

**Cost saving note:** Interface endpoints stop billing within 1 hour of deletion. Gateway endpoints (S3, DynamoDB) are free so no billing to stop.
