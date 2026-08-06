# AWS Console UI Steps — IAM Security Fundamentals

> **Method:** AWS Management Console (browser-based)
> **Estimated time:** 30–40 minutes
> **Difficulty:** Beginner–Intermediate

---

## Prerequisites Check

Before opening the AWS Console, confirm:

- [ ] Logged into [AWS Console](https://console.aws.amazon.com) as root user or an IAM user with `IAMFullAccess` or `AdministratorAccess`
- [ ] MFA authenticator app installed on your phone: Google Authenticator, Authy, or Microsoft Authenticator
- [ ] You know your AWS Account ID (visible in the top-right of the console, under your username → Account)
- [ ] A notepad or password manager ready to store temporary credentials

**Important:** IAM is a **global service** — there is no region selector. IAM users, groups, roles, and policies exist globally across all regions.

---

## Step 1: Set Account Password Policy

A strong password policy enforces security for all IAM users in the account.

### 1.1 — Navigate to IAM

1. AWS Console search bar → type **IAM**
2. Click **IAM** under Services
3. Left sidebar → **Account settings**

### 1.2 — Edit Password Policy

Scroll to **Password policy** section → click **Edit**

**Configure these settings:**

| Setting | Recommended Value |
|---------|-----------------|
| Minimum password length | 12 characters |
| Require uppercase letters | ✅ Check |
| Require lowercase letters | ✅ Check |
| Require numbers | ✅ Check |
| Require special characters | ✅ Check |
| Allow users to change password | ✅ Check |
| Enable password expiration | 90 days |
| Prevent password reuse | 5 passwords |

Click **Save changes**

📸 **Screenshot checkpoint:** Account settings showing the custom password policy saved with all requirements enabled.

---

## Step 2: Create a User Group

### 2.1 — Navigate to User Groups

1. Left sidebar → **User groups**
2. Click **Create group**

### 2.2 — Configure the Group

**Group name:** `developers`

Scroll to **Attach permissions policies** section.

### Decision Point 1: Which Policy to Attach?

| Policy | What it allows | Use case |
|--------|---------------|---------|
| **ReadOnlyAccess** ✅ | `Describe*`, `List*`, `Get*` on all services | Developers who need visibility but no write access |
| PowerUserAccess | Almost everything except IAM management | Trusted developers |
| AdministratorAccess | Everything | Admins only |

**For this exercise:** Search for and select **ReadOnlyAccess** (AWS managed policy)

Click **Create group**

📸 **Screenshot checkpoint:** User groups list showing `developers` group with `ReadOnlyAccess` policy attached (visible in the Attached policies column or by clicking the group).

---

### Troubleshooting — Step 2

**Can't find "ReadOnlyAccess" in the policy list**
- Type `ReadOnly` in the filter box — it should appear as an AWS managed policy (blue icon)

**Error: "Group already exists"**
- Use a different name or delete the existing group first

---

## Step 3: Create an IAM User

### 3.1 — Navigate to Users

1. Left sidebar → **Users**
2. Click **Create user**

### 3.2 — Configure User Details

**Step 1 — Specify user details:**
| Field | Value |
|-------|-------|
| User name | `dev-user-01` |
| Provide user access to the AWS Management Console | ✅ Check |
| Console password | Custom password: choose a strong password |
| Users must create a new password at next sign-in | ✅ Check (force reset) |

Click **Next**

### 3.3 — Set Permissions

**Step 2 — Set permissions:**
- Select **Add user to group**
- Check the checkbox next to **developers**

Click **Next**

### 3.4 — Review and Create

**Step 3 — Review:**
- Confirm: User name = `dev-user-01`
- Confirm: Permissions = developers group (ReadOnlyAccess)

Click **Create user**

📸 **Screenshot checkpoint:** User creation success page showing the console sign-in URL, username, and the option to download .csv with credentials.

> ⚠️ **Important:** Download the `.csv` file or note the console sign-in URL — you'll need it to test the user.

---

### Troubleshooting — Step 3

**Error: "User name already exists"**
- Choose a different username: `dev-user-02` or `dev-alice`

**The user was created but has no way to log in**
- Go to Users → `dev-user-01` → Security credentials → Enable console access

---

## Step 4: Enable MFA for the User

MFA is critical for any human IAM user with console access.

### 4.1 — Open User Security Credentials

1. Left sidebar → **Users** → click **dev-user-01**
2. Click the **Security credentials** tab
3. Scroll to **Multi-factor authentication (MFA)**
4. Click **Assign MFA device**

### 4.2 — Configure Virtual MFA

1. **MFA device name:** `dev-user-01-mfa`
2. **MFA device type:** Select **Authenticator app**
3. Click **Next**
4. In your phone's authenticator app, scan the QR code shown
5. Enter **MFA code 1** (first 6-digit code from app)
6. Wait 30 seconds for the code to rotate
7. Enter **MFA code 2** (second 6-digit code)
8. Click **Add MFA**

📸 **Screenshot checkpoint:** Security credentials tab showing MFA device assigned with status "Active".

### Decision Point 2: MFA Device Type

| Type | Device | Security Level |
|------|--------|---------------|
| **Authenticator app (TOTP)** ✅ | Phone app (Google Auth, Authy) | High |
| Hardware TOTP token | Physical YubiKey-style device | Very High |
| Security key (FIDO) | USB/NFC key | Very High |
| SMS (not recommended) | Phone text message | Low |

**For learning/personal use:** Virtual MFA (authenticator app) is sufficient.

---

### Troubleshooting — Step 4

**QR code won't scan**
- Click "Show secret key" and manually enter the key into your authenticator app

**"MFA code is incorrect" when assigning**
- The codes must be two consecutive codes. Wait for the code to rotate (30 seconds) and enter the new code as MFA code 1, wait again, enter the next as MFA code 2.

**MFA device already assigned**
- Deactivate the existing device: Security credentials → MFA → select device → Deactivate → then assign a new one

---

## Step 5: Create an IAM Role

Roles are used by AWS services (EC2, Lambda) and for cross-account or temporary access.

### 5.1 — Navigate to Roles

1. Left sidebar → **Roles**
2. Click **Create role**

### 5.2 — Configure Trust Relationship

**Step 1 — Select trusted entity:**

Select **AWS account** (for user-to-role assumption)

Under "An AWS account":
- Select **This account** (same account)

> We'll restrict which user can assume this role via the trust policy (the IAM user we created).

Click **Next**

### 5.3 — Attach Permissions

**Step 2 — Add permissions:**
Search for `AmazonS3ReadOnlyAccess` → check the checkbox

Click **Next**

### 5.4 — Name the Role

**Step 3 — Name, review, and create:**
| Field | Value |
|-------|-------|
| Role name | `s3-read-role` |
| Description | `Read-only S3 access for developers` |

Click **Create role**

### 5.5 — Update Trust Policy (Restrict to Specific User)

After creation:
1. Click on `s3-read-role` to open it
2. Click the **Trust relationships** tab
3. Click **Edit trust policy**
4. Replace the policy with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/dev-user-01"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Replace `YOUR_ACCOUNT_ID` with your 12-digit account ID.

5. Click **Update policy**

📸 **Screenshot checkpoint:** Role `s3-read-role` showing: Trust relationships with `dev-user-01` as principal, and Permissions showing `AmazonS3ReadOnlyAccess`.

---

### Troubleshooting — Step 5

**Can't find `AmazonS3ReadOnlyAccess`**
- Make sure you're searching in the permissions step, not trust policy
- Try filtering by "S3" in the policy search box

**Trust policy won't save**
- Ensure the JSON is valid — no trailing commas, correct quote characters
- Replace `YOUR_ACCOUNT_ID` with the actual 12-digit number (no dashes)

---

## Step 6: Test the Setup

### 6.1 — Test Console Access as dev-user-01

1. Open a **private/incognito browser window**
2. Go to: `https://YOUR_ACCOUNT_ID.signin.aws.amazon.com/console`
3. Sign in with: `dev-user-01` and the temporary password
4. Reset the password when prompted
5. Enter the MFA code from your authenticator app

**Expected:** Console access granted with limited permissions (ReadOnly).

### 6.2 — Test Permissions as dev-user-01

Test that ReadOnly works:
- Navigate to S3 → you should see the list of buckets ✅
- Try to create a bucket → you should get an "Access Denied" error ✅ (proves least privilege)
- Navigate to EC2 → you should see instances ✅
- Try to terminate an instance → "Access Denied" ✅

### 6.3 — Switch to the S3 Role

1. Click your username (top right) → **Switch role**
2. **Account:** your account ID
3. **Role:** `s3-read-role`
4. **Display name:** `S3 Read Role`
5. Click **Switch Role**

**Expected:** You're now operating with temporary credentials of the `s3-read-role`. S3 is accessible; other services show Access Denied.

📸 **Screenshot checkpoint:** Console showing the role switch indicator in the top-right (showing `s3-read-role` in the account switcher badge).

---

## Final Expected Outcome

After completing all 6 steps:

- [ ] Account password policy enforces minimum 12 characters + complexity
- [ ] Group `developers` exists with `ReadOnlyAccess` policy
- [ ] User `dev-user-01` exists, is in `developers` group, and can log in to the console
- [ ] MFA is active for `dev-user-01`
- [ ] Role `s3-read-role` exists with `AmazonS3ReadOnlyAccess` and trust to `dev-user-01`
- [ ] `dev-user-01` can view AWS resources but cannot create, modify, or delete them
- [ ] Role switch to `s3-read-role` works from the console

**Your IAM security posture is now:**
- No shared credentials — each user has their own identity
- Least privilege enforced — no blanket admin access
- MFA required — stolen passwords alone can't compromise the account
- Roles for temporary access — minimal blast radius if credentials leak
