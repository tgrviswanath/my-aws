# Project 8.2 — AWS WAF Web Application Firewall

**Stage:** 08 | **Level:** Intermediate | **Est. Time:** 75 min | **Cost:** ~$5/month base

Protect a CloudFront distribution or Application Load Balancer using WAF v2. Attach the AWS-managed
OWASP Core Rule Set to block SQL injection and XSS automatically, layer a rate-based rule that cuts
off any IP sending more than 1,000 requests in a 5-minute window, and add a custom IP-set rule that
explicitly blocks a specific CIDR range. All ALLOW/BLOCK decisions are streamed to a CloudWatch log
group for real-time visibility.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS WAF v2 | Web ACL with managed rules, rate limiting, IP blocking | $1/WebACL + $1/rule/month |
| Amazon CloudFront | CDN distribution the Web ACL is attached to | $0.0085/10K HTTPS requests |
| Application Load Balancer | Alternative attachment point for WAF (regional) | $0.008/LCU-hour |
| Amazon CloudWatch Logs | Receives WAF logs (log group: aws-waf-logs-myapp) | $0.50/GB ingested |
| AWS IAM | Grants WAF permission to write to CloudWatch log group | Free |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| WAF scope | CLOUDFRONT | Use REGIONAL for ALB |
| Managed rule group | AWSManagedRulesCommonRuleSet | OWASP Top 10 rules |
| Rate limit | 1000 requests / 5 min per IP | Sliding window |
| Blocked CIDR | 192.0.2.0/24 | Custom IP set rule |
| Log group name | aws-waf-logs-myapp | Must start with aws-waf-logs- |
| Default action | ALLOW | Block rules are additive |

### Output

| Artifact | Description |
|---|---|
| Web ACL ARN | arn:aws:wafv2:us-east-1:123456789012:global/webacl/myapp-waf/abc123 |
| SQL injection blocked | AWSManagedRulesCommonRuleSet catches SQLi patterns in query strings and body |
| XSS blocked | Same rule group handles reflected XSS payloads |
| Rate-limited IPs | Any IP exceeding 1000 req/5 min receives HTTP 403 automatically |
| WAF logs | CloudWatch log group aws-waf-logs-myapp contains ALLOW/BLOCK records with ruleMatchDetails |

---

## Architecture

```
Internet Request
      |
      v
+------------------+
| AWS WAF v2       |  <-- evaluated BEFORE CloudFront/ALB processes request
| Web ACL Rules:   |
|  1. IP Set Block |  192.0.2.0/24 → BLOCK
|  2. Rate-Based   |  >1000/5min   → BLOCK
|  3. CRS Managed  |  SQLi / XSS   → BLOCK
|  4. Default      |  everything else → ALLOW
+------------------+
      |
      | ALLOW
      v
+------------------+       +---------------------+
| CloudFront       |  or   | App Load Balancer   |
| Distribution     |       | (REGIONAL scope)    |
+------------------+       +---------------------+
      |
      v
   Origin / EC2 / Lambda

      |
      | all rule evaluations
      v
CloudWatch Logs
(aws-waf-logs-myapp)
```

---

## Quick Start

```cmd
REM 1. Create an IP set for the blocked CIDR range
aws wafv2 create-ip-set ^
  --name blocked-ips ^
  --scope CLOUDFRONT ^
  --ip-address-version IPV4 ^
  --addresses 192.0.2.0/24 ^
  --region us-east-1

REM 2. Create the Web ACL with managed CRS, rate rule, and IP block rule
aws wafv2 create-web-acl ^
  --name myapp-waf ^
  --scope CLOUDFRONT ^
  --default-action Allow={} ^
  --rules file://web-acl-rules.json ^
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=myapp-waf ^
  --region us-east-1

REM 3. Attach the Web ACL to a CloudFront distribution
aws wafv2 associate-web-acl ^
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:global/webacl/myapp-waf/abc123 ^
  --resource-arn arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE ^
  --region us-east-1

REM 4. Create CloudWatch log group (name MUST start with aws-waf-logs-)
aws logs create-log-group --log-group-name aws-waf-logs-myapp --region us-east-1

REM 5. Enable WAF logging to the CloudWatch log group
aws wafv2 put-logging-configuration ^
  --logging-configuration ^
  ResourceArn=arn:aws:wafv2:us-east-1:123456789012:global/webacl/myapp-waf/abc123,^
  LogDestinationConfigs=arn:aws:logs:us-east-1:123456789012:log-group:aws-waf-logs-myapp ^
  --region us-east-1

REM 6. Tail WAF logs for live BLOCK/ALLOW events
aws logs tail aws-waf-logs-myapp --follow --region us-east-1
```

---

## Data Flow

1. Client sends HTTPS request to CloudFront distribution endpoint.
2. WAF Web ACL intercepts the request before CloudFront processes it.
3. Rule 1 (IP Set): source IP is checked against the blocked-ips IP set — CIDR match triggers BLOCK.
4. Rule 2 (Rate-Based): if the IP has sent >1,000 requests in the last 5 minutes (sliding window), request is BLOCKED.
5. Rule 3 (AWSManagedRulesCommonRuleSet): AWS inspects URI, headers, query string, and body for SQLi, XSS, and other OWASP Top 10 patterns — match triggers BLOCK.
6. Rule 4 (Default): if no rule matched, the default ALLOW action forwards the request to CloudFront.
7. Every evaluated request is written to the `aws-waf-logs-myapp` CloudWatch log group with `action`, `ruleGroupList`, and `httpRequest` details.

---

## Project Files

| File | Description |
|---|---|
| `web-acl-rules.json` | JSON rule definitions: IP set block, rate-based, CRS managed group |
| `ip-set.json` | IP set input file with blocked CIDR 192.0.2.0/24 |
| `test_waf.py` | Python script sending SQLi and XSS payloads to verify BLOCK responses |
| `query_waf_logs.sh` | CloudWatch Insights query to count BLOCK vs ALLOW by rule name |
| `waf_cost_estimate.md` | Breakdown: $1 WebACL + $1/rule x3 + sampled request costs |

---

## Lessons Learned

- WAF rules are evaluated before the ALB or CloudFront distribution touches the request — a BLOCK never reaches your origin.
- AWS-managed rule groups like `AWSManagedRulesCommonRuleSet` are maintained and updated by AWS; you get rule updates automatically without redeployment.
- The rate-based rule counts requests per source IP across a 5-minute sliding window — it does not reset on the clock boundary, so a burst of 1,001 requests at minute 4:59 still triggers the block.
- WAF log groups must be named with the prefix `aws-waf-logs-` — any other prefix causes the `put-logging-configuration` call to fail silently.
- The default Web ACL action is ALLOW; BLOCK rules are additive — omitting a rule means traffic passes through, not that it is blocked.
- WAF Capacity Units (WCUs) cap the total rule complexity per Web ACL at 1,500 WCUs by default — each managed rule group and custom rule consumes a defined number of WCUs.
- For ALB attachment, use `--scope REGIONAL` and specify the ALB ARN; CLOUDFRONT scope rules must be created in `us-east-1` regardless of the distribution's origin region.
