# VPC — Virtual Private Cloud Deep Dive

## What is a VPC?
A VPC is your private, isolated network within AWS. You control IP ranges, subnets, routing, and network gateways. Every AWS account gets a default VPC per region.

---

## VPC Architecture

```
VPC (10.0.0.0/16)
├── Public Subnet AZ-a (10.0.1.0/24)
│   ├── Internet Gateway route
│   ├── NAT Gateway
│   └── Bastion Host / ALB
├── Public Subnet AZ-b (10.0.2.0/24)
│   └── NAT Gateway (HA)
├── Private Subnet AZ-a (10.0.11.0/24)
│   ├── EC2 App Servers
│   └── ECS Tasks
├── Private Subnet AZ-b (10.0.12.0/24)
│   └── EC2 App Servers
├── Database Subnet AZ-a (10.0.21.0/24)
│   └── RDS Primary
└── Database Subnet AZ-b (10.0.22.0/24)
    └── RDS Standby
```

---

## CIDR Planning

```
/16 = 65,536 IPs  (VPC level — recommended)
/24 = 256 IPs     (subnet level — common)
/28 = 16 IPs      (minimum subnet size)

AWS reserves 5 IPs per subnet:
  x.x.x.0   Network address
  x.x.x.1   VPC router
  x.x.x.2   DNS server
  x.x.x.3   Reserved for future use
  x.x.x.255 Broadcast (not supported, reserved)

So /24 = 251 usable IPs
```

---

## Create VPC with CLI

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=production}]' \
  --query 'Vpc.VpcId' --output text)

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames

# Create subnets
PUB_SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-a}]' \
  --query 'Subnet.SubnetId' --output text)

PRIV_SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-a}]' \
  --query 'Subnet.SubnetId' --output text)

# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# Create public route table
PUB_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route \
  --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID
aws ec2 associate-route-table \
  --route-table-id $PUB_RT \
  --subnet-id $PUB_SUBNET_A

# Enable auto-assign public IP for public subnet
aws ec2 modify-subnet-attribute \
  --subnet-id $PUB_SUBNET_A \
  --map-public-ip-on-launch
```

---

## NAT Gateway

Allows private subnet instances to reach the internet (outbound only).

```bash
# Allocate Elastic IP for NAT Gateway
EIP=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' --output text)

# Create NAT Gateway in public subnet
NAT_GW=$(aws ec2 create-nat-gateway \
  --subnet-id $PUB_SUBNET_A \
  --allocation-id $EIP \
  --query 'NatGateway.NatGatewayId' --output text)

# Wait for NAT Gateway to be available
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW

# Add route in private route table
PRIV_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route \
  --route-table-id $PRIV_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW
aws ec2 associate-route-table \
  --route-table-id $PRIV_RT \
  --subnet-id $PRIV_SUBNET_A
```

**Cost**: $0.045/hr + $0.045/GB processed. For HA, deploy one NAT Gateway per AZ.

---

## Security Groups vs NACLs

| Feature | Security Group | NACL |
|---------|---------------|------|
| Level | Instance/ENI | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow + Deny |
| Evaluation | All rules | In order (lowest number first) |
| Default | Deny all in, allow all out | Allow all in and out |
| Use case | Fine-grained instance control | Subnet-level broad rules |

### Security Group Chaining (Best Practice)

```
Internet → ALB-SG (80,443 from 0.0.0.0/0)
         → App-SG (8080 from ALB-SG only)
         → DB-SG  (5432 from App-SG only)
```

```bash
# App SG: only allow traffic from ALB SG
aws ec2 authorize-security-group-ingress \
  --group-id sg-app-12345678 \
  --protocol tcp \
  --port 8080 \
  --source-group sg-alb-12345678

# DB SG: only allow traffic from App SG
aws ec2 authorize-security-group-ingress \
  --group-id sg-db-12345678 \
  --protocol tcp \
  --port 5432 \
  --source-group sg-app-12345678
```

### NACL Example

```bash
# Create NACL
NACL_ID=$(aws ec2 create-network-acl \
  --vpc-id $VPC_ID \
  --query 'NetworkAcl.NetworkAclId' --output text)

# Allow HTTPS inbound (rule 100)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 100 \
  --protocol tcp \
  --port-range From=443,To=443 \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow \
  --ingress

# Allow ephemeral ports inbound (for return traffic)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 200 \
  --protocol tcp \
  --port-range From=1024,To=65535 \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow \
  --ingress

# Deny all other inbound (rule 32766)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 32766 \
  --protocol -1 \
  --cidr-block 0.0.0.0/0 \
  --rule-action deny \
  --ingress
```

---

## VPC Peering

Connect two VPCs (same or different accounts/regions) privately.

```bash
# Create peering connection
PEER_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa \
  --peer-vpc-id vpc-bbb \
  --peer-region us-west-2 \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

# Accept (from the other VPC's account/region)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id $PEER_ID

# Add routes on both sides
aws ec2 create-route \
  --route-table-id rtb-aaa \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id $PEER_ID
```

**Limitations**: No transitive routing. If A↔B and B↔C, A cannot reach C through B.

---

## VPC Endpoints

Access AWS services without internet traffic.

```bash
# Gateway endpoint (S3, DynamoDB — free)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-private-aaa rtb-private-bbb \
  --vpc-endpoint-type Gateway

# Interface endpoint (most other services — $0.01/hr/AZ)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-private-aaa subnet-private-bbb \
  --security-group-ids sg-endpoint-12345678 \
  --private-dns-enabled
```

---

## VPC Flow Logs

```bash
# Enable flow logs to CloudWatch
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws:iam::123456789:role/flowlogs-role

# Enable flow logs to S3 (cheaper for long-term)
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::my-flowlogs-bucket/vpc/
```

---

## CloudFormation VPC Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'

Parameters:
  VpcCidr:
    Type: String
    Default: 10.0.0.0/16

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: production-vpc

  InternetGateway:
    Type: AWS::EC2::InternetGateway

  IGWAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: public-a

  PrivateSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: private-a

  NatEIP:
    Type: AWS::EC2::EIP
    DependsOn: IGWAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatEIP.AllocationId
      SubnetId: !Ref PublicSubnetA

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: IGWAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway
```

---

## Interview Q&A

### Q1: What is the difference between a public and private subnet?
**Public subnet**: Has a route to an Internet Gateway (0.0.0.0/0 → IGW). Instances can have public IPs and be directly reachable from the internet.
**Private subnet**: No route to IGW. Instances cannot be directly reached from internet. Use NAT Gateway for outbound internet access. Best for databases, app servers, internal services.

### Q2: What is the difference between Security Groups and NACLs?
**Security Groups**: Stateful (return traffic automatically allowed), instance-level, allow rules only, all rules evaluated. Best for fine-grained instance control.
**NACLs**: Stateless (must explicitly allow return traffic), subnet-level, allow and deny rules, rules evaluated in order. Best for broad subnet-level controls, blocking specific IPs.

### Q3: What is a VPC Endpoint and why use it?
VPC Endpoints allow private connectivity to AWS services without internet traffic. Gateway endpoints (S3, DynamoDB) are free and add routes to route tables. Interface endpoints create ENIs in your subnet. Benefits: improved security (traffic stays on AWS network), reduced NAT Gateway costs, can enforce bucket policies requiring VPC endpoint access.

### Q4: What is the difference between VPC Peering and Transit Gateway?
**VPC Peering**: Direct 1:1 connection between two VPCs. No transitive routing. Simple but doesn't scale (N VPCs = N*(N-1)/2 peering connections).
**Transit Gateway**: Hub-and-spoke model. Connect thousands of VPCs and on-premises networks through a single gateway. Supports transitive routing. Better for large-scale multi-VPC architectures.

### Q5: How do you design a VPC for a 3-tier web application?
- Public subnets (2+ AZs): ALB, NAT Gateways
- Private app subnets (2+ AZs): EC2/ECS app servers, accessible only from ALB SG
- Private DB subnets (2+ AZs): RDS, accessible only from app SG
- Security groups chained: ALB-SG → App-SG → DB-SG
- VPC Flow Logs enabled
- VPC Endpoints for S3, DynamoDB, Secrets Manager
- No direct internet access to app or DB tiers
