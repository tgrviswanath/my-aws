# Steps — Project 1.1 Static Website Hosting

## Phase 1 — Console (Learn the concepts)

### 1.1 Create S3 Bucket
1. Go to **S3** → **Create bucket**
2. Bucket name: `your-name-static-website` (must be globally unique)
3. Region: `us-east-1`
4. **Uncheck** "Block all public access" (we'll use CloudFront OAC instead)
5. Enable **Versioning**
6. Click **Create bucket**

### 1.2 Upload Website Files
1. Create a simple `index.html`:
```html
<!DOCTYPE html>
<html>
<head><title>My AWS Static Site</title></head>
<body>
  <h1>Hello from S3 + CloudFront!</h1>
  <p>Hosted on AWS</p>
</body>
</html>
```
2. Upload `index.html` to the bucket
3. Also create and upload `error.html` for 404 pages

### 1.3 Request ACM Certificate
1. Go to **ACM** → **Request certificate** (must be in **us-east-1**)
2. Request a public certificate
3. Domain: `yourdomain.com` and `*.yourdomain.com`
4. Validation: DNS validation
5. Add the CNAME records to Route53 (ACM shows you exactly what to add)
6. Wait for status to show **Issued** (~5 minutes)

### 1.4 Create CloudFront Distribution
1. Go to **CloudFront** → **Create distribution**
2. Origin domain: select your S3 bucket
3. Origin access: **Origin access control settings (OAC)** → Create new OAC
4. Viewer protocol policy: **Redirect HTTP to HTTPS**
5. Alternate domain names (CNAMEs): `yourdomain.com`
6. Custom SSL certificate: select the ACM cert you created
7. Default root object: `index.html`
8. Click **Create distribution**
9. Copy the S3 bucket policy shown and apply it to your S3 bucket

### 1.5 Configure Route53
1. Go to **Route53** → your hosted zone
2. Create an **A record** (alias):
   - Name: `yourdomain.com`
   - Alias: Yes
   - Route traffic to: CloudFront distribution
3. Create another **A record** for `www.yourdomain.com`

### 1.6 Set Up S3 Lifecycle Policy
1. Go to S3 bucket → **Management** → **Lifecycle rules**
2. Create rule: "archive-old-versions"
3. Apply to: Previous versions
4. Transition to Glacier after 30 days
5. Delete after 365 days

---

## Phase 2 — AWS CLI

```bash
# Create bucket
aws s3 mb s3://your-name-static-website --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-name-static-website \
  --versioning-configuration Status=Enabled

# Upload files
aws s3 sync ./website/ s3://your-name-static-website/

# List bucket contents
aws s3 ls s3://your-name-static-website/

# Invalidate CloudFront cache after update
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

---

## Phase 3 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

See `terraform/main.tf` for full infrastructure code.

---

## Phase 4 — Verify

```bash
# Test HTTP redirects to HTTPS
curl -I http://yourdomain.com

# Test HTTPS
curl -I https://yourdomain.com

# Check CloudFront headers
curl -I https://yourdomain.com | grep -i "x-cache"
# Should show: X-Cache: Hit from cloudfront (after first request)

# Test versioning
aws s3api list-object-versions \
  --bucket your-name-static-website \
  --prefix index.html
```

---

## Screenshots to Take
- [ ] S3 bucket created with versioning enabled
- [ ] ACM certificate status: Issued
- [ ] CloudFront distribution deployed (status: Enabled)
- [ ] Website loading at `https://yourdomain.com`
- [ ] Browser showing valid SSL certificate
- [ ] CloudFront cache hit header in curl output
- [ ] S3 lifecycle rule configured
- [ ] `terraform apply` success output
