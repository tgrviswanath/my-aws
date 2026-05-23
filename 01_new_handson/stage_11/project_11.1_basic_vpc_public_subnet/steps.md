# Steps — Project 11.1 Basic VPC with Public Subnet

## Phase 1 — Console

### 1.1 Create VPC
1. Go to **VPC** → **Your VPCs** → **Create VPC**
2. Name: `vpc-11-1`
3. IPv4 CIDR: `10.0.0.0/16`
4. Tenancy: Default
5. Click **Create VPC**

### 1.2 Create Public Subnet
1. **VPC** → **Subnets** → **Create subnet**
2. VPC: `vpc-11-1`
3. Name: `public-subnet-11-1`
4. AZ: `us-east-1a`
5. CIDR: `10.0.1.0/24`
6. Create
7. Select subnet → **Actions** → **Edit subnet settings** → Enable **Auto-assign public IPv4**

### 1.3 Create and Attach Internet Gateway
1. **VPC** → **Internet Gateways** → **Create internet gateway**
2. Name: `igw-11-1`
3. After creation: **Actions** → **Attach to VPC** → select `vpc-11-1`

### 1.4 Create Route Table and Add Route
1. **VPC** → **Route Tables** → **Create route table**
2. Name: `public-rt-11-1`, VPC: `vpc-11-1`
3. **Routes** tab → **Edit routes** → Add:
   - Destination: `0.0.0.0/0`, Target: `igw-11-1`
4. **Subnet associations** → **Edit** → associate `public-subnet-11-1`

### 1.5 Create Security Group
1. **EC2** → **Security Groups** → **Create security group**
2. Name: `sg-web-11-1`, VPC: `vpc-11-1`
3. Inbound rules:
   - SSH (22) from My IP
   - HTTP (80) from 0.0.0.0/0

### 1.6 Launch EC2 Instance
1. **EC2** → **Launch Instance**
2. AMI: Amazon Linux 2023
3. Type: t3.micro
4. Network: `vpc-11-1`, Subnet: `public-subnet-11-1`
5. Auto-assign public IP: Enable
6. Security group: `sg-web-11-1`
7. Key pair: select or create one
8. Launch

---

## Phase 2 — AWS CLI

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=vpc-11-1
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create public subnet
SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --query "Subnet.SubnetId" --output text)
aws ec2 create-tags --resources $SUBNET_ID --tags Key=Name,Value=public-subnet-11-1
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_ID --map-public-ip-on-launch

# Create and attach IGW
IGW_ID=$(aws ec2 create-internet-gateway \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=igw-11-1
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID

# Create route table and add route
RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID --query "RouteTable.RouteTableId" --output text)
aws ec2 create-tags --resources $RT_ID --tags Key=Name,Value=public-rt-11-1
aws ec2 create-route --route-table-id $RT_ID \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $RT_ID --subnet-id $SUBNET_ID

echo "VPC: $VPC_ID | Subnet: $SUBNET_ID | IGW: $IGW_ID | RT: $RT_ID"
```

---

## Phase 3 — Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
terraform output
```

---

## Phase 4 — Verify

```bash
# 1. Confirm VPC exists
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=vpc-11-1" \
  --query "Vpcs[*].{ID:VpcId,CIDR:CidrBlock,State:State}"

# 2. Confirm subnet is public (has IGW route)
aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values=public-subnet-11-1" \
  --query "Subnets[*].{ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}"

# 3. Confirm IGW is attached
aws ec2 describe-internet-gateways \
  --filters "Name=tag:Name,Values=igw-11-1" \
  --query "InternetGateways[*].{ID:InternetGatewayId,Attachments:Attachments}"

# 4. Confirm route table has 0.0.0.0/0 → IGW
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=public-rt-11-1" \
  --query "RouteTables[*].Routes"

# 5. SSH into EC2 and test internet
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
curl -s https://checkip.amazonaws.com   # should return the instance's public IP
ping -c 3 8.8.8.8                        # should succeed

# 6. Run the Python checker
pip install boto3
python code/vpc_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] VPC created with CIDR 10.0.0.0/16
- [ ] Subnet created with CIDR 10.0.1.0/24 in us-east-1a
- [ ] Auto-assign public IP enabled on subnet
- [ ] IGW created and attached to VPC
- [ ] Route table has `0.0.0.0/0 → igw-xxx`
- [ ] Route table associated with public subnet
- [ ] EC2 launched with a public IP
- [ ] SSH into EC2 succeeds
- [ ] `curl https://checkip.amazonaws.com` returns public IP
- [ ] `ping 8.8.8.8` succeeds from inside EC2

---

## Teardown
```bash
# Terminate EC2 first, then:
terraform destroy
# Or manually: delete EC2 → SG → RT associations → RT → IGW detach → IGW → Subnet → VPC
```
