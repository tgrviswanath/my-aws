# Project 8.4 — GuardDuty + Security Hub
## Threat Detection, Security Aggregation, and EventBridge Auto-Remediation

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `guardduty:*`, `securityhub:*`, `events:*`, `lambda:*`, `sns:*`
- [ ] Region: `us-east-1`
- [ ] Note: Both services have 30-day free trials
- [ ] S3 buckets and EC2 instances for GuardDuty to analyze (it monitors your account automatically)

```bash
# Check current account
aws sts get-caller-identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
```

---

## Decision Point 1

**GuardDuty vs Inspector vs Macie — which security service?**

| Service | What It Detects | Data Source | Best For |
|---------|----------------|-------------|----------|
| **GuardDuty** ✅ | Active threats, anomalies | VPC Flow Logs, CloudTrail, DNS logs | Threat detection, lateral movement |
| **Inspector** | Vulnerabilities in code/OS | EC2 agent, ECR scanning | CVEs, OS patches, code vulnerabilities |
| **Macie** | Sensitive data exposure | S3 object content | PII in S3, GDPR/HIPAA data discovery |
| **Security Hub** ✅ | Aggregates all findings | GuardDuty + Inspector + Config + Macie | Central security dashboard |

**Use all four together** for complete security posture.

**For this project:** GuardDuty (threat detection) + Security Hub (aggregation).

---

## 1. Architecture Overview

```
VPC Flow Logs ──────────────┐
CloudTrail ─────────────────┤
DNS Logs ────────────────────┤──→ GuardDuty Detector
S3 Data Events ─────────────┘          │
                                        │ Findings
                                        ▼
AWS Config ──────────────────────→ Security Hub
Inspector ───────────────────────→     │
Macie ───────────────────────────→     │ HIGH severity finding
                                        ▼
                                   EventBridge Rule
                                        │
                                        ▼
                                   Lambda (auto-remediate)
                                   ├── Block IP in WAF
                                   ├── Isolate EC2 instance
                                   └── Send SNS alert
```

---

## 2. Enable GuardDuty

```bash
# Enable GuardDuty detector
DETECTOR_ID=$(aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --data-sources '{
    "S3Logs": {"Enable": true},
    "Kubernetes": {"AuditLogs": {"Enable": false}},
    "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": false}}
  }' \
  --tags '{"Project": "security-monitoring"}' \
  --query 'DetectorId' \
  --output text)

echo "GuardDuty Detector ID: $DETECTOR_ID"

# Verify detector is enabled
aws guardduty get-detector \
  --detector-id $DETECTOR_ID \
  --query '{Status:Status,FindingPublishingFrequency:FindingPublishingFrequency}'
```

---

## 3. Generate Sample Findings for Testing

```bash
# Create sample findings (all finding types — for testing only)
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types \
    "UnauthorizedAccess:EC2/SSHBruteForce" \
    "Recon:EC2/PortScan" \
    "CryptoCurrency:EC2/BitcoinTool.B" \
    "Backdoor:EC2/C&CActivity.B" \
    "CredentialAccess:IAMUser/AnomalousBehavior"

# List findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{
    "Criterion": {
      "severity": {"Gte": 4}
    }
  }' \
  --query 'FindingIds[]'

# Get finding details
FINDING_ID=$(aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --query 'FindingIds[0]' \
  --output text)

aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $FINDING_ID \
  --query 'Findings[0].{Type:Type,Severity:Severity,Title:Title}'
```

---

## 4. Enable Security Hub

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards \
  --tags '{"Project": "security-monitoring"}'

# Enable additional security standards
# AWS Foundational Security Best Practices
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[
    {
      "StandardsArn": "arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"
    },
    {
      "StandardsArn": "arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.2.0"
    }
  ]'

# Check enabled standards
aws securityhub get-enabled-standards \
  --query 'StandardsSubscriptions[].{Name:StandardsArn,Status:StandardsStatus}'
```

---

## 5A. Console: Enable GuardDuty and Security Hub

**GuardDuty:**
1. Navigate to **GuardDuty** → Click **Get Started** → **Enable GuardDuty**
2. Note the 30-day free trial message
3. GuardDuty immediately starts analyzing VPC Flow Logs, CloudTrail, DNS
4. Go to **Findings** — see any active findings (or generate samples)
5. **Settings** → **Sample findings** → **Generate sample findings** (for testing)

**Security Hub:**
1. Navigate to **Security Hub** → Click **Go to Security Hub** → **Enable Security Hub**
2. **Security standards** — enable:
   - ✅ `AWS Foundational Security Best Practices v1.0.0`
   - ✅ `CIS AWS Foundations Benchmark v1.2.0`
3. Click **Enable Security Hub**
4. Go to **Summary** — see aggregated findings from GuardDuty + Config + more

---

## 5B. CLI: Configure EventBridge Auto-Remediation

```bash
# Create Lambda function for auto-remediation
cat > /tmp/guardduty_remediate.py << 'PYEOF'
import json
import boto3
import os

def lambda_handler(event, context):
    """Auto-remediate HIGH severity GuardDuty findings."""
    detail = event.get('detail', {})
    severity = detail.get('severity', 0)
    finding_type = detail.get('type', '')
    
    print(f"Finding: {finding_type}, Severity: {severity}")
    
    # Only act on HIGH (7+) and CRITICAL (9+) findings
    if severity < 7.0:
        return {'action': 'skipped', 'reason': 'severity too low'}
    
    actions_taken = []
    
    # Extract relevant resource info
    resource = detail.get('resource', {})
    instance_details = resource.get('instanceDetails', {})
    
    # Action 1: Send SNS notification
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject=f"HIGH GuardDuty Finding: {finding_type}",
        Message=json.dumps(detail, indent=2, default=str)
    )
    actions_taken.append('sns_notification')
    
    # Action 2: If EC2 instance involved, add to isolation security group
    instance_id = instance_details.get('instanceId')
    if instance_id:
        ec2 = boto3.client('ec2')
        ec2.create_tags(
            Resources=[instance_id],
            Tags=[
                {'Key': 'SecurityStatus', 'Value': 'QUARANTINE'},
                {'Key': 'GuardDutyFinding', 'Value': finding_type}
            ]
        )
        actions_taken.append(f'tagged_instance_{instance_id}')
    
    return {'actions': actions_taken, 'finding_type': finding_type}
PYEOF

# Zip and deploy Lambda
zip /tmp/guardduty_remediate.zip /tmp/guardduty_remediate.py

SNS_ARN=$(aws sns create-topic --name guardduty-alerts --query TopicArn --output text)

LAMBDA_ARN=$(aws lambda create-function \
  --function-name guardduty-auto-remediate \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/lambda-guardduty-role" \
  --handler guardduty_remediate.lambda_handler \
  --zip-file fileb:///tmp/guardduty_remediate.zip \
  --environment "Variables={SNS_TOPIC_ARN=$SNS_ARN}" \
  --query 'FunctionArn' \
  --output text)

# Create EventBridge rule for HIGH GuardDuty findings
aws events put-rule \
  --name "guardduty-high-findings" \
  --event-pattern '{
    "source": ["aws.guardduty"],
    "detail-type": ["GuardDuty Finding"],
    "detail": {
      "severity": [{"numeric": [">=", 7.0]}]
    }
  }' \
  --state ENABLED \
  --description "Trigger remediation for HIGH GuardDuty findings"

# Add Lambda as target
aws events put-targets \
  --rule "guardduty-high-findings" \
  --targets "[{\"Id\": \"1\", \"Arn\": \"$LAMBDA_ARN\"}]"

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name guardduty-auto-remediate \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com
```

---

## 6. Configure Finding Suppression Rules

```bash
# Suppress known false positives (e.g., your own pen-test IP)
aws guardduty create-filter \
  --detector-id $DETECTOR_ID \
  --name "suppress-known-pentest-ip" \
  --action SUPPRESS \
  --description "Suppress findings from authorized penetration testing IP" \
  --finding-criteria '{
    "Criterion": {
      "service.action.networkConnectionAction.remoteIpDetails.ipAddressV4": {
        "Equals": ["203.0.113.100"]
      }
    }
  }'

# List active filters
aws guardduty list-filters \
  --detector-id $DETECTOR_ID
```

---

## 7. Security Hub Finding Aggregation

```bash
# Get all HIGH findings from Security Hub
aws securityhub get-findings \
  --filters '{
    "SeverityLabel": [{"Value": "HIGH", "Comparison": "EQUALS"},
                      {"Value": "CRITICAL", "Comparison": "EQUALS"}],
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
  }' \
  --sort-criteria '[{"Field": "LastObservedAt", "SortOrder": "desc"}]' \
  --max-results 10 \
  --query 'Findings[].{Title:Title,Severity:Severity.Label,Source:ProductName}'

# Get compliance score per standard
aws securityhub describe-standards-controls \
  --standards-subscription-arn "$(aws securityhub get-enabled-standards --query 'StandardsSubscriptions[0].StandardsSubscriptionArn' --output text)" \
  --query 'Controls[?ControlStatus==`FAILED`].{Control:ControlId,Title:Title}' \
  --max-results 10
```

---

## 8. Set Up Security Hub Insights

```bash
# Create custom insight: Count findings by source
aws securityhub create-insight \
  --name "High-Findings-By-Service" \
  --filters '{
    "SeverityLabel": [{"Value": "HIGH", "Comparison": "EQUALS"}],
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
  }' \
  --group-by-attribute "ProductName"

# List insights
aws securityhub get-insights \
  --query 'Insights[].{Name:Name,InsightArn:InsightArn}'
```

---

## 9. Enable Threat Intelligence Feeds

```bash
# Add custom threat intelligence list to GuardDuty
# Create S3 bucket for threat intel
aws s3 mb s3://guardduty-threatintel-${ACCOUNT_ID}

# Upload sample threat IP list
echo "198.51.100.1/32
198.51.100.2/32" > /tmp/threat-ips.txt

aws s3 cp /tmp/threat-ips.txt \
  s3://guardduty-threatintel-${ACCOUNT_ID}/threat-ips.txt

# Create threat intel set in GuardDuty
THREATINTEL_ID=$(aws guardduty create-threat-intel-set \
  --detector-id $DETECTOR_ID \
  --name "custom-threat-ips" \
  --format TXT \
  --location "s3://guardduty-threatintel-${ACCOUNT_ID}/threat-ips.txt" \
  --activate \
  --query 'ThreatIntelSetId' \
  --output text)

echo "Threat Intel Set: $THREATINTEL_ID"
```

---

## 10. Verify Complete Setup

```bash
echo "=== GuardDuty + Security Hub Verification ==="

# 1. GuardDuty enabled and running
aws guardduty get-detector \
  --detector-id $DETECTOR_ID \
  --query '{Status:Status,FindingPublishingFrequency:FindingPublishingFrequency}'

# 2. Findings exist
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --query 'FindingIds | length(@)'

# 3. Security Hub enabled
aws securityhub describe-hub \
  --query '{HubArn:HubArn,SubscribedAt:SubscribedAt}'

# 4. Standards enabled
aws securityhub get-enabled-standards \
  --query 'StandardsSubscriptions[].StandardsStatus'

# 5. EventBridge rule active
aws events describe-rule \
  --name "guardduty-high-findings" \
  --query '{State:State,EventPattern:EventPattern}'

echo "=== Verification Complete ==="
```

---

## Troubleshooting

**GuardDuty not generating findings:**
```bash
# GuardDuty needs ~15 minutes to analyze initial data
# Generate sample findings for immediate testing
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types "UnauthorizedAccess:EC2/SSHBruteForce"
```

**Security Hub findings not aggregating from GuardDuty:**
```bash
# Verify GuardDuty integration is enabled in Security Hub
aws securityhub list-enabled-products-for-import \
  --query 'ProductSubscriptions[]'
# Should show GuardDuty product ARN
```

**EventBridge rule not triggering Lambda:**
```bash
# Check CloudWatch Events rule invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=guardduty-high-findings \
  --start-time $(date -d '1 hour ago' --utc +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date --utc +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

---

## Expected Outcome

- ✅ GuardDuty detector active, monitoring VPC/CloudTrail/DNS
- ✅ Sample findings visible — verify all finding types load
- ✅ Security Hub aggregating findings from GuardDuty + Config
- ✅ CIS and FSBP standards showing compliance scores
- ✅ EventBridge rule triggering Lambda on HIGH severity findings
- ✅ Auto-remediation tags compromised instances, sends SNS alerts
- ✅ 30-day free trial — no cost for first month

---

## Cleanup

```bash
# Delete EventBridge rule
aws events remove-targets --rule "guardduty-high-findings" --ids "1"
aws events delete-rule --name "guardduty-high-findings"

# Delete Lambda
aws lambda delete-function --function-name guardduty-auto-remediate

# Disable Security Hub
aws securityhub disable-security-hub

# Delete GuardDuty detector
aws guardduty delete-detector --detector-id $DETECTOR_ID

# Clean up SNS
aws sns delete-topic --topic-arn $SNS_ARN

# Clean up S3
aws s3 rm s3://guardduty-threatintel-${ACCOUNT_ID} --recursive
aws s3 rb s3://guardduty-threatintel-${ACCOUNT_ID}

echo "Cleanup complete — free trial stops accumulating after disable"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
