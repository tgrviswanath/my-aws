# Architecture Notes — Project 11.9

## Flow Log Record Format
```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
2 123456789 eni-abc 10.0.1.5 52.94.1.1 54321 443 6 10 5000 1620000000 1620000060 ACCEPT OK
```

## CloudWatch Insights vs Athena
| | CloudWatch Insights | Athena |
|--|--|--|
| Best for | Recent logs, real-time | Historical, large datasets |
| Query language | Custom (like SQL) | Standard SQL |
| Cost | Per GB scanned | Per TB scanned ($5/TB) |
| Setup | None | Create table, partition |

## Useful Athena Table DDL
```sql
CREATE EXTERNAL TABLE vpc_flow_logs (
  version int, account string, interfaceid string,
  sourceaddress string, destinationaddress string,
  sourceport int, destinationport int, protocol int,
  numpackets int, numbytes bigint,
  starttime int, endtime int, action string, logstatus string
)
PARTITIONED BY (dt string)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ' '
LOCATION 's3://flowlogs-11-9-<account>/AWSLogs/<account>/vpcflowlogs/us-east-1/';
```
