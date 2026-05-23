# Verification & Validation — Project 11.4 Network ACLs Implementation

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Public NACL | VPC → Network ACLs | `nacl-public-11-4`, associated with `public-11-4` |
| Private NACL | VPC → Network ACLs | `nacl-private-11-4`, associated with `private-11-4` |
| Public NACL Inbound | Inbound rules tab | Rules 100(HTTP), 110(HTTPS), 120(SSH), 130(ephemeral 1024-65535), * DENY |
| Public NACL Outbound | Outbound rules tab | Rules 100(HTTP), 110(HTTPS), 120(ephemeral), * DENY |
| Subnet Association | Subnet associations tab | Each NACL associated with correct subnet |

📸 Screenshot: Public NACL inbound rules table showing all rule numbers in order  
📸 Screenshot: Subnet associations tab showing `public-11-4` linked to public NACL

---

## 2. AWS CLI Verification

```bash
VPC_ID=<your-vpc-id>

# 2.1 List NACLs and their subnet associations
aws ec2 describe-network-acls \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "NetworkAcls[*].{ID:NetworkAclId,Name:Tags[?Key=='Name']|[0].Value,Subnets:Associations[*].SubnetId}"

# 2.2 View inbound rules for public NACL (sorted by rule number)
aws ec2 describe-network-acls --network-acl-ids $PUB_NACL \
  --query "NetworkAcls[0].Entries[?Egress==\`false\`]|sort_by(@,&RuleNumber)[*].{Rule:RuleNumber,Port:PortRange,Action:RuleAction}"
# Expected: 100=allow, 110=allow, 120=allow, 130=allow, 32767=deny

# 2.3 Confirm stateless behavior — add a DENY before ALLOW, verify it blocks
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 90 --protocol tcp --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 --rule-action deny --ingress
curl --max-time 5 http://<WEB_PUBLIC_IP>   # must timeout — rule 90 fires first

# 2.4 Remove the test DENY rule to restore
aws ec2 delete-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 90 --ingress
curl http://<WEB_PUBLIC_IP>   # must succeed again
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_network_acl.public
# aws_network_acl.private
# aws_network_acl_rule.public_inbound_http
# aws_network_acl_rule.public_inbound_https
# aws_network_acl_rule.public_inbound_ssh
# aws_network_acl_rule.public_inbound_ephemeral
# aws_network_acl_rule.public_outbound_http
# aws_network_acl_rule.public_outbound_https
# aws_network_acl_rule.public_outbound_ephemeral
# aws_network_acl_association.public
# aws_network_acl_association.private

terraform state show aws_network_acl.public
# Shows: vpc_id, subnet_ids, ingress/egress rules

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Key NACL behavior to confirm — stateless (must allow ephemeral ports both ways):
# If you remove the ephemeral port rule (1024-65535), HTTP will break even though port 80 is allowed
# This proves NACLs are stateless (unlike Security Groups)

# Test: remove ephemeral outbound rule temporarily
aws ec2 delete-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 120 --egress
curl http://<WEB_PUBLIC_IP>   # must fail — response packets blocked (stateless)

# Restore
aws ec2 create-network-acl-entry --network-acl-id $PUB_NACL \
  --rule-number 120 --protocol tcp --port-range From=1024,To=65535 \
  --cidr-block 0.0.0.0/0 --rule-action allow --egress
curl http://<WEB_PUBLIC_IP>   # succeeds again
```

---

## 5. Expected Successful Outputs

**CLI — public NACL inbound rules:**
```json
[
  { "Rule": 100, "Port": {"From": 80,   "To": 80},    "Action": "allow" },
  { "Rule": 110, "Port": {"From": 443,  "To": 443},   "Action": "allow" },
  { "Rule": 120, "Port": {"From": 22,   "To": 22},    "Action": "allow" },
  { "Rule": 130, "Port": {"From": 1024, "To": 65535}, "Action": "allow" },
  { "Rule": 32767, "Port": null,                       "Action": "deny"  }
]
```

**Stateless proof:**
```
With ephemeral outbound rule:    curl → ✅ success
Without ephemeral outbound rule: curl → ❌ timeout  (stateless confirmed)
```

---

## 6. Verification Checklist

- [ ] Custom NACL created for public subnet
- [ ] Custom NACL created for private subnet
- [ ] Inbound: HTTP/HTTPS/SSH/ephemeral allowed, default deny
- [ ] Outbound: HTTP/HTTPS/ephemeral allowed, default deny
- [ ] HTTP to web EC2 works with NACL in place
- [ ] Adding DENY rule at lower rule number blocks traffic (stateless confirmed)
- [ ] Removing ephemeral outbound rule breaks HTTP (stateless confirmed)
- [ ] Private NACL only allows traffic from public subnet CIDR
- [ ] `terraform plan` shows no changes
