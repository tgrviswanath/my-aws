# Verification & Validation — Project 1.1 Static Website Hosting

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| S3 Bucket | S3 → Buckets | Bucket exists, Versioning = **Enabled** |
| S3 Files | S3 → Bucket → Objects | `index.html` and `error.html` present |
| S3 Lifecycle Rule | S3 → Bucket → Management | `archive-old-versions` rule active |
| ACM Certificate | ACM → Certificates (us-east-1) | Status = **Issued** |
| CloudFront Distribution | CloudFront → Distributions | Status = **Enabled**, Last modified = recent |
| CloudFront OAC | CloudFront → Origin access | OAC attached to S3 origin |
| Route53 A Record | Route53 → Hosted zone | Alias A record pointing to CloudFront |

📸 Screenshot: S3 bucket showing Versioning = Enabled  
📸 Screenshot: ACM certificate Status = Issued  
📸 Screenshot: CloudFront distribution Status = Enabled with domain name  
📸 Screenshot: Website loading at `https://yourdomain.com` with padlock

---

## 2. AWS CLI Verification

```bash
BUCKET=your-name-static-website
DIST_ID=YOUR_DISTRIBUTION_ID

# 2.1 Bucket exists and versioning enabled
aws s3api get-bucket-versioning --bucket $BUCKET
# Expected: { "Status": "Enabled" }

# 2.2 Files uploaded
aws s3 ls s3://$BUCKET/
# Expected: index.html and error.html listed

# 2.3 CloudFront distribution enabled
aws cloudfront get-distribution --id $DIST_ID \
  --query "Distribution.{Status:Status,Domain:DomainName,Enabled:DistributionConfig.Enabled}"
# Expected: Status=Deployed, Enabled=true

# 2.4 HTTP redirects to HTTPS
curl -I http://yourdomain.com
# Expected: HTTP/1.1 301 or 302, Location: https://yourdomain.com

# 2.5 HTTPS works
curl -I https://yourdomain.com
# Expected: HTTP/2 200

# 2.6 CloudFront cache header
curl -sI https://yourdomain.com | grep -i "x-cache"
# Expected: X-Cache: Hit from cloudfront (after 2nd request)

# 2.7 Object versions exist
aws s3api list-object-versions \
  --bucket $BUCKET --prefix index.html \
  --query "Versions[*].{VersionId:VersionId,LastModified:LastModified}"
# Expected: at least 1 version listed
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_s3_bucket.website
# aws_s3_bucket_versioning.website
# aws_s3_bucket_lifecycle_configuration.website
# aws_cloudfront_distribution.website
# aws_cloudfront_origin_access_control.website
# aws_acm_certificate.website
# aws_route53_record.website

terraform state show aws_cloudfront_distribution.website
# Shows: domain_name, status=Deployed, enabled=true

terraform output
# Expected: cloudfront_url, s3_bucket_name, cloudfront_distribution_id

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check

```bash
# Full end-to-end test
curl -sI https://yourdomain.com | head -5
# Expected: HTTP/2 200, server: CloudFront

# Verify OAC — direct S3 URL must be blocked
S3_URL="https://$BUCKET.s3.amazonaws.com/index.html"
curl -sI $S3_URL
# Expected: 403 Forbidden (only CloudFront can access S3)

# Cache invalidation works
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*" \
  --query "Invalidation.{ID:Id,Status:Status}"
# Expected: Status=InProgress, then Completed
```

---

## 5. Expected Successful Outputs

**S3 versioning:**
```json
{ "Status": "Enabled" }
```

**CloudFront distribution:**
```json
{ "Status": "Deployed", "Domain": "xxxx.cloudfront.net", "Enabled": true }
```

**curl HTTPS response:**
```
HTTP/2 200
content-type: text/html
x-cache: Hit from cloudfront
via: 1.1 xxxx.cloudfront.net (CloudFront)
```

**curl HTTP (redirect):**
```
HTTP/1.1 301 Moved Permanently
Location: https://yourdomain.com/
```

---

## 6. Verification Checklist

- [ ] S3 bucket created with versioning enabled
- [ ] `index.html` and `error.html` uploaded to S3
- [ ] S3 lifecycle rule `archive-old-versions` active
- [ ] ACM certificate status = Issued (us-east-1)
- [ ] CloudFront distribution status = Deployed/Enabled
- [ ] OAC attached — direct S3 URL returns 403
- [ ] Route53 A record alias pointing to CloudFront
- [ ] `http://yourdomain.com` redirects to HTTPS (301)
- [ ] `https://yourdomain.com` returns 200
- [ ] `X-Cache: Hit from cloudfront` on second request
- [ ] `terraform plan` shows no changes
- [ ] `deploy_website.sh` runs and invalidates cache successfully

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
