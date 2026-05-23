# Steps — Project 11.4 Network ACLs Implementation

## Phase 1 — Console

### 1.1 Create VPC and Subnets
- VPC: `vpc-11-4`, CIDR: `10.0.0.0/16`
- Public subnet: `public-11-4`, `10.0.1.0/24`
- Private subnet: `private-11-4`, `10.0.2.0/24`
- Attach IGW, route tables (same as 11.1)

### 1.2 Create Custom NACL for Public Subnet
1. **VPC** → **Network ACLs** → **Create network ACL**
2. Name: `nacl-public-11-4`, VPC: `vpc-11-4`
3. **Inbound rules** (Edit inbound rules):
   | Rule # | Type | Protocol | Port | Source | Allow/Deny |
   |--------|------|----------|------|--------|------------|
   | 100 | HTTP | TCP | 80 | 0.0.0.0/0 | Allow |
   | 110 | HTTPS | TCP | 443 | 0.0.0.0/0 | Allow |
   | 120 | SSH | TCP | 22 | My IP/32 | Allow |
   | 130 | Custom TCP | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
   | * | All traffic | All | All | 0.0.0.0/0 | Deny |
4. **Outbound rules**:
   | Rule # | Type | Protocol | Port | Destination | Allow/Deny |
   |--------|------|----------|------|-------------|------------|
   | 100 | HTTP | TCP | 80 | 0.0.0.0/0 | Allow |
   | 110 | HTTPS | TCP | 443 | 0.0.0.0/0 | Allow |
   | 120 | Custom TCP | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
   | * | All traffic | All | All | 0.0.0.0/0 | Deny |
5. **Subnet associations** → associate `public-11-4`

### 1.3 Create Custom NACL for Private Subnet
- Name: `nacl-private-11-4`
- Inbound: Allow TCP all ports from `10.0.1.0/24` (public subnet), ephemeral from 0.0.0.0/0
- Outbound: Allow TCP all ports to `10.0.1.0/24`, ephemeral to 0.0.0.0/0
- Associate with `private-11-4`

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<your-vpc-id>
PUB_SUBNET=<public-subnet-id>
PRIV_SUBNET=<private-subnet-id>

# Create public NACL
PUB_NACL=$(aws ec2 create-network-acl --vpc-id $VPC_ID \
  --query "NetworkAcl.NetworkAclId" --output text)
aws ec2 create-tags --resources $PUB_NACL --tags Key=Name,Value=nacl-public-11-4

# Inbound rules
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 100 --protocol tcp --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 --rule-action allow --ingress
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 110 --protocol tcp --port-range From=443,To=443 \
  --cidr-block 0.0.0.0/0 --rule-action allow --ingress
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 120 --protocol tcp --port-range From=22,To=22 \
  --cidr-block <MY_IP>/32 --rule-action allow --ingress
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 130 --protocol tcp --port-range From=1024,To=65535 \
  --cidr-block 0.0.0.0/0 --rule-action allow --ingress

# Outbound rules
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 100 --protocol tcp --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 --rule-action allow --egress
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 110 --protocol tcp --port-range From=443,To=443 \
  --cidr-block 0.0.0.0/0 --rule-action allow --egress
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 120 --protocol tcp --port-range From=1024,To=65535 \
  --cidr-block 0.0.0.0/0 --rule-action allow --egress

# Associate with public subnet
aws ec2 replace-network-acl-association \
  --association-id $(aws ec2 describe-network-acls \
    --filters "Name=association.subnet-id,Values=$PUB_SUBNET" \
    --query "NetworkAcls[0].Associations[0].NetworkAclAssociationId" --output text) \
  --network-acl-id $PUB_NACL

echo "Public NACL: $PUB_NACL"
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. List NACLs and their associations
aws ec2 describe-network-acls \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "NetworkAcls[*].{ID:NetworkAclId,Name:Tags[?Key=='Name']|[0].Value,Associations:Associations[*].SubnetId}"

# 2. View inbound rules for public NACL
aws ec2 describe-network-acls --network-acl-ids $PUB_NACL \
  --query "NetworkAcls[0].Entries[?Egress==\`false\`]|sort_by(@,&RuleNumber)"

# 3. Test: HTTP to web EC2 should work
curl http://<WEB_PUBLIC_IP>

# 4. Test: intentionally break it — add a DENY rule before the ALLOW
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 90 --protocol tcp --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 --rule-action deny --ingress
# Now curl should FAIL — rule 90 DENY fires before rule 100 ALLOW
curl http://<WEB_PUBLIC_IP>   # should timeout

# 5. Remove the deny rule to restore
aws ec2 delete-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 90 --ingress

# 6. Run NACL checker
python code/nacl_checker.py --vpc-id $VPC_ID
```

### Verification Checklist
- [ ] Custom NACL created for public subnet
- [ ] Custom NACL created for private subnet
- [ ] Inbound: HTTP/HTTPS/SSH allowed, ephemeral ports allowed
- [ ] Outbound: HTTP/HTTPS/ephemeral allowed
- [ ] HTTP to web EC2 works with NACL in place
- [ ] Adding DENY rule at lower number blocks traffic (stateless confirmed)
- [ ] Removing DENY rule restores traffic
- [ ] Private subnet NACL only allows traffic from public subnet CIDR

---

## Teardown
```bash
terraform destroy
```
