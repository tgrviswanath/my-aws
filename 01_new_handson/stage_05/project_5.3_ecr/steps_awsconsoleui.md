# Project 5.3 — AWS Console UI Steps: Amazon ECR Deep Dive

## Prerequisites Check

- [ ] AWS Console access with ECR full permissions
- [ ] Docker installed and daemon running locally
- [ ] AWS CLI configured (for push commands — Console alone cannot push images)
- [ ] Region selected in Console (top-right corner)
- [ ] Account IDs ready for cross-account setup

---

## Step 1: Open ECR Console

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. In the top search bar, type **ECR** and click **Elastic Container Registry**
3. The default view is **Private registry**
4. If this is your first time, you'll see the "Get started" landing page

📸 Screenshot checkpoint: ECR homepage showing Private registry and Public registry tabs

---

## Step 2: Create a Private Repository

1. Click **Create repository** (top right)
2. Configure the repository:

**Repository configuration:**
- Visibility: **Private**
- Repository name: `my-app`

**Image tag mutability:**
- Select **Immutable**
- Tooltip explains: "Prevents image tags from being overwritten"

**Image scan settings:**
- ☑ Scan on push — **Enable this**
- This runs Amazon Inspector on every push automatically

**Encryption configuration:**
- Select **AES-256** (default, free)
- KMS option shown for compliance-heavy workloads

3. Click **Create repository**

📸 Screenshot checkpoint: Create repository form with name `my-app`, IMMUTABLE selected, scan on push checked

---

## Step 3: Explore the Repository Settings

1. Click on the `my-app` repository
2. Explore the left sidebar tabs:
   - **Images** — shows all pushed image tags
   - **Permissions** — resource-based policy for cross-account
   - **Lifecycle policy** — rules for auto-expiring images
   - **Replication** — copy images to other regions
   - **Settings** — tag mutability, scan configuration

📸 Screenshot checkpoint: Repository detail page showing the sidebar tabs

---

## Step 4: View Push Commands

1. Inside the `my-app` repository, click **View push commands** (top right)
2. The dialog shows 4 commands for macOS/Linux:
   - Command 1: `aws ecr get-login-password ...` 
   - Command 2: `docker build -t my-app .`
   - Command 3: `docker tag my-app:latest <URI>:latest`
   - Command 4: `docker push <URI>:latest`
3. Copy these and run them in your terminal
4. After pushing, return to the Console and refresh

📸 Screenshot checkpoint: View push commands dialog with 4 commands visible

---

## Step 5: Configure Lifecycle Policy via Console

1. In your `my-app` repository, click **Lifecycle policy** (left sidebar)
2. Click **Create rule**
3. Configure Rule 1:
   - Rule priority: `1`
   - Rule description: `Keep last 5 tagged images`
   - Image status: **Tagged**
   - Tag prefixes: enter `1` (matches tags starting with "1", e.g., 1.0.0)
   - Match criteria: **Image count more than** → `5`
   - Action: **Expire**
4. Click **Save**
5. Click **Create rule** again for Rule 2:
   - Rule priority: `2`
   - Description: `Delete untagged after 1 day`
   - Image status: **Untagged**
   - Match criteria: **Since image pushed** → `1 day`
   - Action: **Expire**
6. Click **Save**

📸 Screenshot checkpoint: Lifecycle policy showing both rules (priority 1 and 2) in the rules list

---

## Decision Point: Which Tags to Include in Lifecycle Policy

| Tag Status | Use Case | Policy Action |
|-----------|----------|--------------|
| Tagged (prefix "1") | Version releases like 1.0.0, 1.2.3 | Keep last N |
| Tagged (prefix "v") | Semver like v1.0.0, v2.1.0 | Keep last N |
| Untagged | Failed builds, intermediate layers | Expire after 1 day |
| `latest` tag | Most recent | Keep last 1 (optional) |

---

## Step 6: Set Repository Permissions for Cross-Account Pull

1. Click **Permissions** in the left sidebar
2. Click **Edit policy JSON**
3. Paste the following policy (replace `TRUSTED_ACCOUNT_ID` with actual account):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCrossAccountPull",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::TRUSTED_ACCOUNT_ID:root"
      },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ]
    }
  ]
}
```

4. Click **Save**

📸 Screenshot checkpoint: Permissions tab showing the cross-account policy JSON

---

## Step 7: View Pushed Images and Scan Results

After pushing images from your terminal:

1. In the `my-app` repository, click **Images**
2. You see a table with columns:
   - Image tag (e.g., `1.0.0`, `latest`)
   - Pushed at
   - Size
   - Scan status: `Complete`, `In Progress`, `Failed`
3. Click on an image's digest to view scan details
4. Navigate to the **Scan findings** tab
5. Review findings grouped by severity: CRITICAL, HIGH, MEDIUM, LOW

📸 Screenshot checkpoint: Images list showing multiple tags with scan status "Complete"

📸 Screenshot checkpoint: Scan findings tab showing severity breakdown (ideally 0 CRITICAL)

---

## Step 8: Test Lifecycle Policy Preview (CLI Only)

The Console does not show a live preview of what lifecycle rules would expire. Use the CLI:

```bash
aws ecr get-lifecycle-policy-preview \
  --repository-name my-app \
  --region us-east-1
```

Note: Preview requires a prior initiation via CLI. This is normal — lifecycle policy preview is a CLI-only feature.

📸 Screenshot checkpoint: CLI terminal output showing lifecycle policy preview results

---

## Step 9: Monitor Repository with CloudWatch

1. Go to **CloudWatch** → **Metrics** → **ECR**
2. Available metrics:
   - `RepositoryPullCount` — how many times images were pulled
   - `StorageBytes` — current storage usage
3. Create an alarm if StorageBytes exceeds 400MB (approaching free tier limit):
   - Metric: `AWS/ECR` → `StorageBytes`
   - Threshold: 419430400 (400MB in bytes)
   - Action: SNS notification

📸 Screenshot checkpoint: CloudWatch metrics showing ECR StorageBytes metric

---

## Step 10: Cleanup via Console

1. Go to ECR → Repositories
2. Check the box next to `my-app`
3. Click **Delete** (top right)
4. In the confirmation dialog, type `delete`
5. Click **Delete**

⚠️ This permanently deletes all images in the repository.

📸 Screenshot checkpoint: Delete repository confirmation dialog

---

## Troubleshooting

**Can't find the repository after creation:**
- Verify the region in the Console matches where you created it
- ECR is regional — `us-east-1` and `us-west-2` are separate registries

**Lifecycle policy not expiring old images:**
- Normal — lifecycle policies run at most once per day
- They only expire images that match the rule at the time of evaluation
- There is no manual trigger button in the Console

**Scan shows "SCAN_ELIGIBILITY_EXPIRED":**
- ECR basic scanning (non-Enhanced) results expire after 30 days
- Re-push or manually trigger a new scan to get fresh results

**Permission policy shows "Invalid JSON":**
- Use the JSON validator in the policy editor
- Ensure account IDs are 12-digit numbers (no dashes)
- `Principal.AWS` must be a full ARN: `arn:aws:iam::123456789012:root`
