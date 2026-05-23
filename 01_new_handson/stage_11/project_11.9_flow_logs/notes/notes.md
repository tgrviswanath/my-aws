# Notes — Project 11.9

## Flow Log Delay
Flow logs have a ~10 minute delay before appearing in CloudWatch.
For the 1-minute aggregation interval, records are still batched and delayed.
Don't panic if logs don't appear immediately.

## Generating Test Traffic
```bash
# Generate ACCEPT traffic
curl https://example.com
aws s3 ls

# Generate REJECT traffic (blocked port)
nc -zv 8.8.8.8 9999   # port 9999 blocked by SG → REJECT record

# Generate high volume for analysis
for i in $(seq 1 100); do curl -s https://example.com > /dev/null; done
```

## Security Use Cases
- Find port scans: many REJECT records from same srcAddr
- Find data exfiltration: unusually high bytes from a private instance
- Find lateral movement: unexpected traffic between private subnets
