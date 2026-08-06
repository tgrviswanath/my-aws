# Project 8.6 — Zero Trust Security Architecture

**Stage:** 08 | **Level:** Advanced | **Est. Time:** 120 min | **Cost:** ~$0.01/hr per interface endpoint

Implement Zero Trust principles on AWS by eliminating all public internet paths for internal traffic,
enforcing hard region boundaries through Service Control Policies, and constraining IAM permissions
with boundary policies. VPC gateway endpoints route S3 and DynamoDB traffic within the AWS network
at zero cost. Interface endpoints bring SSM, Secrets Manager, and ECR inside the VPC. SCPs in AWS
Organizations block resource creation in every region except us-east-1, and permission boundaries
cap developer roles so privilege escalation is architecturally impossible.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| VPC Gateway Endpoints | Private routing to S3 and DynamoDB — no internet gateway needed | Free |
| VPC Interface Endpoints | Private ENI-based access to SSM, Secrets Manager, ECR | $0.01/hr each (~$7.20/month) |
| AWS Organizations (SCPs) | Deny API calls outside us-east-1 at the organization level | Free |
| AWS IAM (Permission Boundaries) | Hard ceiling on maximum permissions for developer roles | Free |
| Amazon S3 (Block Public Access) | Account-level public access block on all buckets | Free |
| Network ACLs | Stateless subnet-level firewall layered on top of security groups | Free |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| VPC ID | vpc-0abc123def456 | Target VPC for endpoints |
| Gateway endpoint services | com.amazonaws.us-east-1.s3, com.amazonaws.us-east-1.dynamodb | Free endpoints |
| Interface endpoint services | ssm, secretsmanager, ecr.api, ecr.dkr | $0.01/hr each |
| SCP denied regions | All regions except us-east-1 | Applied to OU or account |
| Permission boundary ARN | arn:aws:iam::123456789012:policy/DeveloperBoundary | Attached to developer role |
| S3 block public access | Enabled at account level | All four block settings = true |

### Output

| Artifact | Description |
|---|---|
| S3/DynamoDB traffic | Routes through gateway endpoint — never traverses public internet |
| SSM/Secrets Manager traffic | Routes through interface endpoint ENI inside the VPC subnet |
| SCP enforcement | Any CreateBucket, RunInstances, etc. outside us-east-1 returns AccessDenied |
| Permission boundary | Developer role cannot attach AdministratorAccess even if granted by identity policy |
| S3 public access | All buckets in account have public access blocked; CloudFront OAC still works |
| Network ACLs | Explicit DENY on ports 23 (Telnet) and 20/21 (FTP) at subnet level |

---

## Architecture

```
Developer / EC2 / Lambda (inside VPC)
          |
          | (no internet gateway path for AWS service calls)
          |
     +----+-------------------------------+
     |                                   |
     v                                   v
+------------------+           +--------------------+
| VPC Gateway      |           | VPC Interface      |
| Endpoints        |           | Endpoints (ENI)    |
|                  |           |                    |
| S3 (free)        |           | SSM                |
| DynamoDB (free)  |           | Secrets Manager    |
+------------------+           | ECR API / DKR      |
     |                         +--------------------+
     | stays in AWS network          |
     v                               v
  Amazon S3              AWS Service APIs
  Amazon DynamoDB        (no public internet)

IAM Layer:
  Identity Policy (what is granted)
        ∩
  Permission Boundary (maximum allowed)
  = Effective Permissions

Organization Layer (SCP):
  Deny { NotAction: ... }
  Condition: aws:RequestedRegion != us-east-1
  --> blocks ALL users including account admin
  outside us-east-1

Network Layer:
  Security Groups (stateful)  +  Network ACLs (stateless)
  = defense in depth at instance and subnet levels
```

---

## Quick Start

```cmd
REM 1. Create S3 and DynamoDB gateway endpoints (free)
aws ec2 create-vpc-endpoint ^
  --vpc-id vpc-0abc123def456 ^
  --service-name com.amazonaws.us-east-1.s3 ^
  --vpc-endpoint-type Gateway --route-table-ids rtb-0123456789abcdef0

aws ec2 create-vpc-endpoint ^
  --vpc-id vpc-0abc123def456 ^
  --service-name com.amazonaws.us-east-1.dynamodb ^
  --vpc-endpoint-type Gateway --route-table-ids rtb-0123456789abcdef0

REM 2. Create SSM and Secrets Manager interface endpoints ($0.01/hr each)
aws ec2 create-vpc-endpoint ^
  --vpc-id vpc-0abc123def456 ^
  --service-name com.amazonaws.us-east-1.ssm ^
  --vpc-endpoint-type Interface --subnet-ids subnet-0abc123 ^
  --security-group-ids sg-0abc123 --private-dns-enabled

aws ec2 create-vpc-endpoint ^
  --vpc-id vpc-0abc123def456 ^
  --service-name com.amazonaws.us-east-1.secretsmanager ^
  --vpc-endpoint-type Interface --subnet-ids subnet-0abc123 ^
  --security-group-ids sg-0abc123 --private-dns-enabled

REM 3. Block all S3 public access at account level
aws s3control put-public-access-block ^
  --account-id 123456789012 ^
  --public-access-block-configuration ^
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

REM 4. Create and attach SCP restricting all activity to us-east-1
aws organizations create-policy ^
  --name DenyNonUSEast1 --type SERVICE_CONTROL_POLICY ^
  --content file://scp-deny-non-us-east1.json

REM 5. Create permission boundary and attach to developer role
aws iam create-policy ^
  --policy-name DeveloperBoundary --policy-document file://developer-boundary.json
aws iam put-role-permissions-boundary ^
  --role-name developer-role ^
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary
```

---

## Data Flow

1. EC2 or Lambda calls `s3.put_object()` — the request resolves to the gateway endpoint route in the VPC route table and never leaves the AWS network.
2. Lambda calls `secretsmanager.get_secret_value()` — DNS resolves to the interface endpoint ENI private IP inside the VPC; traffic stays within the VPC subnet.
3. Developer runs `aws ec2 run-instances --region eu-west-1` — the SCP `DenyNonUSEast1` evaluates before IAM and returns `AccessDenied`.
4. Developer role attempts to attach `AdministratorAccess` — the permission boundary does not include `iam:AttachRolePolicy`, so the action is denied even if the identity policy would allow it.
5. A script sets an S3 bucket ACL to public-read — the account-level S3 Block Public Access rejects it regardless of the bucket policy.
6. Inbound traffic hits a subnet on port 23 — the Network ACL DENY rule fires before the security group is evaluated.
7. CloudFront fetches objects from a private S3 bucket via OAC signed requests — OAC uses IAM auth, not public ACLs, so Block Public Access does not interfere.

---

## Project Files

| File | Description |
|---|---|
| `scp-deny-non-us-east1.json` | SCP policy denying all actions with RequestedRegion != us-east-1 |
| `developer-boundary.json` | Permission boundary policy: S3, DynamoDB, Lambda read/write only |
| `endpoint-security-group.json` | Security group allowing port 443 inbound from VPC CIDR to interface endpoints |
| `nacl-rules.json` | Network ACL rules: deny Telnet (23), FTP (20/21), allow 443/80 |
| `verify_no_public_route.sh` | CLI checks confirming S3 and DynamoDB calls route through endpoints |
| `test_scp_enforcement.sh` | Commands demonstrating AccessDenied for eu-west-1 API calls under SCP |

---

## Lessons Learned

- Gateway VPC endpoints for S3 and DynamoDB are free — they add a route to the VPC route table so all S3/DynamoDB traffic stays within the AWS backbone with no data transfer charge.
- Interface VPC endpoints for SSM, Secrets Manager, and ECR cost $0.01/hr each ($7.20/month per endpoint per AZ) — create them only in subnets that need private API access to avoid unnecessary spend.
- SCPs are guardrails, not grants — they restrict what even the account root user and administrators can do; they do not grant any permissions on their own.
- A permission boundary is a maximum permission ceiling: the effective permissions of a role are the intersection of the identity policy and the boundary — a boundary alone grants nothing.
- Zero Trust means verify explicitly (every request authenticated and authorized), use least privilege (permission boundaries + SCPs enforce the ceiling), and assume breach (GuardDuty + CloudTrail for detection).
- Removing S3 public access at the account level using `put-public-access-block` does not break CloudFront OAC (Origin Access Control) — OAC uses signed AWS IAM requests, which bypass public-access restrictions entirely.
- Network ACLs are stateless and evaluated before security groups at the subnet boundary — layering both provides defense-in-depth so a misconfigured security group does not expose the subnet.
