# Cost Estimate — Project 10.1: AWS Organizations Multi-Account

## Organizations Service Pricing

| Feature | Cost | Notes |
|---------|------|-------|
| AWS Organizations | **Free** | No charge for the service itself |
| SCPs, Tag Policies, OUs | **Free** | No charge for policy management |
| Consolidated Billing | **Free** | No charge for billing aggregation |
| Member accounts | **Free** | No per-account fee |

**AWS Organizations itself costs nothing.** Charges come from services used within each account.

---

## Free Tier

- AWS Organizations: **Always free**
- Each member account gets its own free tier (12 months for new accounts)
- This means 10 accounts = 10× free tier limits across the organization

---

## Actual Costs Come From: Individual Services Per Account

| Account Type | Typical Monthly Cost | Services Running |
|-------------|---------------------|-----------------|
| Management | ~$5-20 | Organizations, Billing, minimal EC2 |
| Security | ~$15-50 | GuardDuty, Security Hub, Config |
| Log Archive | ~$5-20 | S3 (log storage), CloudTrail |
| Dev | ~$20-100 | EC2, RDS, Lambda (dev workloads) |
| Staging | ~$50-200 | Full stack staging environment |
| Prod | ~$100-1000+ | Full production workloads |
| Sandbox | ~$10-50 | Experiments, limited by SCP |

### Example Organization Monthly Cost
| Account | Estimated Cost |
|---------|---------------|
| Management | $10 |
| Security | $30 |
| Log Archive | $15 |
| Dev | $50 |
| Staging | $100 |
| Prod | $300 |
| Sandbox | $20 |
| **Total** | **~$525/month** |

---

## Consolidated Billing Benefits

AWS consolidates all accounts into a single bill and pools usage for volume discounts:

| Service | Tier Pricing | Benefit |
|---------|-------------|---------|
| S3 | First 50 TB at $0.023/GB, then $0.022/GB | Multiple accounts combined |
| Data Transfer | 1 GB/month free per service, then tiered | Pooled across accounts |
| Reserved Instances | Shared across accounts in same org | Dev can use prod RIs during off-hours |
| Savings Plans | Shared across org | Maximize coverage |

**Example saving:** 5 accounts each with 20 TB S3 = 100 TB total
- Without org: 5 × (20 TB × $0.023) = $2,300
- With org: 50 TB × $0.023 + 50 TB × $0.022 = $1,150 + $1,100 = $2,250 (~2% saving)

---

## Cost Allocation Setup

```bash
# Enable Cost Allocation Tags for per-account/per-project tracking
aws ce create-cost-category-definition \
  --name "AccountType" \
  --rules '[
    {"Value": "Production", "Rule": {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": ["PROD_ACCOUNT_ID"]}}},
    {"Value": "Development", "Rule": {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": ["DEV_ACCOUNT_ID"]}}},
    {"Value": "Staging", "Rule": {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": ["STAGING_ACCOUNT_ID"]}}}
  ]' \
  --rule-version "CostCategoryExpression.v1"
```

---

## Total

| Scenario | Monthly | Notes |
|----------|---------|-------|
| Organizations service alone | **$0** | Always free |
| Minimal (3 accounts, light usage) | ~$50-100 | Per services used |
| Medium (7 accounts, dev+prod) | ~$500-1000 | Per services used |
| Enterprise (20+ accounts) | $5,000+ | Scales with workloads |

**Cost savings from multi-account:**
- Volume discounts via consolidated billing
- Sandbox SCP prevents expensive service usage
- Better visibility enables optimization
- Reserved Instance sharing across accounts

---

## Cleanup

```bash
# Must follow this order (can't delete org with active accounts)

# Step 1: Remove all member accounts
# Must close accounts via Billing console first (takes 90 days for full closure)
# Or: aws organizations remove-account-from-organization for non-master accounts

# Step 2: Detach all policies from OUs and accounts
aws organizations detach-policy --policy-id $PROD_SCP --target-id $PROD_OU
aws organizations detach-policy --policy-id $SANDBOX_SCP --target-id $SANDBOX_OU
aws organizations detach-policy --policy-id $TAG_POLICY_ID --target-id $ROOT_ID

# Step 3: Delete policies
aws organizations list-policies --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[?Name!=`FullAWSAccess`].Id' --output text | \
  xargs -n1 aws organizations delete-policy --policy-id

# Step 4: Delete OUs (must be empty — no accounts, no child OUs)
for OU_ID in $DEV_OU $STAGING_OU $PROD_OU; do
  aws organizations delete-organizational-unit --organizational-unit-id $OU_ID
done
aws organizations delete-organizational-unit --organizational-unit-id $WORKLOADS_OU

# Step 5: Delete organization (all member accounts removed first)
aws organizations delete-organization

echo "Organizations cleanup complete"
echo "Note: AWS Organizations is free so cleanup is about reducing operational complexity"
```

**Cost note:** Since Organizations is free, cleanup is mainly about governance/complexity, not cost savings. Close member accounts if they have running resources.
