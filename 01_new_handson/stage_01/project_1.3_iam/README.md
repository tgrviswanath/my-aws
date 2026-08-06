# Project 1.3 — IAM Users, Groups, Roles & Policies

**Stage:** 01 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** $0

Build a least-privilege IAM structure from scratch: create `developers` and `readonly` groups, attach AWS managed policies, write a custom JSON policy scoped to a single S3 bucket, enable MFA on an IAM user, and test `sts:AssumeRole` to confirm temporary credential issuance. Everything runs in the console and CLI — no code deployed.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| IAM | Users, groups, roles, policies, MFA | Free |
| STS | `AssumeRole` to issue temporary credentials | Free |
| S3 (test target) | Resource referenced in custom least-privilege policy | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| AWS root account | Required to create initial IAM users and groups |
| Policy JSON file | Custom policy allowing `s3:GetObject` on one bucket only |
| MFA device | Virtual MFA app (Google Authenticator or Authy) for TOTP codes |
| Trust policy JSON | Allows `sts:AssumeRole` from the developer IAM user |

### Output
| Type | Description |
|------|-------------|
| IAM group: `developers` | `PowerUserAccess` managed policy attached |
| IAM group: `readonly` | `ReadOnlyAccess` managed policy attached |
| IAM user: `dev-alice` | Member of `developers`, MFA enabled, console access |
| IAM user: `readonly-bob` | Member of `readonly`, programmatic access only |
| Custom policy | `s3-readonly-mybucket` — allows `s3:GetObject` on `arn:aws:s3:::mybucket/*` only |
| IAM role: `developer-role` | Trust policy: `dev-alice` can assume; permissions: `PowerUserAccess` |
| STS output | `AssumeRole` returns `AccessKeyId`, `SecretAccessKey`, `SessionToken` |

---

## Architecture

```
Root account (setup only — not used day-to-day)
  │
  ├── IAM Group: developers
  │     ├── Policy: PowerUserAccess (AWS managed)
  │     └── User: dev-alice  ← MFA enabled
  │
  ├── IAM Group: readonly
  │     ├── Policy: ReadOnlyAccess (AWS managed)
  │     └── User: readonly-bob
  │
  ├── Custom Policy: s3-readonly-mybucket
  │     └── Allow s3:GetObject on arn:aws:s3:::mybucket/*
  │           └── Attached to readonly-bob directly
  │
  └── IAM Role: developer-role
        ├── Trust policy: Principal = dev-alice (sts:AssumeRole)
        └── Permissions: PowerUserAccess
              │
              └── dev-alice → aws sts assume-role → temporary creds (TTL ≤ 12h)
```

---

## Quick Start

```cmd
REM 1. Create groups
aws iam create-group --group-name developers
aws iam create-group --group-name readonly

REM 2. Attach AWS managed policies to groups
aws iam attach-group-policy --group-name developers ^
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
aws iam attach-group-policy --group-name readonly ^
    --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

REM 3. Create users and add to groups
aws iam create-user --user-name dev-alice
aws iam add-user-to-group --user-name dev-alice --group-name developers
aws iam create-user --user-name readonly-bob
aws iam add-user-to-group --user-name readonly-bob --group-name readonly

REM 4. Create custom least-privilege policy (see code/s3_readonly_policy.json)
aws iam create-policy --policy-name s3-readonly-mybucket ^
    --policy-document file://code/s3_readonly_policy.json

REM 5. Create IAM role for assumption (trust policy in code/trust_policy.json)
aws iam create-role --role-name developer-role ^
    --assume-role-policy-document file://code/trust_policy.json
aws iam attach-role-policy --role-name developer-role ^
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

REM 6. Test AssumeRole as dev-alice (configure dev-alice profile first)
aws sts assume-role ^
    --role-arn arn:aws:iam::ACCOUNT_ID:role/developer-role ^
    --role-session-name test-session ^
    --profile dev-alice

REM 7. Enable MFA via console: IAM → Users → dev-alice → Security credentials → Assign MFA device
```

---

## Data Flow

```
1. Root creates groups and attaches managed policies — policies define what group members can do
2. Users are added to groups — permissions are inherited, not set per-user (cleaner, scalable)
3. Custom policy JSON is uploaded: Effect=Allow, Action=[s3:GetObject], Resource=[arn:...mybucket/*]
4. Policy evaluation at API call time: IAM collects all applicable policies, checks for explicit Deny first, then Allow
5. dev-alice calls sts:AssumeRole with the developer-role ARN
6. STS checks the role's trust policy — confirms dev-alice is a trusted principal
7. STS issues temporary credentials: AccessKeyId (ASIA...), SecretAccessKey, SessionToken (expiry ≤ 12h)
8. Caller sets AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN env vars (or uses a named profile)
9. All API calls made with these creds carry the role's permissions until expiry
10. MFA adds a second factor to console login and can be required in the trust policy via Condition: aws:MultiFactorAuthPresent
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — IAM structure overview |
| `GUIDE.md` | Full walkthrough: groups, users, custom policy, role assumption |
| `steps.md` | Windows CMD quick-reference for IAM and STS commands |
| `steps_awsconsoleui.md` | Console walkthrough: MFA setup, policy editor, role creation |
| `verify.md` | Checklist: users exist, policies attached, role assumed, MFA working |
| `cost_estimate.md` | Cost breakdown ($0) |
| `code/s3_readonly_policy.json` | Custom least-privilege policy for S3 bucket access |
| `code/trust_policy.json` | Trust policy allowing dev-alice to assume developer-role |
| `docs/` | IAM policy evaluation logic diagram, policy types reference |

---

## Lessons Learned

- Never use the root account for daily work — root has unrestricted access with no way to apply a Deny policy; create an IAM admin user immediately after account creation
- IAM policies are JSON documents with `Effect`, `Action`, and `Resource` — the simplest least-privilege policy is one `Allow` statement with the exact action and a specific ARN, not `*`
- Policy evaluation order: **explicit Deny always wins** over any Allow, regardless of which policy contains the Deny — this is why SCPs (Service Control Policies) can block even admin users
- A role has two distinct policies: the **trust policy** (who can assume it, `sts:AssumeRole`) and the **permissions policy** (what the assumed role can do) — beginners often confuse which one to edit
- `sts:AssumeRole` returns three values — `AccessKeyId` (starts with `ASIA`), `SecretAccessKey`, and `SessionToken` — all three must be provided when using temporary credentials; missing the session token gives an `InvalidClientTokenId` error
- MFA enforcement on `AssumeRole` requires a `Condition` block in the trust policy: `"aws:MultiFactorAuthPresent": "true"` — without it, MFA on the user account does not carry over to role sessions
- `AmazonS3ReadOnlyAccess` (managed policy) grants `s3:GetObject` on `*` (all buckets) — a custom policy scoped to one bucket ARN is always preferable when only one bucket is needed
