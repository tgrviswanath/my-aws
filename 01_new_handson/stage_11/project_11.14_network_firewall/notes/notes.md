# Notes — Project 11.14

## Most Common Mistake
Forgetting the IGW edge route table association.
The IGW needs a route table that sends return traffic back through the firewall.
Without it: outbound works but inbound responses are dropped.

## Getting the Firewall Endpoint ID
```bash
aws network-firewall describe-firewall --firewall-name nfw-11-14 \
  --query "FirewallStatus.SyncStates.*.Attachment.EndpointId" \
  --output text
```
Use this ID as the target in route tables (not the firewall ARN).

## Firewall Logs Setup
```bash
# Enable flow logs and alert logs
aws network-firewall update-logging-configuration \
  --firewall-name nfw-11-14 \
  --logging-configuration '{
    "LogDestinationConfigs": [
      {
        "LogType": "FLOW",
        "LogDestinationType": "CloudWatchLogs",
        "LogDestination": {"logGroup": "/aws/network-firewall/nfw-11-14/flow"}
      },
      {
        "LogType": "ALERT",
        "LogDestinationType": "CloudWatchLogs",
        "LogDestination": {"logGroup": "/aws/network-firewall/nfw-11-14/alert"}
      }
    ]
  }'
```

## Suricata Rule Example
```
# Block HTTP requests containing a specific string
alert http any any -> any any (msg:"Block keyword"; content:"blocked-keyword"; http_uri; sid:1001; rev:1;)

# Block all traffic to a specific IP
drop ip any any -> 1.2.3.4 any (msg:"Block bad IP"; sid:1002; rev:1;)
```
