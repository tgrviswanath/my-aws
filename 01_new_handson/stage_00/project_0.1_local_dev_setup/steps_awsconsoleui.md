# AWS Console UI Steps — Project 0.1: Local Dev Environment Setup

> **Purpose:** Step-by-step AWS Console walkthrough with screenshots guidance  
> **Time:** 20–30 minutes  
> **Cost:** $0  

---

## Prerequisites Check

Before opening the AWS Console, confirm:

- [ ] You have an AWS account (https://aws.amazon.com/free)
- [ ] You can log in to https://console.aws.amazon.com
- [ ] You are logged in as **root user** OR an IAM user with **IAM full access**
- [ ] AWS CLI v2 is already installed locally (`aws --version` returns output)
- [ ] You have a text editor ready to paste keys

> **⚠️ Root user warning:** Using root for daily work is a security risk. We create an IAM user here specifically so you can stop using root for CLI work.

---

## Step 1 — Create IAM User

### Navigate to IAM Service

1. Open https://console.aws.amazon.com in your browser
2. In the **top search bar**, type: `IAM`
3. Click **IAM** (the first result under "Services")
4. You are now on the IAM Dashboard

### Decision Point 1: What Type of User to Create?

| Option | Use Case | Credential Type |
|--------|----------|-----------------|
| ✅ **IAM User** | Learning, personal AWS account, solo projects | Long-term access key |
| ❌ **SSO User (IAM Identity Center)** | Teams, organizations, production workloads | Short-lived token |
| ❌ **Federated identity** | Enterprise with existing identity provider | SAML/OIDC |

> **Decision for this project: IAM User** — straightforward, no extra services needed, ideal for hands-on learning.

### Create the User

1. In the left sidebar, click **Users**
2. Click the orange **Create user** button (top right of the Users page)

   **📸 Screenshot:** Capture the Users list page showing the "Create user" button

3. Fill in the user details:
   - **User name:** `cli-learning-user`
   - Console access: Leave unchecked (we only need CLI access)
4. Click **Next**

### Attach Permissions

5. On the "Set permissions" page, select **"Attach policies directly"**
6. In the policy search box, type: `AdministratorAccess`
7. Check the checkbox next to **AdministratorAccess** (AWS managed policy)

   **📸 Screenshot:** Capture the policy attachment screen with AdministratorAccess checked

8. Click **Next**
9. Review the summary:
   - User name: `cli-learning-user`
   - Permissions: AdministratorAccess
10. Click **Create user**

### Expected Outcome — Step 1

You see a green success banner:
```
User "cli-learning-user" has been created successfully.
```

The Users list now shows `cli-learning-user`.

### Troubleshooting — Step 1

| Problem | Solution |
|---------|----------|
| "You do not have permission to perform: iam:CreateUser" | Log in as root or ask your admin |
| Username already exists | Choose a different name or delete the existing user |
| Policy not found | Ensure you're searching "AdministratorAccess" exactly (camel case) |
| Console hangs on Create | Refresh page; check if user was created before retrying |

---

## Step 2 — Generate Access Key

### Navigate to User Security Credentials

1. Click on the user name **cli-learning-user** (in the Users list)
2. You are now on the user detail page
3. Click the **Security credentials** tab

   **📸 Screenshot:** Capture the Security credentials tab showing the empty Access keys section

### Decision Point 2: What Access Key Type to Create?

On the "Create access key" page, AWS asks for the use case:

| Option | Use When | Notes |
|--------|----------|-------|
| ✅ **Command Line Interface (CLI)** | Running AWS CLI from your local machine | This project |
| ❌ **Local code** | Application code running locally using SDK | Different project |
| ❌ **Application running on AWS compute** | EC2, Lambda, ECS | Use IAM roles instead — never keys |
| ❌ **Third-party service** | External tools needing AWS access | Consider short-lived tokens |

> **Decision: Command Line Interface (CLI)** — matches our use case exactly.

### Create the Key

4. Scroll to the **Access keys** section
5. Click **Create access key**
6. Select **"Command Line Interface (CLI)"**
7. Check the acknowledgment: "I understand the above recommendation and want to proceed to create an access key"
8. Click **Next**
9. Optional: Add a description tag, e.g., `local-dev-windows`
10. Click **Create access key**

### Download/Copy the Keys

**CRITICAL STEP — You only see the secret key ONCE.**

11. You now see:
    ```
    Access key:        YOUR_ACCESS_KEY_ID
    Secret access key: YOUR_SECRET_ACCESS_KEY
    ```
12. Click **Download .csv file** — save it to a secure location (NOT in a Git repo)
13. Alternatively, click the copy icons to copy each key to a password manager

    **📸 Screenshot:** Capture this page (blur/crop the actual key values before saving to notes)

14. Click **Done**

### Expected Outcome — Step 2

Back on the Security credentials tab, you see:
```
Access keys (1)
YOUR_ACCESS_KEY_ID    Active    Created just now    local-dev-windows
```

### Troubleshooting — Step 2

| Problem | Solution |
|---------|----------|
| "You have reached the maximum number of access keys" | You already have 2 keys. Delete one first. |
| Closed the dialog without copying the secret | Deactivate the key, delete it, create a new one |
| CSV file is empty | Re-download; if still empty, create a new key |
| Secret key shows asterisks | This is expected after creation — you can't retrieve it again |

---

## Step 3 — Configure AWS CLI Locally

Now switch from browser to your terminal (PowerShell or CMD).

### Run `aws configure`

```powershell
aws configure
```

Enter the values when prompted:

```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json
```

> **Region choice:** Use `us-east-1` (US East N. Virginia) for stage_00 projects. It has the broadest free tier support and lowest latency to AWS's main services.

### Verify the Configuration

```bash
# Check what was saved
aws configure list

# Output:
#       Name                    Value             Type    Location
#       ----                    -----             ----    --------
#    profile                <not set>             None    None
# access_key     ****************MPLE shared-credentials-file
# secret_key     ****************EKEY shared-credentials-file
#     region                us-east-1      config-file    ~/.aws/config

# Test the connection
aws sts get-caller-identity
```

### Expected Final Output

```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/cli-learning-user"
}
```

If you see this JSON response, your AWS CLI is fully configured and authenticated.

**📸 Screenshot:** Capture your terminal showing the `aws sts get-caller-identity` output (you can show the Account ID — it's not sensitive by itself)

### Decision Point 3: Output Format

| Format | Best For | Example |
|--------|----------|---------|
| `json` | Default, machine-readable, most complete | `{"Key": "Value"}` |
| `table` | Human reading in terminal | Pretty ASCII table |
| `text` | Scripting, grep/awk processing | Tab-separated values |
| `yaml` | CloudFormation-like readability | `Key: Value` |

> **Recommendation:** Use `json` as default. Override per-command with `--output table` when you want to read output interactively.

---

## Additional Console Verifications

### Verify the IAM User in Console

1. Return to IAM Console → Users → `cli-learning-user`
2. Click **Access Advisor** tab — shows which AWS services the user has accessed
3. After running `aws sts get-caller-identity`, you'll see "STS" listed here

### Verify Access Key Last Used

1. IAM → Users → `cli-learning-user` → **Security credentials** tab
2. Under Access keys, check the **Last used** column
3. Should show "Today" or very recent after your CLI test

---

## Console Navigation Quick Reference

| Task | Console Path |
|------|-------------|
| Create IAM user | IAM → Users → Create user |
| Create access key | IAM → Users → [username] → Security credentials → Create access key |
| Deactivate key | IAM → Users → [username] → Security credentials → Actions → Deactivate |
| Delete key | IAM → Users → [username] → Security credentials → Actions → Delete |
| View account ID | Top-right corner of console (click your username) |
| Switch region | Top-right region dropdown (IAM is global, not regional) |

---

*End of steps_awsconsoleui.md — Project 0.1*
