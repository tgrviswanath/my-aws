# Verification & Validation — Project 11.8 VPC Endpoints (Gateway & Interface)

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| S3 Gateway Endpoint | VPC → Endpoints | `ep-s3-11-8`, Type=Gateway, State=**available** |
| DynamoDB Gateway Endpoint | VPC → Endpoints | `ep-dynamodb-11-8`, Type=Gateway, State=**available** |
| SSM Interface Endpoint | VPC → Endpoints | `ep-ssm-11-8`, Type=Interface, State=**available** |
| Route Table | VPC → Route Tables → Routes | Prefix list route `pl-xxx → vpce-xxx` for S3 and DynamoDB |
| EC2 Instance | EC2 → Instances | Running in private subnet, **no** public IP |
| SSM Session | Systems Manager → Session Manager | Instance appears as managed |

📸 Screenshot: Endpoints list showing all 3 endpoints with state = available  
📸 Screenshot: Route table showing prefix list route (pl-xxxxxxxx) for S3  
📸 Screenshot: SSM Session Manager showing instance as managed/online

---

## 2. AWS CLI Verification

```bash
# 2.1 List all endpoints in VPC
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "VpcEndpoints[*].{Name:Tags[?Key=='Name']|[0].Value,Type:VpcEndpointType,State:State,Service:ServiceName}"
# Expected: 3 endpoints, all State=available

# 2.2 Route table — S3 gateway adds a prefix list route
aws ec2 describe-route-tables --route-table-ids $RT_ID \
  --query "RouteTables[0].Routes[?DestinationPrefixListId!=null].{PrefixList:DestinationPrefixListId,Target:GatewayId}"
# Expected: pl-xxxxxxxx (S3) → vpce-xxx, pl-xxxxxxxx (DynamoDB) → vpce-xxx

# 2.3 Connect via SSM (no SSH, no public IP needed)
aws ssm start-session --target <INSTANCE_ID>

# 2.4 From inside EC2 — S3 access via endpoint (no internet)
aws s3 ls                                    # succeeds via endpoint
curl --max-time 5 https://example.com        # timeout — no internet path
ping -c 3 8.8.8.8                            # fails — no internet path

# 2.5 S3 upload/download test
aws s3 mb s3://test-ep-11-8-$(date +%s)
echo "endpoint test" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://test-ep-11-8-*/
aws s3 cp s3://test-ep-11-8-*/test.txt /tmp/downloaded.txt
cat /tmp/downloaded.txt   # prints: endpoint test
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_vpc_endpoint.s3
# aws_vpc_endpoint.dynamodb
# aws_vpc_endpoint.ssm
# aws_vpc_endpoint.ssmmessages
# aws_vpc_endpoint.ec2messages
# aws_security_group.endpoint

terraform state show aws_vpc_endpoint.s3
# Shows: id, vpc_id, service_name, vpc_endpoint_type=Gateway, route_table_ids

terraform state show aws_vpc_endpoint.ssm
# Shows: id, vpc_id, service_name, vpc_endpoint_type=Interface, private_dns_enabled=true

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Confirm traffic to S3 does NOT go through NAT (if NAT existed)
# Check VPC Flow Logs — S3 traffic should show destination as prefix list, not 0.0.0.0/0

# Confirm SSM endpoints are working
aws ssm describe-instance-information \
  --query "InstanceInformationList[*].{ID:InstanceId,Status:PingStatus,Platform:PlatformType}"
# Expected: PingStatus=Online
```

---

## 5. Expected Successful Outputs

**CLI — endpoints list:**
```json
[
  { "Name": "ep-s3-11-8",        "Type": "Gateway",   "State": "available", "Service": "com.amazonaws.us-east-1.s3" },
  { "Name": "ep-dynamodb-11-8",  "Type": "Gateway",   "State": "available", "Service": "com.amazonaws.us-east-1.dynamodb" },
  { "Name": "ep-ssm-11-8",       "Type": "Interface", "State": "available", "Service": "com.amazonaws.us-east-1.ssm" }
]
```

**Route table prefix list routes:**
```json
[
  { "PrefixList": "pl-63a5400a", "Target": "vpce-0abc123" },
  { "PrefixList": "pl-02cd2c6b", "Target": "vpce-0def456" }
]
```

**Internet access test from private EC2:**
```
curl https://example.com → curl: (28) Operation timed out  ✅ (no internet)
aws s3 ls              → (lists buckets)                   ✅ (via endpoint)
```

---

## 6. Verification Checklist

- [ ] S3 Gateway endpoint state = available
- [ ] DynamoDB Gateway endpoint state = available
- [ ] SSM Interface endpoint state = available (+ ssmmessages + ec2messages)
- [ ] Route table shows prefix list routes for S3 and DynamoDB
- [ ] EC2 accessible via SSM Session Manager (no SSH/public IP)
- [ ] `aws s3 ls` works from private EC2
- [ ] S3 upload/download works from private EC2
- [ ] `curl https://example.com` times out (no internet path)
- [ ] `ping 8.8.8.8` fails (no internet path)
- [ ] `terraform plan` shows no changes
