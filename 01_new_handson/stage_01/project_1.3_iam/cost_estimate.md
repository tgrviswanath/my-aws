# Cost Estimate — IAM Security Fundamentals

> **IAM is completely free** — no charge for any IAM feature.

---

## Free Tier

IAM has no free tier limit because it is **always free with no usage caps**.

| Resource | Cost | Notes |
|----------|------|-------|
| IAM users | $0.00 | Unlimited users |
| IAM groups | $0.00 | Unlimited groups |
| IAM roles | $0.00 | Unlimited roles |
| IAM policies | $0.00 | Up to 10 managed policies per user/group/role |
| Customer managed policies | $0.00 | Up to 1,500 policies per account |
| MFA devices (virtual) | $0.00 | Unlimited virtual MFA devices |
| MFA devices (hardware) | Physical cost only | AWS provides the token; you buy the physical device (~$20–$60) |
| STS calls (AssumeRole) | $0.00 | Unlimited |
| IAM Access Analyzer | $0.00 | Free for account-level analysis |
| Policy Simulator | $0.00 | Free to use |
| Credential Reports | $0.00 | Free to generate |

---

## Related Costs (Optional)

While IAM itself is free, some features you might use alongside IAM have costs:

| Feature | Cost | Notes |
|---------|------|-------|
| AWS Organizations | Free for management | Consolidated billing, SCPs |
| AWS SSO / IAM Identity Center | Free | Centralized user access management |
| AWS CloudTrail (IAM audit logs) | First trail free in each region | Additional trails: $2.00/100K events |
| AWS Config (compliance) | $0.003/configuration item | For tracking IAM changes over time |

**For this project (IAM only):** Total cost = **$0.00**

---

## Total

| Month | Cost |
|-------|------|
| Month 1 | **$0.00** |
| Month 12 | **$0.00** |
| After 12 months | **$0.00** |
| Lifetime | **$0.00** |

IAM is part of AWS's core infrastructure and is never charged separately.

---

## Cleanup

Even though IAM is free, clean up test resources to maintain a tidy account:

### CLI Cleanup

```bash
# Remove user from group
aws iam remove-user-from-group \
  --user-name dev-user-01 \
  --group-name developers

# Delete user inline policies
aws iam delete-user-policy \
  --user-name dev-user-01 \
  --policy-name AllowAssumeS3ReadRole

# Delete access keys
ACCESS_KEY_ID=$(aws iam list-access-keys \
  --user-name dev-user-01 \
  --query 'AccessKeyMetadata[0].AccessKeyId' --output text)
aws iam delete-access-key \
  --user-name dev-user-01 \
  --access-key-id $ACCESS_KEY_ID

# Delete MFA device
MFA_SERIAL=$(aws iam list-mfa-devices \
  --user-name dev-user-01 \
  --query 'MFADevices[0].SerialNumber' --output text)
aws iam deactivate-mfa-device \
  --user-name dev-user-01 \
  --serial-number $MFA_SERIAL
aws iam delete-virtual-mfa-device --serial-number $MFA_SERIAL

# Delete login profile
aws iam delete-login-profile --user-name dev-user-01

# Delete user
aws iam delete-user --user-name dev-user-01

# Detach group policy and delete group
aws iam detach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam delete-group --group-name developers

# Detach role policies and delete role
aws iam detach-role-policy \
  --role-name s3-read-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name s3-read-role

echo "✅ All IAM resources cleaned up — still $0 cost"
```

### Console Cleanup

1. IAM → Users → `dev-user-01` → Delete user
2. IAM → User groups → `developers` → Delete group
3. IAM → Roles → `s3-read-role` → Delete role

Cleanup cost impact: **$0** (there was nothing to charge for)
