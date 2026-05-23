# Steps — Project 11.5 Three-Tier Web Application

## Phase 1 — Console

### 1.1 Create VPC
- Name: `vpc-11-5`, CIDR: `10.0.0.0/16`, DNS hostnames: enabled

### 1.2 Create 6 Subnets
| Name | CIDR | AZ | Tier |
|------|------|----|------|
| web-public-a | 10.0.1.0/24 | us-east-1a | Web |
| web-public-b | 10.0.2.0/24 | us-east-1b | Web |
| app-private-a | 10.0.3.0/24 | us-east-1a | App |
| app-private-b | 10.0.4.0/24 | us-east-1b | App |
| db-private-a | 10.0.5.0/24 | us-east-1a | DB |
| db-private-b | 10.0.6.0/24 | us-east-1b | DB |

Enable auto-assign public IP on `web-public-a` and `web-public-b` only.

### 1.3 Create Internet Gateway
- Name: `igw-11-5` → attach to `vpc-11-5`

### 1.4 Create 2 NAT Gateways (one per AZ)
- `nat-11-5-a`: in `web-public-a`, allocate Elastic IP
- `nat-11-5-b`: in `web-public-b`, allocate Elastic IP
- Wait for both to be Available

### 1.5 Create Route Tables
- `public-rt-11-5`: `0.0.0.0/0 → igw-11-5` → associate web-public-a, web-public-b
- `private-rt-a-11-5`: `0.0.0.0/0 → nat-11-5-a` → associate app-private-a, db-private-a
- `private-rt-b-11-5`: `0.0.0.0/0 → nat-11-5-b` → associate app-private-b, db-private-b

### 1.6 Security Groups
- `sg-web-11-5`: HTTP 80 from 0.0.0.0/0, SSH 22 from My IP
- `sg-app-11-5`: TCP 8080 from `sg-web-11-5`, SSH from `sg-web-11-5`
- `sg-db-11-5`: MySQL 3306 from `sg-app-11-5`

---

## Phase 2 — AWS CLI

```bash
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query "Vpc.VpcId" --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=vpc-11-5
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create all 6 subnets
for i in "web-public-a 10.0.1.0/24 us-east-1a" \
         "web-public-b 10.0.2.0/24 us-east-1b" \
         "app-private-a 10.0.3.0/24 us-east-1a" \
         "app-private-b 10.0.4.0/24 us-east-1b" \
         "db-private-a 10.0.5.0/24 us-east-1a" \
         "db-private-b 10.0.6.0/24 us-east-1b"; do
  read NAME CIDR AZ <<< $i
  ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $CIDR \
    --availability-zone $AZ --query "Subnet.SubnetId" --output text)
  aws ec2 create-tags --resources $ID --tags Key=Name,Value=$NAME
  echo "$NAME: $ID"
done
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
terraform output
```

---

## Phase 4 — Verify

```bash
# 1. Confirm all 6 subnets exist
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{Name:Tags[?Key=='Name']|[0].Value,CIDR:CidrBlock,AZ:AvailabilityZone}" \
  --output table

# 2. Confirm 2 NAT Gateways are available
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query "NatGateways[*].{ID:NatGatewayId,State:State,Subnet:SubnetId}"

# 3. Confirm route tables — private-a routes to nat-a, private-b routes to nat-b
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,Routes:Routes[*].{Dest:DestinationCidrBlock,Target:NatGatewayId}}"

# 4. Launch test EC2 in each tier and verify connectivity
# Web EC2 → public IP, can reach internet directly
# App EC2 → no public IP, can reach internet via NAT
# DB EC2 → no public IP, can reach internet via NAT (for updates only)

# 5. From App EC2, verify it cannot reach DB EC2 on port 80 (only 3306 allowed)
nc -zv <DB_PRIVATE_IP> 3306   # should succeed
nc -zv <DB_PRIVATE_IP> 80     # should fail

# 6. Run full checker
python code/three_tier_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] VPC with 6 subnets across 2 AZs
- [ ] 2 NAT Gateways (one per AZ) in Available state
- [ ] Public RT: `0.0.0.0/0 → igw`
- [ ] Private RT-a: `0.0.0.0/0 → nat-a`
- [ ] Private RT-b: `0.0.0.0/0 → nat-b`
- [ ] Web subnets have auto-assign public IP enabled
- [ ] App/DB subnets have no public IP
- [ ] SG chaining: web → app → db
- [ ] App EC2 can reach internet (via NAT)
- [ ] DB EC2 cannot be reached from internet

---

## Teardown
```bash
terraform destroy
# 2 NAT Gateways = ~$0.09/hr — destroy immediately after lab
```
