# Project 4.6 — Step Functions Workflow
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create Lambda IAM Role

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global service)

**Step 1.1: Navigate and Verify**
1. Go to [IAM Console](https://console.aws.amazon.com/iam)
2. Click **Roles** in left sidebar → Click **Create role**
3. **Expected View:** Role creation wizard

**Step 1.2: Make Selections**

**Decision Point 1:** Trusted Entity

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | A service assumes this role | ✅ Select this |
| AWS account | Cross-account access | ❌ Not needed |

Select **AWS service** → Choose **Lambda** → Click **Next**

**Step 1.3: Configure Details**

Search and attach:

| Policy | Purpose |
|--------|---------|
| `AWSLambdaBasicExecutionRole` | Lambda can write CloudWatch logs |

Role name: `handson-doc-proc-lambda-role`

Click **Create role**

---

#### Step 2 — Deploy All 6 Lambda Functions

**Prerequisites Check:**
- ✅ Required permissions: `lambda:CreateFunction`
- ✅ IAM role created: `handson-doc-proc-lambda-role`
- ✅ `src/steps.py` available locally

**Why 6 Lambda functions from one file?**

All 6 step handlers live in `src/steps.py`. You deploy 6 separate Lambda functions, each pointing to a different Python function (handler) in the same file. Step Functions calls each function independently.

**Step 2.1: Create All 6 Functions**

Go to [Lambda Console](https://console.aws.amazon.com/lambda) → **Create function** (repeat 6 times)

For ALL 6 functions:
- Creation method: Author from scratch
- Runtime: **Python 3.11**
- Execution role: `handson-doc-proc-lambda-role`
- Paste entire `src/steps.py` as code
- Timeout: 30 seconds
- Click **Deploy**

**Decision Point 1:** Handler naming — CRITICAL

| Function Name | Handler Value | What it does |
|---------------|--------------|-------------|
| `handson-doc-proc-validate` | `steps.validate` | Validates file type (.pdf/.txt/.docx/.csv) and size (max 10MB) — raises `ValueError` on failure |
| `handson-doc-proc-extract_text` | `steps.extract_text` | Simulates text extraction — returns word_count, page_count, text_preview |
| `handson-doc-proc-classify` | `steps.classify` | Classifies document into invoice/contract/report/correspondence |
| `handson-doc-proc-check_compliance` | `steps.check_compliance` | PII detection via regex — checks for email and SSN patterns |
| `handson-doc-proc-store_results` | `steps.store_results` | Stores results, generates record_id |
| `handson-doc-proc-notify` | `steps.notify` | Sends SNS notification (optional — skipped if SNS_TOPIC_ARN not set) |

> **How to change handler in the console:**
> Lambda function → **Code** tab → **Runtime settings** → **Edit** → change **Handler** field

**📸 Screenshot:** Lambda Functions list showing all 6 `handson-doc-proc-*` functions

**Step 2.2: Set Environment Variable for notify Function Only**

Lambda → `handson-doc-proc-notify` → **Configuration** → **Environment variables** → **Edit**

| Key | Value |
|-----|-------|
| `SNS_TOPIC_ARN` | *(leave empty for lab — notify will skip SNS gracefully)* |

---

#### Step 3 — Create Step Functions IAM Role

Step Functions needs its own separate IAM role with permission to **invoke** the 6 Lambda functions. This is different from the Lambda execution role.

**Step 3.1: Navigate**
1. IAM Console → Roles → **Create role**
2. Select **AWS service**

**Decision Point 1:** Service Selection

| Service | Use Case | For This Project |
|---------|----------|-----------------|
| Lambda | Lambda assumes this role | ❌ That's the other role |
| Step Functions | State machine assumes this role | ✅ Search and select "Step Functions" |

Search for **Step Functions** in the use cases → Select it → Click **Next**

**Step 3.2: Skip Policy Attachment**

No managed policy covers this exactly — we'll add an inline policy after creation.

Click **Next** → Role name: `handson-doc-proc-sfn-role` → Click **Create role**

**Step 3.3: Add Inline Policy**

1. Click on the new role `handson-doc-proc-sfn-role`
2. **Add permissions** → **Create inline policy**
3. Switch to **JSON** tab
4. Paste this policy (replace `ACCOUNT_ID` with your actual 12-digit account number):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": [
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-validate",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-extract_text",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-classify",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-check_compliance",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-store_results",
        "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-notify"
      ]
    }
  ]
}
```

Policy name: `invoke-step-lambdas` → Click **Create policy**

**Step 3.4: Validate**

**Expected Outcome:** Role shows 1 inline policy `invoke-step-lambdas` listing all 6 Lambda ARNs

**📸 Screenshot:** Step Functions IAM role showing inline policy with 6 Lambda ARNs

---

#### Step 4 — Create the State Machine

**Prerequisites Check:**
- ✅ Required permissions: `states:CreateStateMachine`
- ✅ All 6 Lambda functions deployed and tested
- ✅ Step Functions IAM role with Lambda invoke policy created

**Step 4.1: Navigate and Verify**
1. Go to [Step Functions Console](https://console.aws.amazon.com/states)
2. **Expected View:** State machines list with "Create state machine" button
3. Click **Create state machine**

**Step 4.2: Make Selections**

**Decision Point 1:** Authoring Method

| Option | How it works | For This Project |
|--------|-------------|-----------------|
| Workflow Studio (visual drag-and-drop) | Add states visually, code generated | ✅ Good for learning |
| Write your definition in code | Paste ASL JSON directly | ✅ More control, matches our file |

Select **Write your definition in code** → Click **Next**

**Decision Point 2:** Workflow Type — IMPORTANT

| Type | Max Duration | Execution History | Price | For This Project |
|------|-------------|------------------|-------|-----------------|
| Standard | Up to 1 year | 90-day audit trail in console | $0.025/1K transitions | ✅ Use this |
| Express | Up to 5 minutes | CloudWatch Logs only | $1/million executions | ❌ No history in console |

Select **Standard**

**Step 4.3: Paste State Machine Definition**

In the code editor, paste the following. Replace ALL 6 instances of `ACCOUNT_ID` with your actual AWS account number:

```json
{
  "Comment": "Document processing workflow",
  "StartAt": "Validate",
  "States": {
    "Validate": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-validate",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["ValueError"],
          "Next": "ValidationFailed",
          "ResultPath": "$.error"
        },
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "ProcessingFailed",
          "ResultPath": "$.error"
        }
      ],
      "Next": "ExtractText"
    },
    "ExtractText": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-extract_text",
      "Retry": [
        {
          "ErrorEquals": ["States.ALL"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 1.5
        }
      ],
      "Next": "ParallelAnalysis"
    },
    "ParallelAnalysis": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "Classify",
          "States": {
            "Classify": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-classify",
              "End": true
            }
          }
        },
        {
          "StartAt": "CheckCompliance",
          "States": {
            "CheckCompliance": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-check_compliance",
              "End": true
            }
          }
        }
      ],
      "ResultSelector": {
        "classification.$": "$[0].classification",
        "compliance.$": "$[1].compliance"
      },
      "ResultPath": "$.analysis",
      "Next": "StoreResults"
    },
    "StoreResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-store_results",
      "Next": "Notify"
    },
    "Notify": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:handson-doc-proc-notify",
      "Next": "Success"
    },
    "Success": {
      "Type": "Succeed"
    },
    "ValidationFailed": {
      "Type": "Fail",
      "Error": "ValidationError",
      "Cause": "Document failed validation checks"
    },
    "ProcessingFailed": {
      "Type": "Fail",
      "Error": "ProcessingError",
      "Cause": "An unexpected error occurred during processing"
    }
  }
}
```

**Step 4.4: Validate the Definition**

Click **Next** — Step Functions will validate the JSON and show a visual preview of the state machine graph.

**Expected View:** Visual diagram showing:
```
Validate → ExtractText → ParallelAnalysis (Classify + CheckCompliance) → StoreResults → Notify → Success
                  ↓ ValueError
            ValidationFailed
```

**📸 Screenshot:** State machine definition visual preview showing all states and connections

**Step 4.5: Configure State Machine Settings**

| Field | Value | Explanation |
|-------|-------|-------------|
| State machine name | `handson-doc-proc-state-machine` | Matches terraform naming convention |
| IAM role | **Choose an existing role** → `handson-doc-proc-sfn-role` | The role created in Step 3 |
| Logging | **OFF** | Simplify for lab (enable in production) |
| Tracing | **OFF** | X-Ray tracing — not needed for lab |

Click **Create state machine**

**Step 4.6: Validate Result**

**Expected Outcome:** State machine status = **Active**. The visual workflow diagram shows all states.

**📸 Screenshot:** State machine detail page showing Status = Active and the visual workflow graph

**Troubleshooting:**
- `AccessDeniedException` when starting execution: The Step Functions role doesn't have `lambda:InvokeFunction` — check inline policy ARNs match exactly
- State machine shows `FAILED` immediately: Check if Lambda function ARNs in the definition are correct (right account ID and region)

---

#### Step 5 — Start a Successful Execution

**Step 5.1: Navigate**
1. Click on your state machine `handson-doc-proc-state-machine`
2. Click **Start execution** (orange button)

**Step 5.2: Enter Input**

In the input box, paste:

```json
{
  "file_key": "documents/invoice-2024.pdf",
  "file_size": 524288,
  "uploaded_by": "alice@example.com"
}
```

Click **Start execution**

**Step 5.3: Watch Real-Time Execution**

**Expected View:** The execution detail page shows the visual workflow with states highlighted:

| State colour | Meaning |
|-------------|---------|
| 🔵 Blue border | Currently executing |
| ✅ Green | Completed successfully |
| ❌ Red | Failed |

Watch all states turn green one by one:
1. **Validate** → green (file type and size pass)
2. **ExtractText** → green (text extraction simulated)
3. **ParallelAnalysis** → **Classify** and **CheckCompliance** turn green simultaneously
4. **StoreResults** → green
5. **Notify** → green
6. **Success** → green — execution complete

**Expected Total Duration:** ~2–5 seconds (all simulated, no real I/O)

**📸 Screenshot:** Visual execution graph with ALL states showing green checkmarks

**Step 5.4: Explore Execution Details**

Click on any state (e.g. **Validate**) in the visual graph to see:
- **Input:** The JSON the state received
- **Output:** The JSON the state returned

**Decision Point 1:** What to look for in state I/O

| State | Input contains | Output adds |
|-------|--------------|-------------|
| Validate | `file_key`, `file_size`, `uploaded_by` | `"validation": {"status": "passed", "file_type": "pdf"}` |
| ExtractText | Everything above | `"extraction": {"word_count": 1250, "page_count": 3, ...}` |
| ParallelAnalysis | Everything above | `"analysis": {"classification": {...}, "compliance": {...}}` |
| StoreResults | Everything above | `"storage": {"status": "saved", "record_id": "doc-..."}` |
| Notify | Everything above | `"notification": {"status": "sent"}` |

**📸 Screenshot:** State input/output panel showing data accumulating through the workflow

**Step 5.5: View Execution History Tab**

Click **Events** tab on the execution page.

**Expected Outcome:** Ordered list of all state transitions with timestamps:

```
ExecutionStarted        12:00:00.000Z
TaskStateEntered        Validate       12:00:00.100Z
TaskSucceeded           Validate       12:00:00.800Z
TaskStateEntered        ExtractText    12:00:00.800Z
TaskSucceeded           ExtractText    12:00:01.100Z
TaskStateEntered        Classify       12:00:01.100Z  ← same time!
TaskStateEntered        CheckCompliance 12:00:01.100Z ← parallel!
TaskSucceeded           Classify       12:00:01.500Z
TaskSucceeded           CheckCompliance 12:00:01.500Z
TaskStateEntered        StoreResults   12:00:01.500Z
TaskSucceeded           StoreResults   12:00:02.000Z
TaskStateEntered        Notify         12:00:02.000Z
TaskSucceeded           Notify         12:00:02.500Z
ExecutionSucceeded      12:00:02.500Z
```

**Key observation:** `Classify` and `CheckCompliance` have **identical** start timestamps — this confirms true parallel execution.

**📸 Screenshot:** Execution Events tab showing Classify and CheckCompliance with matching timestamps

---

#### Step 6 — Test the Failure Path

**Step 6.1: Start a Failing Execution**

1. Click **Start execution** again
2. Enter this input (unsupported `.exe` file type):

```json
{
  "file_key": "documents/malware.exe",
  "file_size": 1024
}
```

Click **Start execution**

**Step 6.2: Observe the Failure**

**Expected View:**
- **Validate** state turns ❌ red
- Arrow from Validate → **ValidationFailed** highlights
- **ValidationFailed** state turns red (Fail state)
- Execution status = **FAILED**

**Decision Point 1:** Understanding the error routing

| What happened in Lambda | How Step Functions handled it |
|------------------------|------------------------------|
| `validate()` raised `ValueError("Unsupported file type: .exe")` | Catch block matched `"ErrorEquals": ["ValueError"]` |
| | Routed to `ValidationFailed` state |
| | Stored error detail at `$.error` |
| | Execution terminated as FAILED |

**📸 Screenshot:** Visual execution graph showing Validate red and ValidationFailed path highlighted

**Step 6.3: View Error Details**

Click on the **Validate** state in the failed execution:
- **Exception** tab → Shows: `ValueError: Unsupported file type: .exe`

**📸 Screenshot:** Validate state Exception tab showing the ValueError message

---

#### Step 7 — Explore the Retry Behavior

**Step 7.1: Understand What Retry Does**

The Validate state definition includes:
```json
"Retry": [{
  "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
  "IntervalSeconds": 2,
  "MaxAttempts": 3,
  "BackoffRate": 2
}]
```

This means: if Lambda itself has a transient error (throttled, service error), Step Functions automatically retries up to 3 times with exponential backoff (2s, 4s, 8s). The business logic `ValueError` is NOT retried — it goes directly to Catch.

**Step 7.2: View Retry Attempts in Execution History**

In a successful execution, check Events tab:

**Decision Point 1:** Retry vs Catch

| Error Type | Handled by | Behaviour |
|------------|-----------|-----------|
| `Lambda.ServiceException` | Retry | Wait and try again (up to 3 times) |
| `Lambda.TooManyRequestsException` | Retry | Wait and try again (throttling) |
| `ValueError` (business logic) | Catch | Route to ValidationFailed state immediately |
| `States.ALL` (anything else) | Catch (fallback) | Route to ProcessingFailed state |

---

#### Step 8 — View the Complete Final Output

**Step 8.1: From the Executions Tab**

1. State machine → **Executions** tab
2. Click on your successful execution
3. Scroll to **Execution output** section

**Expected Final Output:**
```json
{
  "file_key": "documents/invoice-2024.pdf",
  "file_size": 524288,
  "uploaded_by": "alice@example.com",
  "validation": {
    "status": "passed",
    "file_type": "pdf"
  },
  "extraction": {
    "status": "completed",
    "word_count": 1250,
    "page_count": 3,
    "text_preview": "This document contains important information about..."
  },
  "analysis": {
    "classification": {
      "category": "invoice",
      "confidence": 0.92
    },
    "compliance": {
      "status": "clean",
      "has_pii": false,
      "has_email": false,
      "has_ssn": false
    }
  },
  "storage": {
    "status": "saved",
    "record_id": "doc-1705312801"
  },
  "notification": {
    "status": "sent"
  }
}
```

**📸 Screenshot:** Execution output showing the complete merged JSON with all step results

---

#### Step 9 — Check Lambda Logs for Each Step

Each Lambda function writes its own CloudWatch log group.

1. CloudWatch → Log groups → filter by `handson-doc-proc-`
2. You should see 6 log groups:
   - `/aws/lambda/handson-doc-proc-validate`
   - `/aws/lambda/handson-doc-proc-extract_text`
   - `/aws/lambda/handson-doc-proc-classify`
   - `/aws/lambda/handson-doc-proc-check_compliance`
   - `/aws/lambda/handson-doc-proc-store_results`
   - `/aws/lambda/handson-doc-proc-notify`

**Expected log entries in validate log group:**
```
Validating: {"file_key": "documents/invoice-2024.pdf", "file_size": 524288, ...}
```

**Expected log entries in classify log group:**
```
Classifying document: documents/invoice-2024.pdf
```

**📸 Screenshot:** CloudWatch log groups showing all 6 `handson-doc-proc-*` groups

---

#### Step 10 — Run Multiple Executions and View History

Start 3 more executions with different inputs:

**Execution 1 — PDF (should succeed):**
```json
{"file_key": "documents/contract-2024.pdf", "file_size": 102400}
```

**Execution 2 — CSV (should succeed):**
```json
{"file_key": "reports/monthly-sales.csv", "file_size": 20480}
```

**Execution 3 — EXE (should fail at Validate):**
```json
{"file_key": "tools/setup.exe", "file_size": 2048576}
```

**Expected Executions List:**

| Name | Status | Duration |
|------|--------|---------|
| execution-uuid-1 | ✅ SUCCEEDED | ~2s |
| execution-uuid-2 | ✅ SUCCEEDED | ~2s |
| execution-uuid-3 | ❌ FAILED | ~1s |

**📸 Screenshot:** Executions tab showing mix of SUCCEEDED and FAILED executions

**📸 Screenshot:** Final architecture overview — state machine page showing the visual diagram and execution count
