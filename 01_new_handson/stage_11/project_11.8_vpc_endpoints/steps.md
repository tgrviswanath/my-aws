# Steps — Project 11.8 VPC Endpoints (Gateway & Interface)

## Phase 1 — Console

### 1.1 Create VPC with Private Subnet (no NAT Gateway)
- VPC: `vpc-11-8`, CIDR: `10.0.0.0/16`
- Private subnet: `private-11-8`, `10.0.1.0/24`, us-east-1a
- No IGW, no NAT — this subnet has zero internet access by default

### 1.2 Create S3 Gateway Endpoint
1. **VPC** → **Endpoints** → **Create endpoint**
2. Name: `ep-s3-11-8`
3. Service category: AWS services
4. Search: `com.amazonaws.us-east-1.s3` → select **Gateway** type
5. VPC: `vpc-11-8`
6. Route tables: select the private subnet's route table
7. Policy: Full access (default)
8. Create

### 1.3 Create DynamoDB Gateway Endpoint
1. Same process, service: `com.amazonaws.us-east-1.dynamodb`
2. Name: `ep-dynamodb-11-8`
3. Same VPC and route table

### 1.4 Create SSM Interface Endpoint
1. Service: `com.amazonaws.us-east-1.ssm`
2. Name: `ep-ssm-11-8`
3. Type: Interface
4. VPC: `vpc-11-8`, Subnet: `private-11-8`
5. Enable private DNS: Yes
6. Security group: allow HTTPS 443 from VPC CIDR `10.0.0.0/16`
7. Create
8. Repeat for `ssmmessages` and `ec2messages` (required for SSM Session Manager)

### 1.5 Launch EC2 in Private Subnet
- No public IP, no key pair needed (will use SSM)
- Attach IAM role with `AmazonSSMManagedInstanceCore` policy

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<vpc-id>
RT_ID=<private-route-table-id>
SUBNET_ID=<private-subnet-id>
SG_ID=<endpoint-sg-id>

# S3 Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids $RT_ID \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ep-s3-11-8}]'

# DynamoDB Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids $RT_ID \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ep-dynamodb-11-8}]'

# SSM Interface Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.ssm \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_ID \
  --security-group-ids $SG_ID \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ep-ssm-11-8}]'

# Also create ssmmessages and ec2messages endpoints (same command, different service names)
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. List all endpoints in the VPC
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "VpcEndpoints[*].{Name:Tags[?Key=='Name']|[0].Value,Type:VpcEndpointType,State:State,Service:ServiceName}"

# 2. Check route table — S3 gateway endpoint adds a prefix list route
aws ec2 describe-route-tables --route-table-ids $RT_ID \
  --query "RouteTables[0].Routes[*].{Dest:DestinationPrefixListId,Target:GatewayId}"
# Should show: pl-xxxxxxxx (S3 prefix list) → vpce-xxx

# 3. Connect to EC2 via SSM Session Manager (no SSH needed)
aws ssm start-session --target <INSTANCE_ID>
```

---

## Phase 5 — Test

```bash
# All tests run FROM INSIDE the EC2 via SSM session

# Test 1: S3 access WITHOUT going through internet
aws s3 ls  # should work — traffic goes via S3 gateway endpoint
# Confirm: check VPC Flow Logs — traffic to S3 prefix list, NOT to 0.0.0.0/0

# Test 2: Upload and download from S3
aws s3 mb s3://test-bucket-11-8-$(date +%s)
echo "hello endpoint" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://test-bucket-11-8-*/
aws s3 cp s3://test-bucket-11-8-*/test.txt /tmp/downloaded.txt
cat /tmp/downloaded.txt   # should print: hello endpoint

# Test 3: DynamoDB access
aws dynamodb list-tables --region us-east-1  # should work via endpoint

# Test 4: Confirm NO internet access (no NAT, no IGW)
curl --max-time 5 https://example.com  # should TIMEOUT — no internet path
ping -c 3 8.8.8.8                       # should FAIL

# Test 5: Confirm S3 traffic does NOT go through NAT
# (If you had a NAT, check CloudWatch — NAT bytes processed should be 0 for S3 traffic)

# Run automated checker
python code/endpoint_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] S3 Gateway endpoint created, state = available
- [ ] DynamoDB Gateway endpoint created, state = available
- [ ] SSM Interface endpoint created, state = available
- [ ] Route table shows prefix list route for S3 and DynamoDB
- [ ] EC2 accessible via SSM Session Manager (no SSH/public IP needed)
- [ ] `aws s3 ls` works from private EC2 (via endpoint)
- [ ] S3 upload/download works from private EC2
- [ ] `curl https://example.com` times out (no internet path)
- [ ] `ping 8.8.8.8` fails (no internet path)

---

## Teardown
```bash
terraform destroy
# Interface endpoints cost ~$0.01/hr each — destroy after lab
```
