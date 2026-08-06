# Project 8.6 — Zero Trust on AWS: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] IAM permissions: `ec2:CreateVpcEndpoint`, `organizations:CreatePolicy`, `iam:CreatePolicy`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] VPC with private subnets exists
- [ ] AWS Organizations access (management account) for SCPs

---

## Step 1 — Navigate to VPC Endpoints

1. Sign in to **AWS Management Console**
2. Search for **VPC** in the search bar
3. Click **VPC** service
4. In left nav under **Virtual private cloud**: click **Endpoints**
5. You see a list of existing endpoints (likely empty for new accounts)

📸 Screenshot: VPC Endpoints list page showing empty state

**Decision Point: Gateway vs Interface Endpoints?**
- **Gateway** (S3, DynamoDB): Free, adds route to route table, high throughput
- **Interface** (all others): $0.01/AZ/hr, creates private DNS, works for 100+ services

---

## Step 2 — Create S3 Gateway Endpoint (Free)

1. Click **Create endpoint** (orange button)
2. **Name tag**: `s3-gateway-endpoint`
3. **Service category**: `AWS services`
4. **Search**: type `s3`
5. Select `com.amazonaws.us-east-1.s3`
   - Type should show: **Gateway** (not Interface)
6. **VPC**: Select your private VPC from the dropdown
7. **Route tables**: Check all private subnet route tables
   - This adds a route: `pl-xxxxx (S3 prefix list) → vpce-xxxx`
8. **Policy**: Full Access (or customize)
9. Click **Create endpoint**

📸 Screenshot: S3 endpoint creation with Gateway type highlighted and route tables selected

---

## Step 3 — Create DynamoDB Gateway Endpoint (Free)

1. Click **Create endpoint**
2. **Name tag**: `dynamodb-gateway-endpoint`
3. **Service category**: `AWS services`
4. **Search**: type `dynamodb`
5. Select `com.amazonaws.us-east-1.dynamodb` → **Type: Gateway**
6. **VPC**: Same private VPC
7. **Route tables**: Same private subnet route tables
8. **Policy**: Full Access
9. Click **Create endpoint**

📸 Screenshot: DynamoDB gateway endpoint with route table association

---

## Step 4 — Create Secrets Manager Interface Endpoint

1. Click **Create endpoint**
2. **Name tag**: `secretsmanager-interface-endpoint`
3. **Service category**: `AWS services`
4. **Search**: type `secretsmanager`
5. Select `com.amazonaws.us-east-1.secretsmanager` → **Type: Interface**
6. **VPC**: Your private VPC
7. **Subnets**: Select private subnets in each AZ (select all AZs for HA)
8. **IP address type**: IPv4
9. **Security groups**: Select or create `vpc-endpoints-sg`
   - Rule: Allow TCP 443 from VPC CIDR
10. **Private DNS name**: ✅ Enable
    - This makes `secretsmanager.us-east-1.amazonaws.com` resolve to private IP
11. **Policy**: Full Access
12. Click **Create endpoint**

📸 Screenshot: Secrets Manager interface endpoint creation with Private DNS enabled

**Troubleshooting — Private DNS not working:**
- VPC must have "DNS hostnames" and "DNS support" enabled
- VPC → Select VPC → Actions → Edit VPC settings → Enable both

---

## Step 5 — Create Additional Interface Endpoints

Repeat Step 4 for each service (one at a time or use CLI from GUIDE.md):

| Service Name | Search Term |
|-------------|------------|
| SSM Agent | `com.amazonaws.us-east-1.ssm` |
| SSM Messages | `com.amazonaws.us-east-1.ssmmessages` |
| EC2 Messages | `com.amazonaws.us-east-1.ec2messages` |
| STS | `com.amazonaws.us-east-1.sts` |
| ECR API | `com.amazonaws.us-east-1.ecr.api` |
| ECR Docker | `com.amazonaws.us-east-1.ecr.dkr` |
| CloudWatch Logs | `com.amazonaws.us-east-1.logs` |

📸 Screenshot: Endpoints list showing all created endpoints with "Available" status

---

## Step 6 — Verify Endpoints Created

1. In **VPC** → **Endpoints**
2. You should see all endpoints with **Status: Available**
3. Click on the S3 gateway endpoint:
   - **Route tables** tab shows which route tables have the S3 route added
   - **Policy** tab shows the endpoint access policy
4. Click on Secrets Manager interface endpoint:
   - **Subnets** tab shows private IP assigned in each AZ
   - **DNS names** tab shows the private DNS entries

📸 Screenshot: Endpoint detail page showing DNS names tab with private IP addresses

---

## Step 7 — Create SCP via AWS Organizations

1. Search for **AWS Organizations**
2. Navigate to **Organizations** → **Policies** → **Service control policies**
3. If SCPs not enabled: Click **Enable service control policies**
4. Click **Create policy**
5. **Policy name**: `RegionRestrictionAndSecurityControls`
6. In the policy editor, paste the SCP JSON from GUIDE.md section 5B
7. Click **Create policy**
8. Navigate to **AWS accounts** or **Organizational units**
9. Select target OU (e.g., `dev` OU)
10. Click **Attach policy** → select your new SCP

📸 Screenshot: SCP policy editor with region restriction JSON

**Decision Point: Attach SCP to OU or individual account?**
- **OU** = affects all accounts in OU and child OUs (recommended for consistency)
- **Account** = granular control per account
- Never attach to Root OU (affects management account too)

---

## Step 8 — Create IAM Permission Boundary

1. Navigate to **IAM** → **Policies**
2. Click **Create policy**
3. Select **JSON** tab
4. Paste the permission boundary JSON from GUIDE.md section 4
5. Click **Next** → **Policy name**: `AppPermissionBoundary`
6. Click **Create policy**
7. Note the Policy ARN

**Apply to existing roles:**
1. Navigate to **IAM** → **Roles**
2. Click on a role → **Permissions** tab
3. Click **Set permissions boundary** → Select `AppPermissionBoundary`

📸 Screenshot: IAM role permissions tab showing "Permissions boundary" section

---

## Step 9 — Remove NAT Gateway (If Exists)

1. Navigate to **VPC** → **NAT gateways**
2. If you have NAT Gateways: verify your workloads now use VPC endpoints instead
3. Test from private EC2: `aws s3 ls` should work via endpoint
4. If confirmed working, select NAT Gateway → **Actions** → **Delete NAT gateway**
5. Also release Elastic IPs: **VPC** → **Elastic IPs** → **Release**

📸 Screenshot: NAT Gateways list with Delete option

---

## Step 10 — Verify Zero Trust Architecture

1. **VPC** → **Endpoints**: All show **Available** status
2. **VPC** → **Route tables**: Private route tables have S3/DynamoDB prefix list routes
3. **Organizations** → **Policies**: SCP attached to target OU
4. **IAM** → **Roles**: Key roles have permission boundary set
5. Test connectivity from private EC2 (via Session Manager — no SSH):
   - `aws s3 ls` → works via gateway endpoint
   - `curl https://example.com` → fails (no internet access) ✅

📸 Screenshot: VPC route table showing S3 prefix list route pointing to gateway endpoint

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| SDK calls fail from private EC2 | Missing interface endpoint | Create endpoint for that service |
| S3 endpoint not working | Route not added | Check route table association in endpoint detail |
| DNS not resolving to private IP | DNS settings off | Enable DNS hostnames + DNS support on VPC |
| SCP blocking all actions | SCP too broad | Review NotAction list, ensure IAM and STS are excluded |
| Permission boundary blocks everything | Too restrictive | Review boundary policy, ensure needed services are allowed |

---

## Console Navigation Quick Reference

```
AWS VPC
├── Endpoints
│   ├── Create endpoint      → Add new S3/Secrets Manager/etc.
│   ├── [Endpoint] → Details → Route tables, DNS names, Policy
│   └── Modify endpoint      → Update policy, subnets
│
AWS Organizations
├── AWS accounts             → Account structure
├── Policies → SCPs          → Create/attach/detach
└── Organizational units     → OU structure + policy attachments
│
AWS IAM
├── Policies                 → Create permission boundary
└── Roles → [Role] → Permissions boundary → Set/remove
```
