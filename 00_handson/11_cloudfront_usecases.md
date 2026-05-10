# CloudFront — Real-World Use Cases

## Use Case 1: CDN for React SPA with S3

**Business Problem**: React app loads slowly for users in Asia (server is in us-east-1). Need global CDN with HTTPS and custom domain.

```bash
BUCKET="my-spa-prod"
DOMAIN="app.mycompany.com"
CERT_ARN="arn:aws:acm:us-east-1:123456789:certificate/abc-123"  # Must be in us-east-1!

# 1. Create Origin Access Control (OAC) — replaces legacy OAI
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "my-spa-oac",
    "Description": "OAC for SPA bucket",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }' \
  --query 'OriginAccessControl.Id' --output text)

# 2. Create CloudFront distribution
DIST_ID=$(aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "my-spa-'$(date +%s)'",
    "Comment": "React SPA CDN",
    "DefaultRootObject": "index.html",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "s3-origin",
        "DomainName": "'$BUCKET'.s3.us-east-1.amazonaws.com",
        "S3OriginConfig": {"OriginAccessIdentity": ""},
        "OriginAccessControlId": "'$OAC_ID'"
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "s3-origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "Compress": true,
      "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
      "FunctionAssociations": {
        "Quantity": 1,
        "Items": [{
          "FunctionARN": "'$CF_FUNCTION_ARN'",
          "EventType": "viewer-request"
        }]
      }
    },
    "CacheBehaviors": {
      "Quantity": 1,
      "Items": [{
        "PathPattern": "/api/*",
        "TargetOriginId": "alb-origin",
        "ViewerProtocolPolicy": "https-only",
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"]}
      }]
    },
    "CustomErrorResponses": {
      "Quantity": 1,
      "Items": [{
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      }]
    },
    "Aliases": {"Quantity": 1, "Items": ["'$DOMAIN'"]},
    "ViewerCertificate": {
      "ACMCertificateArn": "'$CERT_ARN'",
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "Enabled": true,
    "HttpVersion": "http2and3",
    "PriceClass": "PriceClass_All"
  }' \
  --query 'Distribution.Id' --output text)

# 3. Update S3 bucket policy to allow only CloudFront
aws s3api put-bucket-policy \
  --bucket $BUCKET \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Principal\": {\"Service\": \"cloudfront.amazonaws.com\"},
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::${BUCKET}/*\",
      \"Condition\": {
        \"StringEquals\": {
          \"AWS:SourceArn\": \"arn:aws:cloudfront::123456789:distribution/${DIST_ID}\"
        }
      }
    }]
  }"

# 4. CloudFront Function for SPA routing (handle React Router)
aws cloudfront create-function \
  --name "spa-router" \
  --function-config '{"Comment": "SPA routing", "Runtime": "cloudfront-js-2.0"}' \
  --function-code 'function handler(event) {
    var request = event.request;
    var uri = request.uri;
    // If no file extension, serve index.html (React Router)
    if (!uri.includes(".")) {
      request.uri = "/index.html";
    }
    return request;
  }'

echo "CloudFront distribution: $DIST_ID"
echo "Domain: https://$DOMAIN"
```

**What you learn**: OAC (modern replacement for OAI), cache behaviors, custom error responses for SPA, CloudFront Functions.

---

## Use Case 2: Signed URLs for Private Content

**Business Problem**: Video streaming platform — only paying subscribers can access video files. URLs expire after 1 hour.

```python
import boto3
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime, timedelta
import base64

# Load CloudFront private key (stored in Secrets Manager)
def get_private_key():
    sm = boto3.client('secretsmanager')
    secret = sm.get_secret_value(SecretId='cloudfront/private-key')
    return serialization.load_pem_private_key(
        secret['SecretString'].encode(), password=None
    )

def rsa_signer(message):
    """Sign message with CloudFront private key."""
    private_key = get_private_key()
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

def generate_signed_url(video_key: str, user_id: str, expires_hours: int = 1) -> str:
    """Generate a signed URL for a private video."""
    cf_signer = CloudFrontSigner(
        key_id='APKAXXXXXXXXXX',  # CloudFront key pair ID
        rsa_signer=rsa_signer
    )

    url = f"https://videos.mycompany.com/{video_key}"
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

    signed_url = cf_signer.generate_presigned_url(
        url,
        date_less_than=expires_at
    )

    # Log access for audit
    print(f"Generated signed URL for user {user_id}: expires {expires_at}")
    return signed_url

# Usage in FastAPI
@app.get("/videos/{video_id}/stream")
async def get_stream_url(video_id: str, current_user = Depends(get_current_user)):
    # Check subscription
    if not current_user.has_active_subscription:
        raise HTTPException(403, "Subscription required")

    video_key = f"videos/{video_id}/hls/master.m3u8"
    signed_url = generate_signed_url(video_key, current_user.id, expires_hours=4)
    return {"streamUrl": signed_url}
```

**What you learn**: CloudFront signed URLs, key pairs, private content distribution.

---

## Use Case 3: WAF Integration for API Protection

```bash
# 1. Create WAF Web ACL
WAF_ARN=$(aws wafv2 create-web-acl \
  --name "api-protection" \
  --scope CLOUDFRONT \
  --region us-east-1 \
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
      "Name": "BlockBadBots",
      "Priority": 3,
      "Action": {"Block": {}},
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesBotControlRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "BotControl"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=ApiProtection \
  --query 'Summary.ARN' --output text)

# 2. Associate WAF with CloudFront distribution
aws cloudfront update-distribution \
  --id $DIST_ID \
  --if-match $(aws cloudfront get-distribution --id $DIST_ID --query 'ETag' --output text) \
  --distribution-config "$(aws cloudfront get-distribution-config \
    --id $DIST_ID \
    --query 'DistributionConfig' | \
    jq '.WebACLId = "'$WAF_ARN'"')"
```

**What you learn**: WAF managed rules, rate limiting, bot control, CloudFront + WAF integration.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| ACM certificate in wrong region | CloudFront won't accept it | Certificate MUST be in us-east-1 |
| Not invalidating cache after deploy | Users see old version | Invalidate `/*` after every deploy |
| Using OAI instead of OAC | Legacy, less secure | Use Origin Access Control (OAC) |
| Caching API responses | Stale data served | Set `CachePolicyId` to CachingDisabled for API paths |
| No custom error page for 403/404 | Broken SPA routing | Add custom error response → index.html |
| HTTP/1.1 only | Slower performance | Enable `http2and3` |
