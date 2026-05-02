# AWS GuardDuty, Security Hub, Config & Macie

## AWS GuardDuty — Threat Detection

GuardDuty is a managed threat detection service that continuously monitors for malicious activity using ML, anomaly detection, and threat intelligence.

```
Data Sources:
├── VPC Flow Logs (network traffic analysis)
├── CloudTrail (API call analysis)
├── DNS Logs (domain reputation)
├── EKS Audit Logs (Kubernetes threats)
├── S3 Data Events (data access anomalies)
├── RDS Login Events (database threats)
└── Lambda Network Activity (serverless threats)

Finding Types:
├── Backdoor:EC2/C&CActivity.B (command & control)
├── CryptoCurrency:EC2/BitcoinTool.B (crypto mining)
├── Trojan:EC2/BlackholeTraffic (malware)
├── UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B
├── Recon:EC2/PortProbeUnprotectedPort
└── Policy:S3/BucketPublicAccessGranted
```

### Enable and Configure

```bash
# Enable GuardDuty
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --data-sources '{
    "S3Logs": {"Enable": true},
    "Kubernetes": {"AuditLogs": {"Enable": true}},
    "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": true}}
  }'

DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# List findings (high severity)
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{
    "Criterion": {
      "severity": {"Gte": 7},
      "service.archived": {"Eq": ["false"]}
    }
  }' \
  --sort-criteria '{"AttributeName": "severity", "OrderBy": "DESC"}'

# Get finding details
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $FINDING_ID \
  --query 'Findings[0].{Type:Type,Severity:Severity,Description:Description,Resource:Resource}'

# Archive finding (after investigation)
aws guardduty archive-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $FINDING_ID

# Create suppression rule (reduce noise)
aws guardduty create-filter \
  --detector-id $DETECTOR_ID \
  --name "suppress-known-scanner" \
  --action ARCHIVE \
  --finding-criteria '{
    "Criterion": {
      "type": {"Eq": ["Recon:EC2/PortProbeUnprotectedPort"]},
      "service.action.networkConnectionAction.remoteIpDetails.ipAddressV4": {
        "Eq": ["203.0.113.0/24"]
      }
    }
  }'
```

### Automated Response with EventBridge + Lambda

```python
# Lambda: auto-isolate compromised EC2 instance
import boto3
import json

ec2 = boto3.client('ec2')
sns = boto3.client('sns')

def handler(event, context):
    """Triggered by EventBridge when GuardDuty finding severity >= 7"""
    detail = event['detail']
    finding_type = detail['type']
    severity = detail['severity']

    # Extract affected resource
    resource = detail.get('resource', {})
    instance_id = resource.get('instanceDetails', {}).get('instanceId')

    if not instance_id:
        print(f"No EC2 instance in finding: {finding_type}")
        return

    print(f"High severity finding: {finding_type} (severity: {severity}) on {instance_id}")

    # Isolate instance: apply restrictive security group
    isolation_sg = create_isolation_sg(instance_id)
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[isolation_sg]
    )

    # Create forensic snapshot
    volumes = get_instance_volumes(instance_id)
    for vol_id in volumes:
        ec2.create_snapshot(
            VolumeId=vol_id,
            Description=f"Forensic snapshot - GuardDuty finding {detail['id']}"
        )

    # Notify security team
    sns.publish(
        TopicArn=os.environ['SECURITY_TOPIC_ARN'],
        Subject=f"🚨 GuardDuty: {finding_type}",
        Message=json.dumps({
            'finding': finding_type,
            'severity': severity,
            'instance': instance_id,
            'action': 'Instance isolated, forensic snapshot created',
            'findingId': detail['id']
        }, indent=2)
    )

def create_isolation_sg(instance_id: str) -> str:
    vpc_id = ec2.describe_instances(
        InstanceIds=[instance_id]
    )['Reservations'][0]['Instances'][0]['VpcId']

    sg = ec2.create_security_group(
        GroupName=f'isolation-{instance_id}',
        Description='Isolation SG - GuardDuty response',
        VpcId=vpc_id
    )
    # No inbound or outbound rules = complete isolation
    return sg['GroupId']

def get_instance_volumes(instance_id: str) -> list:
    instance = ec2.describe_instances(
        InstanceIds=[instance_id]
    )['Reservations'][0]['Instances'][0]
    return [bdm['Ebs']['VolumeId'] for bdm in instance.get('BlockDeviceMappings', [])]
```

```bash
# EventBridge rule to trigger Lambda on high-severity findings
aws events put-rule \
  --name guardduty-high-severity \
  --event-pattern '{
    "source": ["aws.guardduty"],
    "detail-type": ["GuardDuty Finding"],
    "detail": {
      "severity": [{"numeric": [">=", 7]}]
    }
  }' \
  --state ENABLED

aws events put-targets \
  --rule guardduty-high-severity \
  --targets '[{
    "Id": "IsolateInstance",
    "Arn": "arn:aws:lambda:us-east-1:123456789:function:guardduty-response"
  }]'
```

---

## AWS Security Hub — Centralized Security

Security Hub aggregates findings from GuardDuty, Inspector, Macie, IAM Access Analyzer, Firewall Manager, and third-party tools.

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards \
  --tags Environment=production

# Enable specific standards
aws securityhub batch-enable-standards \
  --standards-subscription-requests \
    StandardsArn=arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0 \
    StandardsArn=arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.2.0 \
    StandardsArn=arn:aws:securityhub:us-east-1::standards/pci-dss/v/3.2.1

# Get security score
aws securityhub describe-hub \
  --query 'SecurityScore'

# Get failed controls
aws securityhub get-findings \
  --filters '{
    "ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}],
    "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}],
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
  }' \
  --sort-criteria '[{"Field": "SeverityLabel", "SortOrder": "desc"}]' \
  --max-results 20 \
  --query 'Findings[*].{Title:Title,Severity:Severity.Label,Resource:Resources[0].Id}'

# Suppress a finding (known exception)
aws securityhub batch-update-findings \
  --finding-identifiers Id=$FINDING_ID,ProductArn=$PRODUCT_ARN \
  --workflow Status=SUPPRESSED \
  --note Text="Known exception - approved by security team",UpdatedBy=security@company.com
```

---

## AWS Config — Compliance & Configuration History

Config records configuration changes to AWS resources and evaluates them against compliance rules.

```bash
# Enable Config recorder
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456789:role/config-role",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

# Create S3 delivery channel
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "my-config-bucket",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

# Start recording
aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# Deploy managed rules
RULES=(
  "ENCRYPTED_VOLUMES"
  "RDS_STORAGE_ENCRYPTED"
  "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  "S3_BUCKET_PUBLIC_WRITE_PROHIBITED"
  "IAM_ROOT_ACCESS_KEY_CHECK"
  "MFA_ENABLED_FOR_IAM_CONSOLE_ACCESS"
  "RESTRICTED_INCOMING_TRAFFIC"
  "VPC_FLOW_LOGS_ENABLED"
  "CLOUD_TRAIL_ENABLED"
  "GUARDDUTY_ENABLED_CENTRALIZED"
)

for RULE in "${RULES[@]}"; do
  aws configservice put-config-rule \
    --config-rule "{
      \"ConfigRuleName\": \"$RULE\",
      \"Source\": {
        \"Owner\": \"AWS\",
        \"SourceIdentifier\": \"$RULE\"
      }
    }"
  echo "Enabled rule: $RULE"
done

# Check compliance
aws configservice describe-compliance-by-config-rule \
  --query 'ComplianceByConfigRules[?Compliance.ComplianceType==`NON_COMPLIANT`].{Rule:ConfigRuleName,Type:Compliance.ComplianceType}' \
  --output table

# Get non-compliant resources for a rule
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name S3_BUCKET_PUBLIC_READ_PROHIBITED \
  --compliance-types NON_COMPLIANT \
  --query 'EvaluationResults[*].{Resource:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,Status:ComplianceType}'

# Auto-remediation with SSM Automation
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisableS3BucketPublicReadWrite",
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 60,
    "Parameters": {
      "AutomationAssumeRole": {
        "StaticValue": {"Values": ["arn:aws:iam::123456789:role/config-remediation-role"]}
      },
      "S3BucketName": {
        "ResourceValue": {"Value": "RESOURCE_ID"}
      }
    }
  }]'
```

---

## Amazon Macie — Sensitive Data Discovery

Macie uses ML to discover and protect sensitive data in S3.

```bash
# Enable Macie
aws macie2 enable-macie \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED

# Create classification job
aws macie2 create-classification-job \
  --job-type ONE_TIME \
  --name "pii-scan-prod-buckets" \
  --s3-job-definition '{
    "bucketDefinitions": [{
      "accountId": "123456789",
      "buckets": ["prod-user-data", "prod-uploads"]
    }]
  }' \
  --managed-data-identifier-selector ALL

# Get findings
aws macie2 list-findings \
  --finding-criteria '{
    "criterion": {
      "severity.description": {
        "eq": ["High", "Critical"]
      }
    }
  }' \
  --sort-criteria '{"attributeName": "severity.score", "orderBy": "DESC"}'

# Get finding details
aws macie2 get-findings \
  --finding-ids $FINDING_ID \
  --query 'findings[0].{Type:type,Severity:severity.description,Bucket:resourcesAffected.s3Bucket.name,Object:resourcesAffected.s3Object.key}'
```

---

## Security Best Practices Checklist

```bash
#!/bin/bash
# Quick security audit script

echo "=== AWS Security Audit ==="

# 1. Check root account MFA
echo "Root MFA:"
aws iam get-account-summary \
  --query 'SummaryMap.AccountMFAEnabled'

# 2. Check for access keys on root
echo "Root access keys:"
aws iam list-access-keys \
  --query 'AccessKeyMetadata[?UserName==`root`]'

# 3. Check password policy
echo "Password policy:"
aws iam get-account-password-policy \
  --query 'PasswordPolicy.{MinLength:MinimumPasswordLength,MFA:HardExpiry,Reuse:PasswordReusePrevention}'

# 4. Check public S3 buckets
echo "Public S3 buckets:"
aws s3api list-buckets --query 'Buckets[*].Name' --output text | \
  tr '\t' '\n' | while read BUCKET; do
    PUBLIC=$(aws s3api get-public-access-block \
      --bucket $BUCKET \
      --query 'PublicAccessBlockConfiguration.BlockPublicAcls' \
      --output text 2>/dev/null || echo "ERROR")
    if [ "$PUBLIC" != "True" ]; then
      echo "  WARNING: $BUCKET may have public access"
    fi
  done

# 5. Check GuardDuty status
echo "GuardDuty enabled:"
aws guardduty list-detectors --query 'DetectorIds' --output text

# 6. Check CloudTrail
echo "CloudTrail trails:"
aws cloudtrail describe-trails \
  --query 'trailList[*].{Name:Name,MultiRegion:IsMultiRegionTrail,LogValidation:LogFileValidationEnabled}'

# 7. Check Security Hub score
echo "Security Hub score:"
aws securityhub describe-hub --query 'SecurityScore' 2>/dev/null || echo "Not enabled"
```

---

## Interview Q&A

### Q1: What is the difference between GuardDuty, Security Hub, and Config?
**GuardDuty**: Threat detection — finds active threats (malware, compromised credentials, crypto mining) using ML on VPC Flow Logs, CloudTrail, DNS. Answers "Is something bad happening right now?"
**Security Hub**: Aggregates findings from GuardDuty, Inspector, Macie, and others. Provides compliance scores against CIS, PCI-DSS, AWS FSBP. Answers "What is my overall security posture?"
**Config**: Configuration compliance — records resource configurations over time, evaluates against rules. Answers "Are my resources configured correctly?" and "What changed?"

### Q2: How do you respond to a GuardDuty finding of a compromised EC2 instance?
1. Isolate: Apply restrictive security group (no inbound/outbound) to prevent lateral movement
2. Preserve evidence: Create EBS snapshots for forensic analysis
3. Investigate: Analyze VPC Flow Logs, CloudTrail, and instance logs
4. Revoke credentials: Rotate any IAM credentials the instance had access to
5. Remediate: Terminate compromised instance, launch clean replacement from known-good AMI
6. Post-mortem: Determine root cause, update security controls to prevent recurrence
Automate steps 1-3 with EventBridge + Lambda for faster response.

### Q3: What is AWS Config auto-remediation?
Config can automatically fix non-compliant resources using SSM Automation documents. When a resource violates a rule (e.g., S3 bucket has public access), Config triggers an SSM Automation runbook that fixes it (e.g., disables public access). Configure with `MaximumAutomaticAttempts` and `RetryAttemptSeconds`. Use carefully in production — test in dev first. Some remediations may cause disruption.

### Q4: How does Amazon Macie help with data security?
Macie uses ML to automatically discover and classify sensitive data (PII, financial data, credentials) in S3 buckets. It identifies: credit card numbers, SSNs, API keys, passwords in files. Generates findings when sensitive data is found in publicly accessible buckets or shared with external accounts. Use for: GDPR/HIPAA compliance, data loss prevention, understanding what sensitive data you have and where it lives.
