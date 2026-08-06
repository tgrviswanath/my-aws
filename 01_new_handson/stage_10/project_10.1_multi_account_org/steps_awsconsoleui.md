# Project 10.1 — AWS Organizations: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] Logged in as **management account** (root of organization)
- [ ] IAM permissions: `organizations:*`
- [ ] Unique email addresses ready for new member accounts
- [ ] Region: Organizations is global — region selector doesn't affect it

---

## Step 1 — Navigate to AWS Organizations

1. Sign in to the **AWS Management Console** (management account)
2. Search for **Organizations** in the search bar
3. Click **AWS Organizations**
4. If no organization exists: click **Create an organization**
5. Choose **Enable all features** (recommended over billing-only)
6. Click **Create organization**

📸 Screenshot: Organizations welcome page with "Create an organization" button

**Decision Point: All features vs Consolidated Billing only?**
- **All features** ✅ — Enables SCPs, tag policies, backup policies, AI services opt-out
- **Billing only** — Just consolidated billing, no SCPs (hard to upgrade later)

---

## Step 2 — View the Organization Structure

1. You see the account tree:
   - **Root** at the top
   - **Management account** directly under Root
2. Left nav shows:
   - **AWS accounts** — account tree
   - **Policies** — SCPs, tag policies
   - **Services** — AWS service integrations
   - **Settings** — Organization management
3. Explore the **AWS accounts** tree view

📸 Screenshot: Organizations account tree showing Root and management account

---

## Step 3 — Create Organizational Units

1. Click on **Root** in the account tree
2. Click **Actions** → **Create new organizational unit**
3. **OU name**: `Security` → Click **Create organizational unit**
4. Repeat to create: `Infrastructure`, `Workloads`, `Sandbox`
5. Click on the `Workloads` OU
6. Click **Actions** → **Create new organizational unit**
7. Create: `Dev`, `Staging`, `Prod` as children of Workloads

📸 Screenshot: OU creation dialog with name field

---

## Step 4 — Add Member Accounts

**Option A — Invite existing account:**
1. Click on the destination OU (e.g., `Workloads/Dev`)
2. Click **Actions** → **Invite AWS account**
3. Enter the account's email address or account ID
4. Add a notes message
5. Click **Send invitation**
6. The invited account must accept in the Organizations console

**Option B — Create new account:**
1. Click on the destination OU
2. Click **Actions** → **Create an AWS account**
3. Fill in:
   - **AWS account name**: `myapp-dev`
   - **Email address**: `aws-dev@yourcompany.com` (unique, unused email)
   - **IAM role name**: `OrganizationAccountAccessRole` (default)
4. Click **Create AWS account**
5. Wait 5-15 minutes — account auto-appears in the OU

📸 Screenshot: Create new account form with email and account name fields

---

## Step 5 — Move Account to Correct OU

1. In the account tree, locate the newly created/joined account
2. Right-click or click **Actions** → **Move**
3. Select the target OU from the tree (e.g., `Workloads/Dev`)
4. Click **Move AWS account**

📸 Screenshot: Move account dialog with OU tree selection

---

## Step 6 — Create Service Control Policies (SCPs)

1. In left nav: click **Policies**
2. Click **Service control policies**
3. If SCPs not enabled: click **Enable service control policies**
4. Click **Create policy**
5. **Policy name**: `ProductionGuardrails`
6. In the **JSON editor**: paste the production SCP from GUIDE.md
7. Click **Create policy**
8. Repeat for `SandboxRestrictions`

📸 Screenshot: SCP JSON editor with policy content and syntax highlighting

---

## Step 7 — Attach SCPs to OUs

1. Click on the `Prod` OU in the account tree
2. Click **Policies** tab (right side panel)
3. Click **Attach** under Service control policies
4. Select `ProductionGuardrails` from the list
5. Click **Attach policy**
6. Repeat: attach `SandboxRestrictions` to `Sandbox` OU

📸 Screenshot: OU detail page showing attached policies tab

**Decision Point: Attach SCP to OU vs account?**
- **OU level**: Affects all current and future accounts in OU ✅ (recommended)
- **Account level**: Granular control, harder to maintain at scale

**Troubleshooting — SCP inheritance:**
- SCPs are cumulative — account gets all SCPs from Root → OU chain
- Use `effective_policy` to see combined SCP for any account
- An explicit DENY anywhere in the chain overrides any ALLOW

---

## Step 8 — Enable AWS Service Integrations

1. In left nav: click **Services**
2. Enable integrations for:
   - ✅ **AWS CloudTrail** — organization trail (logs all accounts)
   - ✅ **AWS Config** — organization conformance packs
   - ✅ **AWS Security Hub** — aggregate findings across accounts
   - ✅ **AWS GuardDuty** — organization-level threat detection
3. Each integration adds delegated administrator capabilities

📸 Screenshot: Services page with enabled integrations listed

---

## Step 9 — View Consolidated Billing

1. Navigate to **AWS Billing** → **Bills**
2. Under **Service charges**, you see charges from all member accounts
3. Navigate to **Cost allocation tags**: enable tags for cost reporting
4. Navigate to **Cost Explorer**: see per-account breakdown
5. Create **Budgets** for individual accounts or the organization

📸 Screenshot: Billing dashboard showing per-account cost breakdown

---

## Step 10 — Verify Organization Structure

1. In **AWS Organizations** → **AWS accounts** tree
2. Verify structure:
   ```
   Root
   ├── [Management Account]
   ├── OU: Security
   ├── OU: Infrastructure
   ├── OU: Workloads
   │   ├── OU: Dev → [dev account]
   │   ├── OU: Staging → [staging account]
   │   └── OU: Prod → [prod account] + ProductionGuardrails SCP
   └── OU: Sandbox → [sandbox account] + SandboxRestrictions SCP
   ```
3. Click on each OU to verify accounts and SCPs are correct

📸 Screenshot: Complete organization tree with all OUs and accounts visible

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Can't create organization | Account already in one | Check Organizations console — already enrolled |
| Account invite not received | Email spam filter | Check spam, or use account ID instead of email |
| SCP not taking effect | Policy not attached | Check OU → Policies tab |
| SCP blocking management account | By design | SCPs don't apply to management account |
| Can't delete OU | Has accounts in it | Move all accounts out first |

---

## Console Navigation Quick Reference

```
AWS Organizations
├── AWS accounts          → Account tree + OU structure
│   ├── Root
│   ├── [OU Name]         → Create child OUs, move accounts
│   └── [Account Name]    → View details, move, close
├── Policies
│   ├── Service control policies → SCPs
│   ├── Tag policies             → Enforce tagging
│   └── Backup policies          → Enforce backup
├── Services              → Enable AWS service integrations
└── Settings
    ├── Delegation        → Delegate admin to member accounts
    └── Enable features   → All features vs billing only
```
