# AWS Console UI Steps — S3 Static Website with CloudFront CDN

> **Method:** AWS Management Console (browser-based)
> **Estimated time:** 20–30 minutes
> **Difficulty:** Beginner

---

## Prerequisites Check

Before opening the AWS Console, confirm:

- [ ] You are logged into the [AWS Console](https://console.aws.amazon.com) with an account that has S3 and CloudFront permissions
- [ ] You know which AWS region you want to use (recommend: **us-east-1** for lowest CloudFront latency)
- [ ] You have an `index.html` file ready to upload (even a simple one-liner works)
- [ ] Your browser allows pop-ups from `*.aws.amazon.com` (needed for some download dialogs)

**Quick permission check:**
- Navigate to IAM → Users → Your user → Permissions tab
- Confirm `AmazonS3FullAccess` or a custom policy with `s3:CreateBucket`, `s3:PutObject`, `cloudfront:CreateDistribution`

---

## Step 1: Create an S3 Bucket

### 1.1 — Open S3

1. In the AWS Console top search bar, type **S3**
2. Click **S3** under Services
3. Click the orange **Create bucket** button

### 1.2 — Configure Bucket Name and Region

**Bucket name rules:**
- Must be globally unique across ALL AWS accounts
- Lowercase letters, numbers, hyphens only
- 3–63 characters long
- Suggested format: `my-website-yourname-20240101`

**Fields to fill:**
| Field | Value |
|-------|-------|
| Bucket name | `my-static-site-20240101` (use your own unique name) |
| AWS Region | `US East (N. Virginia) us-east-1` |
| Object Ownership | ACLs disabled (recommended) |

### Decision Point 1: Block Public Access Settings

> **Should you block public access?**

| Option | When to use |
|--------|-------------|
| ✅ **Uncheck "Block all public access"** | When serving a public website — files MUST be publicly readable |
| Keep blocked | When the bucket contains private data (not for public websites) |

**For this project:** Uncheck all 4 checkboxes under "Block Public Access settings for this bucket"

A warning will appear: *"Turning off block all public access might result in this bucket and the objects within becoming public."* — Check the acknowledgment checkbox and proceed.

📸 **Screenshot checkpoint:** Capture the bucket creation page with Block Public Access unchecked and the acknowledgment checkbox checked.

### 1.3 — Leave Other Settings Default

- Object Ownership: ACLs disabled
- Bucket Versioning: Disable (not needed for static site)
- Default encryption: SSE-S3 (leave as default)
- Advanced settings: leave as default

### 1.4 — Create the Bucket

Click **Create bucket** at the bottom of the page.

**Expected result:** Green success banner: *"Successfully created bucket 'my-static-site-20240101'"*

📸 **Screenshot checkpoint:** S3 bucket list showing your newly created bucket.

---

### Troubleshooting — Step 1

**Error: "Bucket name already exists"**
- Bucket names are globally unique. Try adding your initials or today's date: `my-site-jd-20240115`

**Error: "Access Denied" when creating bucket**
- Your IAM user lacks `s3:CreateBucket` permission
- Go to IAM → Users → your user → Add permissions → Attach `AmazonS3FullAccess`

**Warning: "This bucket is publicly accessible"**
- This is expected for a public website. Acknowledge and proceed.

---

## Step 2: Enable Static Website Hosting

### 2.1 — Open Bucket Properties

1. Click on your newly created bucket name in the S3 bucket list
2. Click the **Properties** tab (second tab after Objects)
3. Scroll to the bottom to find **Static website hosting**

### 2.2 — Enable Static Website Hosting

1. Click **Edit** on the Static website hosting panel
2. Select **Enable**

### Decision Point 2: Index Document vs Redirect

| Option | Use Case |
|--------|----------|
| **Host a static website** ✅ | You want to serve HTML files — choose this |
| **Redirect requests** | You want to forward all traffic to another domain |

**Select: Host a static website**

**Fill in the fields:**
| Field | Value |
|-------|-------|
| Index document | `index.html` |
| Error document | `error.html` (optional but recommended) |

3. Click **Save changes**

📸 **Screenshot checkpoint:** Static website hosting section showing "Enabled" with the index document set to `index.html` and the S3 website endpoint URL visible.

**Expected Outcome:** You will see a website endpoint URL in the format:
`http://my-static-site-20240101.s3-website-us-east-1.amazonaws.com`

> **Note:** This URL uses HTTP only. HTTPS requires CloudFront (Step 4).

---

### Troubleshooting — Step 2

**Error: "Static website hosting" section is greyed out**
- Make sure you are on the **Properties** tab, not Permissions or Objects

**After enabling, the endpoint returns 403 Forbidden**
- The bucket policy hasn't been applied yet — complete Step 3 first

**After enabling, the endpoint returns 404 Not Found**
- `index.html` hasn't been uploaded yet — complete Step 3 first

---

## Step 3: Upload Website Files

### 3.1 — Apply a Bucket Policy for Public Read Access

Before uploading, you need to allow public reads:

1. Click the **Permissions** tab on your bucket
2. Scroll to **Bucket policy** → click **Edit**
3. Paste the following JSON policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-static-site-20240101/*"
    }
  ]
}
```

> ⚠️ Replace `my-static-site-20240101` with your actual bucket name.

4. Click **Save changes**

📸 **Screenshot checkpoint:** Bucket policy editor showing the public read policy saved successfully.

### 3.2 — Upload Files

1. Click the **Objects** tab
2. Click **Upload**
3. Click **Add files** → select `index.html` (and other files)
4. For folders (like `images/`): click **Add folder**
5. Click **Upload**

**For setting cache headers on individual files:**
- Click on the file after upload → Properties → Metadata
- Add: `Cache-Control` = `max-age=86400`

📸 **Screenshot checkpoint:** Objects tab showing uploaded files with their sizes and last modified dates.

**Expected Outcome:** Files visible in the Objects tab. Test the S3 website URL in a browser — you should see your site over HTTP.

---

## Step 4: Create a CloudFront Distribution

### 4.1 — Navigate to CloudFront

1. In the AWS Console search bar, type **CloudFront**
2. Click **CloudFront** under Services
3. Click **Create distribution**

### 4.2 — Configure the Origin

**Origin section:**
| Field | Value |
|-------|-------|
| Origin domain | Click the dropdown — select your S3 bucket's **website endpoint** (format: `my-static-site-20240101.s3-website-us-east-1.amazonaws.com`) |
| Protocol | HTTP only (S3 website endpoints don't support HTTPS at origin) |
| Origin path | Leave empty |
| Name | Auto-filled — leave as default |

> ⚠️ **Important:** Do NOT select the S3 bucket from the dropdown suggestions (e.g., `my-static-site-20240101.s3.amazonaws.com`). You must use the **website endpoint** URL (`.s3-website-us-east-1.amazonaws.com`). The website endpoint respects `index.html` routing; the regular S3 endpoint does not.

### 4.3 — Configure Default Cache Behavior

| Field | Value |
|-------|-------|
| Viewer protocol policy | **Redirect HTTP to HTTPS** ✅ |
| Allowed HTTP methods | GET, HEAD |
| Cache policy | **CachingOptimized** (AWS managed) |
| Compress objects automatically | Yes |

### Decision Point 3: Price Class

| Option | Edge Locations | Monthly Cost |
|--------|---------------|-------------|
| **Use only North America and Europe** | ~50 locations | Lowest ✅ |
| Use North America, Europe, Asia, Middle East, Africa | ~100 locations | Medium |
| Use all edge locations (best performance) | 400+ locations | Highest |

**For this project:** Select **Use only North America and Europe** to stay within free tier.

### 4.4 — Additional Settings

| Field | Value |
|-------|-------|
| Default root object | `index.html` |
| IPv6 | On |
| Description | `Static website for my-static-site-20240101` |

### 4.5 — Create the Distribution

Click **Create distribution**.

📸 **Screenshot checkpoint:** CloudFront distributions list showing your new distribution with status **"Deploying"** and the distribution domain name visible.

**Expected Outcome:** Distribution status changes from "Deploying" to "Enabled" after 5–15 minutes.

---

### Troubleshooting — Step 4

**Site shows "NoSuchKey" XML error**
- You selected the S3 REST endpoint instead of the S3 website endpoint as the origin
- Edit the distribution → Origins → change to the `.s3-website-us-east-1.amazonaws.com` URL

**Site loads at root `/` but subpages give 403/404**
- Add a CloudFront Function or Lambda@Edge to handle SPA routing (advanced topic)
- For simple sites, ensure all pages are uploaded as separate `.html` files

**Distribution stuck on "Deploying" for more than 30 minutes**
- This is rare. Try refreshing the page. If it persists, check Service Health Dashboard.

**CloudFront returns stale content after file update**
- Create an invalidation: CloudFront → your distribution → Invalidations tab → Create invalidation → `/*`

📸 **Screenshot checkpoint:** Browser showing your website loaded at the CloudFront HTTPS URL (`https://d1abc123xyz.cloudfront.net`) with the padlock icon visible in the address bar.

---

## Final Expected Outcome

After completing all 4 steps:

- [ ] S3 bucket exists with static website hosting enabled
- [ ] `index.html` is uploaded and publicly readable
- [ ] CloudFront distribution status is "Enabled"
- [ ] Visiting `https://<your-cf-domain>.cloudfront.net` shows your website
- [ ] Browser shows HTTPS padlock (secure connection)
- [ ] Response headers include `via: 1.1 cloudfront.net (CloudFront)`

**Your site is now:**
- Served over HTTPS globally
- Cached at CloudFront edge locations worldwide
- Ready for a custom domain (Route 53 + ACM — optional next step)
