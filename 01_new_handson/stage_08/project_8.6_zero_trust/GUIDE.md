# Project 8.6 — Zero Trust on AWS
## VPC Endpoints, PrivateLink, SCPs, IAM Permission Boundaries — No Public Internet

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `ec2:*`, `organizations:*`, `iam:*`
- [ ] VPC exists with private subnets: `aws ec2 describe-vpcs`
- [ ] AWS Organizations enabled (for SCPs)
- [ ] Region: `us-east-1`
- [ ] Security groups for endpoints

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=false" \
  --query 'Vpcs[0].VpcId' --output text)
echo "VPC: $VPC_ID"
```

---

## Decision Point 1

**VPC Endpoint vs NAT Gateway vs Public Internet — how should private resources reach AWS services?**

| Option | Cost | Security | Latency |
|--------|------|----------|---------|
| **VPC Gateway Endpoint (S3, DynamoDB)** ✅ | **Free** | ✅ Traffic never leaves AWS | Low |
| **VPC Interface Endpoint (other services)** ✅ | $0.01/AZ/hr + $0.01/GB | ✅ Private IP, no internet | Low |
| **NAT Gateway** | $0.045/hr + $0.045/GB | ❌ Internet-routable | Low |
| **Public Internet (IGW)** | $0.09/GB egress | ❌ Exposed | Low |

**NAT Gateway math:** $0.045/hr × 730 hrs = **$32.85/month** just for NAT.
Interface endpoint: $0.01 × 2 AZs × 730 hrs = **$14.60/month** — cheaper + more secure.

**Zero Trust principle:** Never trust the network. Always verify identity + encrypt in transit.

**Verdict:**
- S3, DynamoDB: Gateway endpoints (free)
- Secrets Manager, SSM, ECR, STS: Interface endpoints
- No NAT Gateway for private workloads

---

## 1. Architecture Overview

```
Private Subnet (no IGW, no NAT)
├── EC2 / ECS / Lambda
│   │
│   ├── → S3 via Gateway Endpoint (free, no data transfer cost)
│   ├── → DynamoDB via Gateway Endpoint (free)
│   ├── → Secrets Manager via Interface Endpoint (PrivateLink)
│   ├── → SSM Parameter Store via Interface Endpoint
│   └── → STS / IAM via Interface Endpoint
│
├── IAM Role with Permission Boundary
│   └── Max permissions: read S3 bucket only, no other services
│
└── SCP at Organization Level
    └── Deny: resources outside us-east-1
    └── Deny: disable CloudTrail
    └── Deny: leave organization

No Internet Gateway → No public IPs → Truly private
```

---

## 2. Create Gateway Endpoints (S3 and DynamoDB — Free)

```bash
# Get route table IDs for private subnets
ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[?!Associations[0].Main].RouteTableId' \
  --output text | tr '\t' ',')

# Create S3 Gateway Endpoint
S3_ENDPOINT_ID=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids $ROUTE_TABLE_IDS \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::myapp-*",
        "arn:aws:s3:::myapp-*/*"
      ]
    }]
  }' \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "S3 Gateway Endpoint: $S3_ENDPOINT_ID"

# Create DynamoDB Gateway Endpoint
DYNAMO_ENDPOINT_ID=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids $ROUTE_TABLE_IDS \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "DynamoDB Gateway Endpoint: $DYNAMO_ENDPOINT_ID"
```

---

## 3. Create Interface Endpoints (Secrets Manager, SSM, STS)

```bash
# Get private subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Type,Values=private" \
  --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

# Create Security Group for endpoints
ENDPOINT_SG=$(aws ec2 create-security-group \
  --group-name "vpc-endpoints-sg" \
  --description "Security group for VPC interface endpoints" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow HTTPS from VPC CIDR only
VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID \
  --query 'Vpcs[0].CidrBlock' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ENDPOINT_SG \
  --protocol tcp --port 443 \
  --cidr $VPC_CIDR

# Create Secrets Manager Interface Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

# Create SSM Interface Endpoint (required for Systems Manager)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.ssm \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

# SSM messages (for Session Manager)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.ssmmessages \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

# STS (for IAM role assumption)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

# ECR (if using containers)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_IDS \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

echo "All interface endpoints created"
```

---

## 4. Create IAM Permission Boundary

```bash
# Create permission boundary policy (max permissions any role can have)
cat > /tmp/permission-boundary.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCoreServices",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "secretsmanager:GetSecretValue",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "xray:PutTraceSegments"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyElevatedPrivileges",
      "Effect": "Deny",
      "Action": [
        "iam:CreateUser",
        "iam:DeleteUser",
        "iam:AttachUserPolicy",
        "iam:CreateRole",
        "organizations:*",
        "account:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyOutsideRegion",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
EOF

BOUNDARY_ARN=$(aws iam create-policy \
  --policy-name "AppPermissionBoundary" \
  --policy-document file:///tmp/permission-boundary.json \
  --description "Maximum permissions boundary for application roles" \
  --query 'Policy.Arn' \
  --output text)

echo "Permission Boundary ARN: $BOUNDARY_ARN"

# Attach boundary when creating a role
aws iam create-role \
  --role-name "myapp-ec2-role" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --permissions-boundary "$BOUNDARY_ARN" \
  --description "EC2 role with permission boundary enforced"
```

---

## 5A. Console: Create VPC Endpoint for S3

1. Navigate to **VPC** → **Endpoints** → **Create endpoint**
2. **Name**: `s3-gateway-endpoint`
3. **Service category**: AWS services
4. **Search**: `s3` → select `com.amazonaws.us-east-1.s3` (Type: Gateway)
5. **VPC**: Select your private VPC
6. **Route tables**: Select private subnet route tables
7. **Policy**: Full access or paste custom policy
8. Click **Create endpoint**

For interface endpoints (Secrets Manager, SSM):
- Same process, but **Type: Interface**
- Select subnets and security group
- Enable **Private DNS name**

---

## 5B. CLI: Create SCP to Deny Non-Approved Regions

```bash
# Requires AWS Organizations access (management account)
cat > /tmp/scp-region-restriction.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "route53:*",
        "budgets:*",
        "waf:*",
        "cloudfront:*",
        "sts:*",
        "support:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2"
          ]
        }
      }
    },
    {
      "Sid": "DenyDisableCloudTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "cloudtrail:UpdateTrail"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyLeaveOrganization",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    }
  ]
}
EOF

# Create SCP
SCP_ID=$(aws organizations create-policy \
  --content file:///tmp/scp-region-restriction.json \
  --description "Restrict resources to approved regions, prevent security control disabling" \
  --name "RegionRestrictionAndSecurityControls" \
  --type SERVICE_CONTROL_POLICY \
  --query 'Policy.PolicySummary.Id' \
  --output text)

echo "SCP ID: $SCP_ID"

# Attach SCP to target OU (replace with your OU ID)
OU_ID="ou-xxxx-xxxxxxxx"  # Get from: aws organizations list-organizational-units-for-parent
aws organizations attach-policy \
  --policy-id $SCP_ID \
  --target-id $OU_ID
```

---

## 6. Remove Default VPC and Public Subnets

```bash
# CAUTION: This removes the default VPC — only do in non-production or new accounts
# List default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs \
  --filters "Name=is-default,Values=true" \
  --query 'Vpcs[0].VpcId' --output text)

if [ "$DEFAULT_VPC" != "None" ]; then
  # Delete default subnets first
  aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" \
    --query 'Subnets[].SubnetId' --output text | \
    xargs -n1 aws ec2 delete-subnet --subnet-id

  # Delete Internet Gateway
  IGW_ID=$(aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=$DEFAULT_VPC" \
    --query 'InternetGateways[0].InternetGatewayId' --output text)
  aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $DEFAULT_VPC
  aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID

  # Delete default VPC
  aws ec2 delete-vpc --vpc-id $DEFAULT_VPC
  echo "Default VPC removed"
fi
```

---

## 7. Verify Endpoints Work (No Internet Needed)

```bash
# Deploy test EC2 in private subnet (no public IP, no NAT)
# From the instance, test that AWS SDK calls work via VPC endpoints:

# Test S3 via gateway endpoint
aws s3 ls --endpoint-url https://s3.us-east-1.amazonaws.com

# Test Secrets Manager via interface endpoint
aws secretsmanager list-secrets --region us-east-1

# Test SSM (Session Manager — no SSH needed)
aws ssm start-session --target i-xxxxxxxxxxxx

# Verify no internet traffic (should fail if endpoints work correctly):
curl --connect-timeout 5 https://example.com || echo "Correctly blocked"
```

---

## 8. Endpoint Policies (Restrict What Endpoints Allow)

```bash
# Restrict S3 endpoint to only access company buckets
ENDPOINT_ID="vpce-xxxx"
LOCK_TOKEN=$(aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids $ENDPOINT_ID \
  --query 'VpcEndpoints[0].PolicyDocument')

aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id $ENDPOINT_ID \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::'"$ACCOUNT_ID"':root"
        },
        "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::myapp-*",
          "arn:aws:s3:::myapp-*/*"
        ]
      }
    ]
  }'
```

---

## 9. Audit Endpoint Usage

```bash
# View VPC endpoints
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[].{Id:VpcEndpointId,Service:ServiceName,State:State,Type:VpcEndpointType}'

# Check VPC Flow Logs to confirm no internet traffic
# Traffic to S3/DynamoDB via gateway endpoint shows pl-xxxxx prefix as destination
aws ec2 describe-prefix-lists \
  --query 'PrefixLists[?contains(PrefixListName,`s3`)].{Name:PrefixListName,Id:PrefixListId}'
```

---

## 10. Verify Zero Trust Setup

```bash
echo "=== Zero Trust Verification ==="

# 1. All required VPC endpoints exist
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
  --query 'VpcEndpoints[].ServiceName' | jq .

# 2. No Internet Gateway attached
aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
  --query 'InternetGateways | length(@)'
# Should return 0 for fully private VPC

# 3. SCP attached
aws organizations list-policies-for-target \
  --target-id $OU_ID \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[].{Name:Name,Id:Id}'

# 4. Permission boundaries on roles
aws iam list-roles \
  --query 'Roles[?PermissionsBoundary!=null].{Name:RoleName,Boundary:PermissionsBoundary.PermissionsBoundaryArn}'

echo "=== Zero Trust Verification Complete ==="
```

---

## Troubleshooting

**SDK calls fail from private subnet:**
```bash
# Check endpoint exists and is available
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.secretsmanager"
# If missing — create the interface endpoint
```

**Private DNS not resolving endpoint:**
```bash
# Verify DNS settings in VPC
aws ec2 describe-vpc-attribute --vpc-id $VPC_ID \
  --attribute enableDnsHostnames
aws ec2 describe-vpc-attribute --vpc-id $VPC_ID \
  --attribute enableDnsSupport
# Both must be true for private DNS to work
```

**SCP blocking legitimate actions:**
```bash
# Test which SCP is causing the deny
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::$ACCOUNT_ID:role/myapp-role" \
  --action-names s3:ListBucket \
  --resource-arns "arn:aws:s3:::myapp-bucket"
```

---

## Expected Outcome

- ✅ S3 and DynamoDB accessible via free gateway endpoints
- ✅ Secrets Manager, SSM, STS via interface endpoints (PrivateLink)
- ✅ No NAT Gateway needed — saves $32+/month
- ✅ SCP denying resources in non-approved regions
- ✅ SCP preventing CloudTrail disabling
- ✅ IAM permission boundaries capping role privileges
- ✅ No Internet Gateway — truly private network

---

## Cleanup

```bash
# List all endpoints in VPC
ENDPOINT_IDS=$(aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[].VpcEndpointId' --output text)

# Delete all VPC endpoints
aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $ENDPOINT_IDS

# Delete endpoint security group
aws ec2 delete-security-group --group-id $ENDPOINT_SG

# Detach and delete SCP
aws organizations detach-policy --policy-id $SCP_ID --target-id $OU_ID
aws organizations delete-policy --policy-id $SCP_ID

# Delete permission boundary policy
aws iam delete-policy --policy-arn "$BOUNDARY_ARN"

echo "Zero Trust cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
