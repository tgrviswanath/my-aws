# Project 5.1 — AWS Console UI Steps: Single Docker App → ECR

## Prerequisites Check

Before using the Console, confirm:
- [ ] AWS account access with ECR permissions
- [ ] Docker Desktop running locally
- [ ] Flask app built locally: `docker images flask-app`
- [ ] AWS CLI configured (needed for `docker login` to ECR — Console alone can't do this)
- [ ] Region selected in Console top-right (e.g., `us-east-1`)

---

## Step 1: Navigate to Amazon ECR

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com)
2. In the search bar at the top, type **ECR** and select **Elastic Container Registry**
3. You land on the ECR dashboard showing **Private registry** and **Public registry** tabs
4. Ensure you are on the **Private registry** tab

📸 Screenshot checkpoint: ECR dashboard showing "Repositories" left nav item and "Private registry" tab

---

## Step 2: Create a Private Repository

1. Click **Create repository** (orange button, top right)
2. Fill in the form:

**General settings:**
- Visibility settings: select **Private**
- Repository name: type `flask-app`

**Image tag mutability:**
- Select **Immutable**
- Reason: prevents overwriting existing tags — important for traceability

**Image scan settings:**
- Check **Scan on push** ✅
- This runs Amazon Inspector scans automatically on every push

**Encryption settings:**
- Leave as **AES-256** (default) unless you need KMS
- For learning purposes, default is fine

3. Scroll down and click **Create repository**

📸 Screenshot checkpoint: "Create repository" form filled with name `flask-app`, Immutable selected, Scan on push enabled

---

## Decision Point: Tag Mutability

| Setting | Immutable | Mutable |
|---------|-----------|---------|
| Can overwrite a tag? | ❌ No | ✅ Yes |
| Traceability | High | Lower |
| Production best practice | ✅ Yes | For dev only |

Choose **Immutable** for this project.

---

## Step 3: View Your New Repository

1. After creation, you are redirected to the repository list
2. Click on the `flask-app` repository name to open it
3. The repository is empty — no images yet
4. Note the **URI** shown at the top:
   ```
   123456789012.dkr.ecr.us-east-1.amazonaws.com/flask-app
   ```
   Copy this URI — you'll need it for tagging

📸 Screenshot checkpoint: Empty `flask-app` repository page showing the Repository URI

---

## Step 4: Get Push Commands from Console

1. In the `flask-app` repository view, click **View push commands** (top right)
2. A dialog opens with 4 commands for **macOS/Linux**:
   - Command 1: `aws ecr get-login-password ...` — authenticates Docker
   - Command 2: `docker build -t flask-app .` — builds image
   - Command 3: `docker tag flask-app:latest <URI>:latest` — tags it
   - Command 4: `docker push <URI>:latest` — pushes it
3. Copy these commands to your terminal
4. Close the dialog

📸 Screenshot checkpoint: "View push commands" modal showing all 4 commands

---

## Step 5: Execute Push Commands (Terminal)

Switch to your terminal. The Console showed you the commands — now run them:

```bash
# Step 5A — Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com
# Expected output: "Login Succeeded"

# Step 5B — Build (if not already built)
docker build -t flask-app:1.0.0 .

# Step 5C — Tag
docker tag flask-app:1.0.0 \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/flask-app:1.0.0

# Step 5D — Push
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/flask-app:1.0.0
```

Expected output during push:
```
The push refers to repository [123456789012.dkr.ecr.us-east-1.amazonaws.com/flask-app]
abc123def456: Pushed
...
1.0.0: digest: sha256:... size: 1234
```

📸 Screenshot checkpoint: Terminal showing "Login Succeeded" and push layers completing

---

## Step 6: Verify Image in Console

1. Return to the AWS Console → ECR → `flask-app` repository
2. Refresh the page (F5 or click refresh icon)
3. You should see your image listed with:
   - **Image tag**: `1.0.0`
   - **Pushed at**: recent timestamp
   - **Size**: ~100-150MB for a Python slim image
   - **Scan status**: `Complete` or `In Progress`

📸 Screenshot checkpoint: `flask-app` repository showing image with tag `1.0.0`, size, and scan status

---

## Step 7: Review Scan Results

1. In the repository, click on the image digest (or the image tag)
2. Select the **Scan findings** tab
3. Review findings by severity: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
4. For a fresh Python 3.11-slim image, you should see 0 CRITICAL findings

📸 Screenshot checkpoint: Scan findings tab showing severity breakdown

---

## Step 8: Add a Lifecycle Policy via Console

1. In the left sidebar under your `flask-app` repo, click **Lifecycle policy**
2. Click **Create rule**
3. Fill in:
   - Rule priority: `1`
   - Rule description: `Keep last 5 tagged images`
   - Image status: **Tagged**
   - Tag prefixes: `1, v`
   - Match criteria: **Image count more than** → `5`
   - Action: **Expire**
4. Click **Save**
5. Add a second rule (priority 2):
   - Description: `Remove untagged images after 1 day`
   - Image status: **Untagged**
   - Match criteria: **Since image pushed** → `1 day`
   - Action: **Expire**
6. Click **Save**

📸 Screenshot checkpoint: Lifecycle policy rules showing both rules with priorities 1 and 2

---

## Step 9: Repository Settings Review

1. In your `flask-app` repo, click the **Settings** tab (left sidebar)
2. Review:
   - Tag immutability: **Enabled**
   - Image scanning: **Enabled**
3. No changes needed — these match what we configured at creation

📸 Screenshot checkpoint: Repository settings page confirming immutability and scanning enabled

---

## Step 10: Cleanup via Console (Optional)

To delete the repository:

1. Go to ECR → Repositories
2. Check the checkbox next to `flask-app`
3. Click **Delete** (top right)
4. Type `delete` to confirm
5. Click **Delete**

⚠️ This deletes ALL images in the repository. This is irreversible.

📸 Screenshot checkpoint: Delete confirmation dialog with `delete` typed

---

## Troubleshooting

**Repository not showing after creation:**
- Verify you are in the correct AWS region (check top-right corner)
- Refresh the browser

**Push fails with "no basic auth credentials":**
- The Console can't authenticate Docker — you must run `aws ecr get-login-password` in your terminal
- Ensure AWS CLI credentials are valid: `aws sts get-caller-identity`

**Scan status shows "FAILED":**
- This can happen with very small or unusual images
- Try pushing again; if it persists, check ECR service health in your region

**Cannot see "View push commands":**
- You must be inside a specific repository (not on the Repositories list page)
- Click the repository name first, then look for the button in the top-right

**Image tag shows as `<none>`:**
- You tagged with `latest` but pushed with `1.0.0` or vice versa
- Always tag explicitly: `docker tag myimage:1.0.0 <URI>:1.0.0`
