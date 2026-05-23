# Notes — Project 11.19

## IPv6 Address Persistence
IPv6 addresses assigned to EC2 instances are NOT persistent across stop/start
(unlike Elastic IPs for IPv4). The address changes when the instance is stopped.
For a static IPv6, use an Elastic IPv6 address (available in some regions).

## Checking IPv6 Connectivity
```bash
# Check your own IPv6 address
curl -6 https://ifconfig.me

# Test IPv6 DNS resolution
nslookup -type=AAAA ipv6.google.com

# Ping IPv6
ping6 ipv6.google.com
ping6 2001:4860:4860::8888   # Google's IPv6 DNS

# SSH via IPv6
ssh -6 ec2-user@2600:1f18:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx
```

## Common Issues
- `ping6` fails from EC2: check SG allows ICMPv6 (protocol 58) from ::/0
- SSH via IPv6 fails: check SG allows TCP 22 from ::/0
- Private EC2 can't reach internet via IPv6: check EIGW route `::/0 → eigw-xxx`
- IPv6 not assigned to instance: check subnet has `assign_ipv6_address_on_creation = true`

## Security Note
Every IPv6-enabled instance gets a globally routable address.
Unlike IPv4 private addresses, IPv6 addresses ARE reachable from the internet
(unless blocked by SG or NACL). Always configure SGs carefully for IPv6.
