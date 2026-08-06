# Project 1.1 — S3 Static Website with CloudFront CDN

## 1. Overview

**Problem:** You have a static website (HTML/CSS/JS) and need to host it publicly on the internet without managing a server, paying for EC2 compute, or worrying about scaling.

**Solution:** Amazon S3 stores the files and serves them as a static website. CloudFront sits in front as a CDN, providing HTTPS, global edge caching, and a clean URL.

**Objectives:**
- Enable S3 static website hosting on a new bucket
- Upload HTML/CSS/JS files to the bucket
- Create a CloudFront distribution pointing to the S3 origin
- Access the site over HTTPS via the CloudFront domain
- (Optional) Attach a custom domain with Route 53

**Expected Result:** A publicly accessible HTTPS URL like `https://d1abc123xyz.cloudfront.net` serving your static site globally.

---

## 2. Architecture

```
User (Browser)
      │
      ▼ HTTPS (port 443)
┌─────────────────────┐
│   Amazon CloudFront  │  ← Global CDN, 400+ edge locations
│   (Distribution)     │    Caches static assets at the edge
└──────────┬──────────┘
           │ origin fetch (HTTPS)
           ▼
┌─────────────────────┐
│    Amazon S3 Bucket  │  ← Object storage, static website hosting enabled
│  (us-east-1 or      │    index.html, style.css, app.js, images/
│   your region)       │
└─────────────────────┘
```

**Data Flow:**
1. First request: CloudFront edge cache miss → fetches from S3 origin → caches at edge
2. Subsequent requests: CloudFront serves from edge cache (low latency globally)
3. Cache invalidation: Manual via `aws cloudfront create-invalidation` or TTL expiry

**Key AWS Services Used:**
| Service | Role | Cost |
|---------|------|------|
| S3 | File storage + static hosting origin | Free tier: 5 GB storage, 20K GET |
| CloudFront | HTTPS CDN, global distribution | Free tier: 1 TB data transfer/month |
| Route 53 | (Optional) Custom domain DNS | $0.50/hosted zone/month |
| ACM | (Optional) SSL certificate for custom domain | Free |

---

## 3. Prerequisites

### AWS Account & Permissions
- [ ] AWS account with billing enabled
- [ ] IAM user or role with the following permissions:
  - `s3:CreateBucket`, `s3:PutObject`, `s3:PutBucketWebsite`, `s3:PutBucketPolicy`
  - `cloudfront:CreateDistribution`, `cloudfront:CreateInvalidation`
- [ ] AWS CLI installed and configured (`aws configure`)

### Local Tools
- [ ] AWS CLI v2 installed: `aws --version`
- [ ] A text editor for creating HTML files
- [ ] `curl` or a browser to verify the deployment

### Files Ready
- [ ] `index.html` — main page (required)
- [ ] `error.html` — custom 404 page (recommended)
- [ ] CSS, JS, image assets (optional)

### Verify AWS CLI is configured:
```bash
aws sts get-caller-identity
# Expected: JSON with your Account ID and UserId
```

---

## 4. Folder Structure

```
project_1.1_static_website/
├── GUIDE.md                    ← This file
├── steps_awsconsoleui.md       ← Console walkthrough
├── website/                    ← Your website files
│   ├── index.html              ← Main page (required)
│   ├── error.html              ← Custom error page
│   ├── style.css               ← Stylesheet
│   ├── app.js                  ← JavaScript
│   └── images/                 ← Image assets
│       └── logo.png
└── scripts/
    ├── deploy.sh               ← CLI deployment script
    └── cleanup.sh              ← Cleanup script
```

**Sample `index.html`:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My AWS Static Site</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Hello from S3 + CloudFront!</h1>
    <p>This site is hosted on Amazon S3 and served via CloudFront CDN.</p>
    <script src="app.js"></script>
</body>
</html>
```

---

## 5. Implementation

### Decision Point 1: S3-Only vs S3 + CloudFront

| Feature | S3 Static Website Only | S3 + CloudFront ✅ Recommended |
|---------|----------------------|-------------------------------|
| Protocol | HTTP only | HTTPS ✅ |
| Custom domain | Difficult (CNAME limitations) | Easy with ACM + Route 53 ✅ |
| Global performance | Single region | 400+ edge locations ✅ |
| DDoS protection | None | AWS Shield Standard ✅ |
| Cost | Slightly cheaper | Free tier covers most use cases ✅ |
| Cache control | None | Full cache control headers ✅ |

**Decision:** Use S3 + CloudFront for any production or portfolio site.

---

### Prerequisites Check

Before starting implementation, verify:

```bash
# 1. AWS CLI is configured
aws sts get-caller-identity

# 2. Check S3 permissions
aws s3 ls  # Should list buckets without error

# 3. Check CloudFront permissions
aws cloudfront list-distributions  # Should return distribution list

# 4. Confirm your region
aws configure get region
```

---

### 5A. Console Implementation

See `steps_awsconsoleui.md` for the full AWS Console walkthrough with screenshots.

**High-level Console steps:**
1. S3 → Create bucket → unique name (e.g., `my-site-20240101`)
2. Bucket → Permissions → Uncheck "Block all public access"
3. Bucket → Properties → Static website hosting → Enable → `index.html`
4. Bucket → Permissions → Bucket policy → paste public read policy
5. Upload `index.html` and all website files
6. CloudFront → Create distribution → S3 bucket origin → HTTPS only
7. Copy CloudFront domain name → test in browser

---

### 5B. CLI Implementation

#### Step 1: Set Variables

```bash
# Set your variables
BUCKET_NAME="my-static-site-$(date +%Y%m%d%H%M%S)"
REGION="us-east-1"
WEBSITE_DIR="./website"

echo "Bucket name: $BUCKET_NAME"
```

#### Step 2: Create S3 Bucket

```bash
# Create the bucket (us-east-1 does not need LocationConstraint)
aws s3 mb s3://$BUCKET_NAME --region $REGION

# For other regions:
# aws s3 mb s3://$BUCKET_NAME --region ap-southeast-1 \
#   --create-bucket-configuration LocationConstraint=ap-southeast-1

echo "✅ Bucket created: $BUCKET_NAME"
```

#### Step 3: Disable Block Public Access

```bash
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "✅ Public access block disabled"
```

#### Step 4: Enable Static Website Hosting

```bash
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document error.html

echo "✅ Static website hosting enabled"
echo "S3 website URL: http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
```

#### Step 5: Apply Bucket Policy (Public Read)

```bash
cat > /tmp/bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket $BUCKET_NAME \
  --policy file:///tmp/bucket-policy.json

echo "✅ Bucket policy applied"
```

#### Step 6: Upload Website Files

```bash
# Upload all files recursively
aws s3 cp $WEBSITE_DIR s3://$BUCKET_NAME/ --recursive

# Optional: set cache-control headers for CSS/JS
aws s3 cp $WEBSITE_DIR/style.css s3://$BUCKET_NAME/style.css \
  --cache-control "max-age=86400"

aws s3 cp $WEBSITE_DIR/app.js s3://$BUCKET_NAME/app.js \
  --cache-control "max-age=86400"

# Verify upload
aws s3 ls s3://$BUCKET_NAME/

echo "✅ Files uploaded"
```

#### Step 7: Create CloudFront Distribution

```bash
cat > /tmp/cf-distribution.json << EOF
{
  "CallerReference": "static-site-$(date +%s)",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-$BUCKET_NAME",
        "DomainName": "$BUCKET_NAME.s3-website-$REGION.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only"
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-$BUCKET_NAME",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "Compress": true
  },
  "Comment": "Static website distribution",
  "DefaultRootObject": "index.html",
  "Enabled": true,
  "PriceClass": "PriceClass_100",
  "HttpVersion": "http2"
}
EOF

DISTRIBUTION=$(aws cloudfront create-distribution \
  --distribution-config file:///tmp/cf-distribution.json)

CF_ID=$(echo $DISTRIBUTION | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['Id'])")
CF_DOMAIN=$(echo $DISTRIBUTION | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['DomainName'])")

echo "✅ CloudFront distribution created"
echo "Distribution ID: $CF_ID"
echo "CloudFront URL: https://$CF_DOMAIN"
```

#### Step 8: Wait for Deployment

```bash
echo "Waiting for CloudFront deployment (this takes 5-15 minutes)..."
aws cloudfront wait distribution-deployed --id $CF_ID
echo "✅ CloudFront distribution deployed!"
```

---

## 6. Code Deep Dive

### Bucket Policy JSON Explained

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",      // Statement ID (human-readable label)
      "Effect": "Allow",                  // Allow this action
      "Principal": "*",                   // Anyone (public internet)
      "Action": "s3:GetObject",           // Only GET objects (read-only)
      "Resource": "arn:aws:s3:::my-bucket/*"  // All objects in the bucket
    }
  ]
}
```

**Why `Principal: "*"`?** For a public website, anyone on the internet must be able to read files. This policy only grants `GetObject` — no delete, upload, or list permissions.

### CloudFront Distribution Config Key Fields

```json
{
  "ViewerProtocolPolicy": "redirect-to-https",  // Force HTTPS
  "PriceClass": "PriceClass_100",               // US/EU/Asia edge locations only (cheapest)
  // PriceClass_All = all locations (most expensive)
  "Compress": true,                             // Gzip/Brotli compression
  "DefaultRootObject": "index.html",            // Serve index.html at /
  "CachePolicyId": "658327ea-..."               // AWS managed CachingOptimized policy
}
```

### CloudFront Cache Invalidation

```bash
# Invalidate specific files after an update
aws cloudfront create-invalidation \
  --distribution-id $CF_ID \
  --paths "/index.html" "/style.css"

# Invalidate everything (use sparingly — first 1000 paths/month are free)
aws cloudfront create-invalidation \
  --distribution-id $CF_ID \
  --paths "/*"
```

---

## 7. Verification

### Test S3 Origin (HTTP)
```bash
curl -I "http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
# Expected: HTTP/1.1 200 OK
```

### Test CloudFront (HTTPS)
```bash
curl -I "https://$CF_DOMAIN"
# Expected:
# HTTP/2 200
# x-cache: Hit from cloudfront  ← (second request, from cache)
# via: 1.1 abc123.cloudfront.net (CloudFront)
```

### List CloudFront Distributions
```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].[Id,DomainName,Status]' \
  --output table
```

### Check Distribution Status
```bash
aws cloudfront get-distribution --id $CF_ID \
  --query 'Distribution.Status'
# Expected: "Deployed"
```

### List Uploaded Files
```bash
aws s3 ls s3://$BUCKET_NAME/ --recursive --human-readable
```

---

## 8. Observations

### CDN Caching Behavior

**`x-cache` header values from CloudFront:**
- `Miss from cloudfront` — first request, fetched from S3 origin
- `Hit from cloudfront` — served from edge cache (fast!)
- `RefreshHit from cloudfront` — cache was expired, refreshed from origin

**Default TTL behavior:**
- S3 objects without `Cache-Control` headers: CloudFront uses its default TTL (24 hours)
- Set `Cache-Control: max-age=31536000` for fingerprinted assets (never expire)
- Set `Cache-Control: no-cache` for `index.html` (always fresh)

### Performance Observations

```bash
# Measure latency — run from different regions to see CDN benefit
time curl -s "https://$CF_DOMAIN/index.html" > /dev/null

# Compare origin vs CDN response time
time curl -s "http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com/index.html" > /dev/null
```

### Origin vs Edge Cache
- S3 origin: single region latency (e.g., 50-200ms from Europe if bucket is in us-east-1)
- CloudFront edge: near-local latency (5-30ms from the nearest edge location)

---

## 9. Screenshots

Capture and save screenshots at these key steps:

1. S3 bucket created with static website hosting enabled
2. Bucket policy showing public read access
3. File listing in S3 console after upload
4. CloudFront distribution creation summary page
5. CloudFront distribution status showing "Deployed"
6. Browser showing the website loaded over HTTPS with CloudFront domain
7. Browser DevTools → Network tab showing `x-cache: Hit from cloudfront`

Save screenshots to: `./screenshots/` folder in this project directory.

---

## 10. Cleanup

**Important:** Delete resources in the correct order to avoid errors.

### Step 1: Disable CloudFront Distribution (required before deletion)

```bash
# Get the current ETag (required for updates)
ETAG=$(aws cloudfront get-distribution --id $CF_ID \
  --query 'ETag' --output text)

# Get current config and disable it
aws cloudfront get-distribution-config --id $CF_ID \
  --query 'DistributionConfig' > /tmp/cf-config-disable.json

# Edit the config: set "Enabled": false
# (use sed or manually edit)
sed -i 's/"Enabled": true/"Enabled": false/' /tmp/cf-config-disable.json

aws cloudfront update-distribution \
  --id $CF_ID \
  --distribution-config file:///tmp/cf-config-disable.json \
  --if-match $ETAG

echo "Waiting for distribution to be disabled..."
aws cloudfront wait distribution-deployed --id $CF_ID
```

### Step 2: Delete CloudFront Distribution

```bash
ETAG=$(aws cloudfront get-distribution --id $CF_ID \
  --query 'ETag' --output text)

aws cloudfront delete-distribution --id $CF_ID --if-match $ETAG
echo "✅ CloudFront distribution deleted"
```

### Step 3: Empty and Delete S3 Bucket

```bash
# Empty the bucket first
aws s3 rm s3://$BUCKET_NAME --recursive

# Delete the bucket
aws s3 rb s3://$BUCKET_NAME --force

echo "✅ S3 bucket deleted"
```

### Verify Cleanup

```bash
aws s3 ls | grep $BUCKET_NAME          # Should return nothing
aws cloudfront list-distributions      # Should not list your distribution
```

### Expected Outcome After Cleanup
- No S3 bucket with your site name
- No CloudFront distribution
- No ongoing charges (one-time data transfer charges may appear on next bill)

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
