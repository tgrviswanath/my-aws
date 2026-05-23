# Notes — Project 11.2

## Key Gotchas
- NAT Gateway must be in a PUBLIC subnet — common mistake is putting it in private
- NAT Gateway takes ~1 minute to become available — wait before testing
- Private EC2 needs SSM Agent or a bastion to access — no direct SSH from internet

## Cost Tip
For learning, use a NAT Instance (t3.nano) instead of NAT Gateway to save ~$30/month.
Switch to NAT Gateway for any production or performance testing.
