# KMS, Secrets Manager, WAF & Shield — Security Services

## AWS KMS — Key Management Service

KMS manages encryption keys. Integrated with 100+ AWS services.

### Key Types

| Type | Key Material | Rotation | Use Case |
|------|-------------|---------|---------|
| AWS Managed | AWS generates | Auto (annual) | Default for AWS services |
| Customer Managed | AWS generates | Manual or auto | Custom encryption needs |
| Customer Managed (imported) | You provide | Manual only | Compliance, bring-your-own-key |
| AWS Owned | AWS generates | AWS managed | Multi-tenant services |

### KMS Operations

```bash
# Create CMK
KEY_ID=$(aws kms create-key \
  --description "Production data encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "Enable IAM User Permissions",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789:root"},
        "Action": "kms:*",
        "Resource": "*"
      },
      {
        "Sid": "Allow EC2 App Role to use key",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789:role/AppRole"},
        "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
        "Resource": "*"
      }
    ]
  }' \
  --query 'KeyMetadata.KeyId' --output text)

# Create alias
aws kms create-alias \
  --alias-name alias/prod-data-key \
  --target-key-id $KEY_ID

# Enable automatic rotation (annual)
aws kms enable-key-rotation --key-id $KEY_ID

# Encrypt data
aws kms encrypt \
  --key-id alias/prod-data-key \
  --plaintext "sensitive-data" \
  --query CiphertextBlob --output text

# Decrypt data
aws kms decrypt \
  --ciphertext-blob fileb://encrypted.bin \
  --query Plaintext --output text | base64 -d
```

### Envelope Encryption

KMS uses envelope encryption for large data:

```
1. Generate Data Key (DEK) from KMS
   → Plaintext DEK (use to encrypt data)
   → Encrypted DEK (store alongside data)

2. Encrypt data with plaintext DEK (locally, fast)
3. Discard plaintext DEK
4. Store: encrypted data + encrypted DEK

To decrypt:
1. Call KMS to decrypt the encrypted DEK
2. Use plaintext DEK to decrypt data
3. Discard plaintext DEK
```

```python
import boto3
import base64
from cryptography.fernet import Fernet

kms = boto3.client('kms')

def encrypt_data(data: bytes, key_id: str) -> dict:
    # Generate data key
    response = kms.generate_data_key(
        KeyId=key_id,
        KeySpec='AES_256'
    )
    plaintext_key = response['Plaintext']
    encrypted_key = response['CiphertextBlob']
    
    # Encrypt data locally
    f = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
    encrypted_data = f.encrypt(data)
    
    return {
        'encrypted_data': encrypted_data,
        'encrypted_key': encrypted_key
    }

def decrypt_data(encrypted_data: bytes, encrypted_key: bytes) -> bytes:
    # Decrypt the data key
    response = kms.decrypt(CiphertextBlob=encrypted_key)
    plaintext_key = response['Plaintext']
    
    # Decrypt data locally
    f = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
    return f.decrypt(encrypted_data)
```

---

## AWS Secrets Manager

Stores, rotates, and retrieves secrets (DB passwords, API keys, OAuth tokens).

### Store and Retrieve Secrets

```bash
# Create secret
aws secretsmanager create-secret \
  --name prod/myapp/database \
  --description "Production database credentials" \
  --secret-string '{
    "username": "admin",
    "password": "MySecurePassword123!",
    "host": "prod-db.cluster.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "dbname": "myapp"
  }' \
  --kms-key-id alias/prod-data-key

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id prod/myapp/database \
  --query SecretString --output text | python3 -m json.tool

# Update secret
aws secretsmanager update-secret \
  --secret-id prod/myapp/database \
  --secret-string '{"username": "admin", "password": "NewPassword456!"}'
```

### Automatic Rotation

```bash
# Enable automatic rotation (every 30 days)
aws secretsmanager rotate-secret \
  --secret-id prod/myapp/database \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789:function:SecretsManagerRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

### Python Integration (with caching)

```python
import boto3
import json
from functools import lru_cache
import time

class SecretsCache:
    def __init__(self, ttl_seconds=300):
        self.client = boto3.client('secretsmanager')
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_secret(self, secret_name: str) -> dict:
        now = time.time()
        if secret_name in self.cache:
            value, timestamp = self.cache[secret_name]
            if now - timestamp < self.ttl:
                return value
        
        response = self.client.get_secret_value(SecretId=secret_name)
        value = json.loads(response['SecretString'])
        self.cache[secret_name] = (value, now)
        return value

# Global instance (reused across Lambda invocations)
secrets = SecretsCache(ttl_seconds=300)

def get_db_connection():
    creds = secrets.get_secret('prod/myapp/database')
    return psycopg2.connect(
        host=creds['host'],
        port=creds['port'],
        database=creds['dbname'],
        user=creds['username'],
        password=creds['password']
    )
```

### Secrets Manager vs SSM Parameter Store

| Feature | Secrets Manager | SSM Parameter Store |
|---------|----------------|-------------------|
| Cost | $0.40/secret/month | Free (Standard), $0.05/advanced |
| Rotation | ✅ Built-in | ❌ Manual |
| Cross-account | ✅ | ❌ |
| Max size | 65KB | 4KB (standard), 8KB (advanced) |
| Versioning | ✅ | ✅ |
| Use case | DB passwords, API keys | Config values, feature flags |

---

## AWS WAF — Web Application Firewall

Protects web applications from common exploits (SQL injection, XSS, etc.).

### WAF Components

```
Web ACL
├── Rules (evaluated in priority order)
│   ├── AWS Managed Rule Groups
│   │   ├── AWSManagedRulesCommonRuleSet (OWASP Top 10)
│   │   ├── AWSManagedRulesSQLiRuleSet
│   │   ├── AWSManagedRulesKnownBadInputsRuleSet
│   │   └── AWSManagedRulesAmazonIpReputationList
│   ├── Custom Rules
│   │   ├── IP-based rules
│   │   ├── Rate-based rules
│   │   └── String match rules
│   └── Rule Groups (reusable)
└── Default Action (Allow/Block)
```

```bash
# Create Web ACL
aws wafv2 create-web-acl \
  --name prod-web-acl \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 1,
      "OverrideAction": {"None": {}},
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet"
      }
    },
    {
      "Name": "RateLimitRule",
      "Priority": 2,
      "Action": {"Block": {}},
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      }
    },
    {
      "Name": "BlockBadIPs",
      "Priority": 3,
      "Action": {"Block": {}},
      "Statement": {
        "IPSetReferenceStatement": {
          "ARN": "arn:aws:wafv2:us-east-1:123456789:regional/ipset/bad-ips/abc123"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "BlockedIPs"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=ProdWebACL \
  --region us-east-1

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789:regional/webacl/prod-web-acl/abc123 \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789:loadbalancer/app/my-alb/abc123
```

---

## AWS Shield — DDoS Protection

| Tier | Cost | Protection |
|------|------|-----------|
| Shield Standard | Free | L3/L4 DDoS protection (automatic) |
| Shield Advanced | $3,000/month | L3/L4/L7, DDoS cost protection, 24/7 DRT support |

```bash
# Enable Shield Advanced
aws shield create-subscription

# Add protection for ALB
aws shield create-protection \
  --name prod-alb-protection \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789:loadbalancer/app/my-alb/abc123

# Enable proactive engagement (DRT contacts you during attacks)
aws shield update-proactive-engagement --proactive-engagement-status ENABLED
```

---

## Security Best Practices Summary

```
Encryption:
├── At rest: KMS for all sensitive data (S3, EBS, RDS, DynamoDB)
├── In transit: TLS 1.2+ everywhere, enforce HTTPS
└── Key rotation: Enable automatic rotation for KMS CMKs

Secrets:
├── Never hardcode credentials in code or config
├── Use Secrets Manager for DB passwords, API keys
├── Use SSM Parameter Store for config values
└── Rotate secrets automatically

Network:
├── WAF on all public-facing ALBs and CloudFront
├── Shield Advanced for critical applications
├── VPC endpoints to keep traffic off internet
└── Security groups: least privilege, no 0.0.0.0/0 SSH

Identity:
├── MFA for all human users
├── IAM roles for all services (no access keys on EC2)
├── Permission boundaries for developer roles
└── SCPs for organization-wide guardrails
```

---

## Interview Q&A

### Q1: What is envelope encryption and why does KMS use it?
KMS uses envelope encryption because KMS can only encrypt data up to 4KB directly. For larger data: (1) KMS generates a data encryption key (DEK), (2) You encrypt your data locally with the DEK (fast, no KMS API call per record), (3) KMS encrypts the DEK itself, (4) Store encrypted data + encrypted DEK together. To decrypt: call KMS to decrypt the DEK, then decrypt data locally. Benefits: performance (one KMS call per session, not per record), cost efficiency.

### Q2: What is the difference between KMS and Secrets Manager?
**KMS**: Manages encryption keys. Used to encrypt/decrypt data. Doesn't store your data — stores keys.
**Secrets Manager**: Stores actual secret values (passwords, API keys). Uses KMS to encrypt the stored secrets. Adds rotation, versioning, cross-account access. Use KMS for encryption operations, Secrets Manager for storing and rotating credentials.

### Q3: How does WAF protect against SQL injection?
WAF inspects HTTP request components (URI, query string, headers, body) against rule patterns. The `AWSManagedRulesSQLiRuleSet` contains patterns that match SQL injection attempts (e.g., `' OR 1=1`, `UNION SELECT`, `DROP TABLE`). When matched, WAF blocks the request before it reaches your application. WAF is a complement to — not a replacement for — parameterized queries in your application code.

### Q4: What is the difference between Shield Standard and Shield Advanced?
**Standard**: Free, automatic, protects against common L3/L4 DDoS attacks (SYN floods, UDP reflection). Applied to all AWS resources automatically.
**Advanced**: $3,000/month + data transfer fees. Adds: L7 protection, DDoS cost protection (AWS credits for scaling costs during attacks), 24/7 access to AWS DDoS Response Team (DRT), attack diagnostics, proactive engagement. Use for business-critical applications.

### Q5: How do you implement secrets rotation without downtime?
Secrets Manager rotation uses a Lambda function with 4 phases: (1) `createSecret` — create new version with AWSPENDING label, (2) `setSecret` — set new credentials in the service (e.g., change DB password), (3) `testSecret` — verify new credentials work, (4) `finishSecret` — move AWSCURRENT label to new version. During rotation, both old and new credentials are valid briefly. Applications using Secrets Manager SDK automatically get the new secret after rotation.
