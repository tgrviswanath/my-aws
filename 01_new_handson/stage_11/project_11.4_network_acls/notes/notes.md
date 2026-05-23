# Notes — Project 11.4

## Most Common Mistake
Forgetting ephemeral ports (1024-65535) in outbound rules.
Symptom: SSH connects but hangs, HTTP requests time out.
Fix: Add outbound rule allowing TCP 1024-65535 to 0.0.0.0/0.

## Blocking a Specific IP
```bash
# Add a DENY rule at a low rule number to block a specific IP
aws ec2 create-network-acl-entry --network-acl-id $NACL_ID \
  --rule-number 50 --protocol -1 \
  --cidr-block 1.2.3.4/32 --rule-action deny --ingress
```
This is something SGs cannot do — NACLs are the only way to explicitly deny.
