# VPC — Real-World Use Cases

## Use Case 1: 3-Tier Production Network

**Business Problem**: Deploy a web app with strict network isolation — internet can only reach the load balancer, app servers can only be reached from the ALB, databases only from app servers.

```bash
REGION="us-east-1"

# 1. Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=prod-vpc}]' \
  --query 'Vpc.VpcId' --output text)

aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# 2. Create subnets across 3 AZs
for i in 1 2 3; do
  AZ="${REGION}$(echo 'abc' | cut -c$i)"

  # Public subnet (ALB lives here)
  PUB_SUBNET[$i]=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block "10.0.${i}.0/24" \
    --availability-zone $AZ \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=public-${AZ}}]" \
    --query 'Subnet.SubnetId' --output text)
  aws ec2 modify-subnet-attribute --subnet-id ${PUB_SUBNET[$i]} --map-public-ip-on-launch

  # Private subnet (App servers live here)
  PRIV_SUBNET[$i]=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block "10.0.1${i}.0/24" \
    --availability-zone $AZ \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-app-${AZ}}]" \
    --query 'Subnet.SubnetId' --output text)

  # DB subnet (Databases live here)
  DB_SUBNET[$i]=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block "10.0.2${i}.0/24" \
    --availability-zone $AZ \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-db-${AZ}}]" \
    --query 'Subnet.SubnetId' --output text)
done

# 3. Internet Gateway (for public subnets)
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=prod-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID

# 4. NAT Gateways (one per AZ for HA — private subnets need internet for updates)
for i in 1 2 3; do
  EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
  NAT_GW[$i]=$(aws ec2 create-nat-gateway \
    --subnet-id ${PUB_SUBNET[$i]} \
    --allocation-id $EIP_ALLOC \
    --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=nat-az${i}}]" \
    --query 'NatGateway.NatGatewayId' --output text)
done

# 5. Route tables
# Public RT: 0.0.0.0/0 → IGW
PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $PUB_RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
for i in 1 2 3; do
  aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id ${PUB_SUBNET[$i]}
done

# Private RTs: 0.0.0.0/0 → NAT GW (one per AZ)
for i in 1 2 3; do
  PRIV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
  aws ec2 create-route --route-table-id $PRIV_RT --destination-cidr-block 0.0.0.0/0 --nat-gateway-id ${NAT_GW[$i]}
  aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id ${PRIV_SUBNET[$i]}
  aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id ${DB_SUBNET[$i]}
done

# 6. Security Groups (chained: ALB → App → DB)
SG_ALB=$(aws ec2 create-security-group --group-name sg-alb --description "ALB" --vpc-id $VPC_ID --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_ALB --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ALB --protocol tcp --port 80  --cidr 0.0.0.0/0

SG_APP=$(aws ec2 create-security-group --group-name sg-app --description "App servers" --vpc-id $VPC_ID --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_APP --protocol tcp --port 8080 --source-group $SG_ALB

SG_DB=$(aws ec2 create-security-group --group-name sg-db --description "Databases" --vpc-id $VPC_ID --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_DB --protocol tcp --port 5432 --source-group $SG_APP

echo "3-tier VPC created!"
echo "Public subnets:  ${PUB_SUBNET[*]}"
echo "Private subnets: ${PRIV_SUBNET[*]}"
echo "DB subnets:      ${DB_SUBNET[*]}"
```

**What you learn**: Subnet tiers, NAT Gateway HA, security group chaining, route table design.

---

## Use Case 2: VPC Peering (Connect Two VPCs)

**Business Problem**: Shared services VPC (monitoring, logging) needs to communicate with application VPCs without going over the internet.

```bash
# VPC A: 10.0.0.0/16 (application)
# VPC B: 10.1.0.0/16 (shared services)

VPC_A="vpc-app-xxxxxxxx"
VPC_B="vpc-shared-xxxxxxxx"

# 1. Create peering connection
PEER_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id $VPC_A \
  --peer-vpc-id $VPC_B \
  --tag-specifications 'ResourceType=vpc-peering-connection,Tags=[{Key=Name,Value=app-to-shared}]' \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

# 2. Accept the peering (if same account, can auto-accept)
aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id $PEER_ID

# 3. Add routes in BOTH VPCs (peering is not transitive!)
# In VPC A: route to VPC B via peering
aws ec2 create-route \
  --route-table-id $RT_VPC_A \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id $PEER_ID

# In VPC B: route to VPC A via peering
aws ec2 create-route \
  --route-table-id $RT_VPC_B \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id $PEER_ID

# 4. Update security groups to allow traffic from peered VPC
aws ec2 authorize-security-group-ingress \
  --group-id $SG_MONITORING \
  --protocol tcp --port 9090 \
  --cidr 10.0.0.0/16  # Allow from app VPC

# Verify connectivity
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids $PEER_ID \
  --query 'VpcPeeringConnections[0].Status'
```

**What you learn**: VPC peering, bidirectional routes, CIDR non-overlap requirement, transitive routing limitation.

---

## Use Case 3: VPC Endpoints (Keep Traffic Off Internet)

**Business Problem**: EC2 instances in private subnets need to access S3 and DynamoDB without going through NAT Gateway (saves $0.045/GB).

```bash
# Gateway endpoints (FREE — S3 and DynamoDB only)
# 1. S3 Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids $PRIV_RT_1 $PRIV_RT_2 $PRIV_RT_3 \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-endpoint}]'

# 2. DynamoDB Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids $PRIV_RT_1 $PRIV_RT_2 $PRIV_RT_3

# Interface endpoints ($0.01/hr per AZ — for other services)
# 3. Secrets Manager Interface Endpoint (Lambda can fetch secrets without internet)
SG_ENDPOINT=$(aws ec2 create-security-group \
  --group-name sg-vpc-endpoints \
  --description "VPC Interface Endpoints" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ENDPOINT \
  --protocol tcp --port 443 \
  --cidr 10.0.0.0/16  # Allow from entire VPC

aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIV_SUBNET_1 $PRIV_SUBNET_2 \
  --security-group-ids $SG_ENDPOINT \
  --private-dns-enabled

# 4. Verify: from EC2 in private subnet, S3 traffic stays in AWS
# Before endpoint: traffic goes EC2 → NAT GW → Internet → S3
# After endpoint:  traffic goes EC2 → VPC Endpoint → S3 (never leaves AWS)
aws s3 ls s3://my-bucket  # Should work without NAT GW
```

**What you learn**: Gateway vs Interface endpoints, cost savings vs NAT, private DNS for interface endpoints.

---

## Use Case 4: VPC Flow Logs for Security Investigation

**Business Problem**: Investigate a suspected data exfiltration — find all outbound connections from a compromised EC2 instance.

```bash
# 1. Enable VPC Flow Logs to CloudWatch
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws:iam::123456789:role/flowlogs-role \
  --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}'

# 2. Query flow logs with CloudWatch Logs Insights
# Find all REJECTED connections (potential port scans or attacks)
aws logs start-query \
  --log-group-name /aws/vpc/flowlogs \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, srcAddr, dstAddr, dstPort, action
    | filter action = "REJECT"
    | stats count(*) as rejectCount by srcAddr, dstAddr, dstPort
    | sort rejectCount desc
    | limit 20
  '

# 3. Find all outbound connections from a specific instance
INSTANCE_IP="10.0.1.50"
aws logs start-query \
  --log-group-name /aws/vpc/flowlogs \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string "
    fields @timestamp, srcAddr, dstAddr, dstPort, bytes, action
    | filter srcAddr = '${INSTANCE_IP}' and action = 'ACCEPT'
    | stats sum(bytes) as totalBytes by dstAddr, dstPort
    | sort totalBytes desc
    | limit 50
  "

# 4. Detect unusual data transfer (> 1GB to external IP)
aws logs start-query \
  --log-group-name /aws/vpc/flowlogs \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields srcAddr, dstAddr, bytes
    | filter not (dstAddr like /^10\./ or dstAddr like /^172\./ or dstAddr like /^192\.168\./)
    | stats sum(bytes) as totalBytes by srcAddr, dstAddr
    | filter totalBytes > 1073741824
    | sort totalBytes desc
  '
```

**What you learn**: Flow logs setup, CloudWatch Logs Insights queries, security investigation patterns.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Single NAT Gateway | AZ failure = no internet for private subnets | One NAT GW per AZ |
| Overlapping CIDR blocks | Can't peer VPCs | Plan CIDR ranges upfront |
| No VPC endpoints for S3/DynamoDB | Unnecessary NAT GW costs | Add Gateway endpoints (free) |
| Security group allows 0.0.0.0/0 on all ports | Open to internet | Restrict to specific ports and sources |
| Not enabling flow logs | Can't investigate security incidents | Enable from day 1 |
| Using default VPC in production | No isolation, default settings | Create custom VPC with proper segmentation |
