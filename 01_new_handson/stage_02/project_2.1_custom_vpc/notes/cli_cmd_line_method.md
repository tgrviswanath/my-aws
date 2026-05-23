Got it! Here's the full step-by-step guide. Run each command one by one in your terminal.

Phase 1 — Create VPC
Step 1 — Create VPC and save the ID:

VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=handson-vpc
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
echo "VPC: $VPC_ID"

Copy
bash
Phase 2 — Create 6 Subnets
Step 2 — Public subnets:

PUB_A=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB_A --tags Key=Name,Value=public-subnet-a

PUB_B=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PUB_B --tags Key=Name,Value=public-subnet-b

Copy
bash
Step 3 — Private app subnets:

PRIV_APP_A=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_APP_A --tags Key=Name,Value=private-app-a

PRIV_APP_B=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 --availability-zone us-east-1b --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_APP_B --tags Key=Name,Value=private-app-b

Copy
bash
Step 4 — Private DB subnets:

PRIV_DB_A=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.5.0/24 --availability-zone us-east-1a --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_DB_A --tags Key=Name,Value=private-db-a

PRIV_DB_B=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.6.0/24 --availability-zone us-east-1b --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $PRIV_DB_B --tags Key=Name,Value=private-db-b

Copy
bash
Phase 3 — Internet Gateway
Step 5 — Create and attach IGW:

IGW_ID=$(aws ec2 create-internet-gateway --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=handson-igw
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
echo "IGW: $IGW_ID"

Copy
bash
Phase 4 — NAT Gateway
Step 6 — Allocate Elastic IP and create NAT Gateway:

EIP=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)
NAT_ID=$(aws ec2 create-nat-gateway --subnet-id $PUB_A --allocation-id $EIP --query "NatGateway.NatGatewayId" --output text)
aws ec2 create-tags --resources $NAT_ID --tags Key=Name,Value=handson-nat
echo "Waiting for NAT Gateway to become available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_ID
echo "NAT Gateway ready: $NAT_ID"

Copy
bash
⏳ This takes ~1 minute to become available.

Phase 5 — Route Tables
Step 7 — Public route table (routes to IGW):

PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PUB_RT --tags Key=Name,Value=public-rt
aws ec2 create-route --route-table-id $PUB_RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_A
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_B

Copy
bash
Step 8 — Private route table (routes to NAT):

PRIV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $PRIV_RT --tags Key=Name,Value=private-rt
aws ec2 create-route --route-table-id $PRIV_RT --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_ID
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV_APP_A
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV_APP_B
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV_DB_A
aws ec2 associate-route-table --route-table-id $PRIV_RT --subnet-id $PRIV_DB_B

Copy
bash
Phase 6 — Verify Everything
Step 9 — Verify:

# Check VPC
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=handson-vpc" --query "Vpcs[*].{ID:VpcId,CIDR:CidrBlock,State:State}"

# Check all 6 subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,CIDR:CidrBlock,AZ:AvailabilityZone}"

# Check route tables
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,Routes:Routes[*].DestinationCidrBlock}"

Copy
bash
⚠️ Important: All the $VPC_ID, $PUB_A, $NAT_ID etc. variables are session-scoped. Run all commands in the same terminal session so the variables carry over.

Let me know after each phase and I'll guide you through the next one!