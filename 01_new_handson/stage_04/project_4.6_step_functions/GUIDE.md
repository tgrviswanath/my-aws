# Project 4.6 — Step Functions Workflow
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** Multi-Step Document Processing Workflow with AWS Step Functions

**Business / Problem Statement:**
Complex business processes like document processing, order fulfillment, or video transcoding involve many sequential and parallel steps with error handling, retries, and branching logic. If you chain Lambda functions manually, error handling becomes spaghetti code. AWS Step Functions solves this: you define the workflow as a JSON state machine, and Step Functions orchestrates execution, manages state, handles retries, runs parallel branches, and gives you a visual execution graph. This project processes uploaded documents through 5 coordinated steps with parallel analysis branches and automatic error handling.

**Learning Objectives:**
- Understand Step Functions state machine concepts (Task, Parallel, Choice, Wait, Succeed, Fail)
- Define a state machine in Amazon States Language (ASL) JSON
- Implement retry logic with exponential backoff per state
- Use Catch blocks to route failures to specific error states
- Run parallel branches (Classify + CheckCompliance simultaneously) and merge results
- Use `ResultPath` and `ResultSelector` to manage state data between steps
- Read the visual execution graph in the AWS Console
- Understand Standard vs Express Workflow tradeoffs

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| Step Functions (Standard) | Orchestrates the workflow — manages state, retries, routing |
| Lambda (×6 functions) | Business logic for each step (validate, extract, classify, etc.) |
| SNS | Sends completion notification from the `notify` step |
| IAM (2 roles) | One for Lambda, one for Step Functions to invoke Lambda |

**Workflow Steps:**
```
[INPUT] file_key, file_size, uploaded_by
         │
         ▼
  ┌─────────────┐  ValueError  ┌──────────────────┐
  │  Validate   │ ───────────► │ ValidationFailed  │ → [FAIL]
  └──────┬──────┘              └──────────────────┘
         │ success
         ▼
  ┌─────────────┐
  │ ExtractText │
  └──────┬──────┘
         │
         ▼
  ┌─────────────────────────────────────────────┐
  │           ParallelAnalysis                   │
  │  ┌──────────────┐   ┌────────────────────┐  │
  │  │   Classify   │   │  CheckCompliance   │  │
  │  │ (concurrent) │   │   (concurrent)     │  │
  │  └──────────────┘   └────────────────────┘  │
  └──────────────────────────┬──────────────────┘
                             │ both complete
                             ▼
                    ┌──────────────┐
                    │ StoreResults │
                    └──────┬───────┘
                           │
                           ▼
                      ┌────────┐
                      │ Notify │
                      └───┬────┘
                          │
                          ▼
                      [SUCCESS]
```

**State Types Used:**

| State | Type | Description |
|-------|------|-------------|
| Validate | Task | Invokes Lambda; raises ValueError on invalid input |
| ExtractText | Task | Invokes Lambda; simulates text extraction |
| ParallelAnalysis | Parallel | Runs Classify and CheckCompliance concurrently |
| StoreResults | Task | Merges parallel results, writes to storage |
| Notify | Task | Publishes SNS completion notification |
| Success | Succeed | Terminal success state |
| ValidationFailed | Fail | Terminal failure state — triggered by ValueError |

> **Note on `ProcessingFailed` state:** The `state_machine/definition.json` reference file and the Console UI guide (steps_awsconsoleui.md) include a `ProcessingFailed` catch-all Fail state for `States.ALL` errors — this is the recommended production pattern. However, the Terraform deployment in `terraform/main.tf` omits this state for brevity. If deploying via Terraform, unexpected Lambda errors surface as execution failures without routing to a named Fail state. To add it, include a second Catch entry: `{"ErrorEquals": ["States.ALL"], "Next": "ProcessingFailed", "ResultPath": "$.error"}`.

**Best Practices Followed:**
- `ResultPath: "$.error"` on Catch blocks (preserves original input alongside error detail)
- `ResultSelector` on Parallel state to reshape output before merging
- Retry with exponential backoff for transient Lambda errors (ServiceException)
- Catch-all (`States.ALL`) as fallback error handler
- Standard Workflow used (not Express) — full execution history, 90-day audit trail
- Step Functions IAM role uses least-privilege: only `lambda:InvokeFunction` on specific ARNs

---

## 3. Prerequisites

**Same as Project 4.1, plus:**

| Extra Requirement | Why |
|------------------|-----|
| Understanding of JSON | State machine is defined in JSON (ASL format) |
| Python 3.11 + boto3 | Lambda functions use Python |

**IAM Permissions Required (additional):**
```
states:CreateStateMachine, states:StartExecution
states:DescribeExecution, states:GetExecutionHistory
iam:CreateRole, iam:AttachRolePolicy (for Step Functions role)
```

**Environment Variable Setup:**
```bash
export AWS_DEFAULT_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
# After deployment:
# export STATE_MACHINE_ARN=$(terraform output -raw state_machine_arn)
```

---

## 4. Project Folder Structure

```
project_4.6_step_functions/
│
├── README.md                    ← Workflow overview, state types, lessons learned
├── GUIDE.md                     ← This file — complete implementation guide
├── steps.md                     ← Deploy, start execution, monitor, failure tests
├── verify.md                    ← Console graph, parallel timing check, failure path test
├── cost_estimate.md             ← Step Functions transition costs
│
├── src/
│   └── steps.py                 ← ALL 6 Lambda handlers in one file (validate,
│                                    extract_text, classify, check_compliance,
│                                    store_results, notify)
│
├── state_machine/
│   └── definition.json          ← ASL state machine definition (ARN placeholders)
│
├── docs/
│   └── architecture.md          ← State diagram, error handling pattern, Standard vs Express
│
└── terraform/
    └── main.tf                  ← Step Functions state machine, 6 Lambda functions,
                                    2 IAM roles (Lambda + Step Functions)
```

**File-by-File Explanation:**

| File | Purpose | Key Detail |
|------|---------|-----------|
| `src/steps.py` | All 6 Lambda handlers | Each function = one state in the workflow |
| `state_machine/definition.json` | ASL definition with `${...Arn}` placeholders | Used as reference — Terraform generates the real one with actual ARNs |
| `terraform/main.tf` | Creates 6 Lambdas + state machine with wired ARNs | Uses `for_each` over `handler_map` to create all 6 Lambda functions |
| `docs/architecture.md` | Visual state diagram + error pattern | Standard vs Express comparison table |

---

## 5. Project Input & Output

**INPUT — Start execution with this JSON:**
```json
{
  "file_key": "documents/invoice-2024.pdf",
  "file_size": 524288,
  "uploaded_by": "alice@example.com"
}
```

**OUTPUT — Successful execution final state:**
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

**OUTPUT — Failed execution (unsupported file type):**
```json
Input:  {"file_key": "documents/malware.exe", "file_size": 1024}
Result: Execution FAILED at Validate state
        Error: ValidationError
        Cause: "Document failed validation checks"
```

**OUTPUT — Step Functions Console Execution History:**
```
Timestamp              Type                  State
2024-01-15T12:00:00Z   TaskStateEntered      Validate
2024-01-15T12:00:01Z   TaskSucceeded         Validate
2024-01-15T12:00:01Z   TaskStateEntered      ExtractText
2024-01-15T12:00:02Z   TaskSucceeded         ExtractText
2024-01-15T12:00:02Z   TaskStateEntered      Classify        ← parallel start
2024-01-15T12:00:02Z   TaskStateEntered      CheckCompliance ← same timestamp!
2024-01-15T12:00:03Z   TaskSucceeded         Classify
2024-01-15T12:00:03Z   TaskSucceeded         CheckCompliance
2024-01-15T12:00:03Z   TaskStateEntered      StoreResults
2024-01-15T12:00:04Z   TaskSucceeded         StoreResults
2024-01-15T12:00:04Z   TaskStateEntered      Notify
2024-01-15T12:00:05Z   TaskSucceeded         Notify
2024-01-15T12:00:05Z   ExecutionSucceeded
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create Lambda IAM Role

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Services enabled: IAM (global)

**Step 1.1: Navigate**
1. Go to [IAM Console](https://console.aws.amazon.com/iam) → **Roles** → **Create role**

**Step 1.2: Configure Lambda Role**

| Field | Value |
|-------|-------|
| Trusted entity | AWS service → **Lambda** |
| Policies | `AWSLambdaBasicExecutionRole` |
| Role name | `handson-doc-proc-lambda-role` |

Click **Create role**

---

#### Step 2 — Deploy All 6 Lambda Functions

All 6 handlers live in **one file**: `src/steps.py`. You create 6 Lambda functions pointing to different handlers in the same file.

**Step 2.1: Navigate**
1. Lambda Console → **Create function** (repeat 6 times)

| Function Name | Handler | Description |
|---------------|---------|-------------|
| `handson-doc-proc-validate` | `steps.validate` | Validates file type and size |
| `handson-doc-proc-extract_text` | `steps.extract_text` | Extracts text content |
| `handson-doc-proc-classify` | `steps.classify` | Classifies document category |
| `handson-doc-proc-check_compliance` | `steps.check_compliance` | Scans for PII |
| `handson-doc-proc-store_results` | `steps.store_results` | Saves results |
| `handson-doc-proc-notify` | `steps.notify` | Sends SNS notification |

For EACH function:
1. Author from scratch
2. Runtime: Python 3.11
3. Execution role: `handson-doc-proc-lambda-role`
4. Paste entire `src/steps.py` as code
5. Set handler to the specific handler listed above
6. Click **Deploy**

**Step 2.2: Set `notify` Function Environment Variable**

The `notify` function optionally sends SNS. For now leave `SNS_TOPIC_ARN` empty (notification will be skipped gracefully).

| Function | Key | Value |
|----------|-----|-------|
| `handson-doc-proc-notify` | `SNS_TOPIC_ARN` | *(leave empty for lab)* |

**📸 Screenshot:** Lambda Functions list showing all 6 `handson-doc-proc-*` functions

---

#### Step 3 — Create Step Functions IAM Role

Step Functions needs permission to **invoke Lambda functions**. This is a separate role.

**Step 3.1: Navigate**
1. IAM → Roles → **Create role**

**Step 3.2: Make Selections**

**Decision Point 1:** Trusted Entity

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS service | Service assumes the role | ✅ Select this |
| Custom trust policy | Advanced control | ❌ Not needed |

Select **AWS service** → In the "Use case" dropdown, search for **Step Functions** → Select it

**Step 3.3: Configure**

| Field | Value | Explanation |
|-------|-------|-------------|
| Permissions | (skip — add manually below) | No matching managed policy |
| Role name | `handson-doc-proc-sfn-role` | Descriptive |

Click **Create role**

**Step 3.4: Add Inline Policy**

1. Click the new role → **Add permissions** → **Create inline policy**
2. Switch to **JSON** tab
3. Enter:

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

Replace `ACCOUNT_ID` with your actual AWS account ID.

Policy name: `invoke-step-lambdas` → Click **Create policy**

**📸 Screenshot:** Step Functions IAM role showing inline policy with 6 Lambda ARNs

---

#### Step 4 — Create the Step Functions State Machine

**Prerequisites Check:**
- ✅ Required permissions: `states:CreateStateMachine`
- ✅ All 6 Lambda functions deployed
- ✅ Step Functions IAM role created

**Step 4.1: Navigate**
1. Go to [Step Functions Console](https://console.aws.amazon.com/states)
2. Click **Create state machine**

**Step 4.2: Make Selections**

**Decision Point 1:** Authoring Method

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Workflow Studio (visual) | Drag and drop — easy to start | ✅ Good for learning |
| Write your definition (JSON) | Direct ASL control | ✅ Use for production |

Select **Write your definition** (gives you full control)

**Decision Point 2:** Workflow Type

| Type | Max Duration | Pricing | Audit | For This Project |
|------|-------------|---------|-------|-----------------|
| Standard | 1 year | $0.025/1K transitions | 90-day history | ✅ Use this |
| Express | 5 minutes | $1/million executions | CloudWatch only | ❌ For high-volume short flows |

Select **Standard**

**Step 4.3: Paste the State Machine Definition**

In the code editor, paste the following definition. Replace all `ACCOUNT_ID` with your account ID:

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

**Step 4.4: Configure State Machine Details**

| Field | Value |
|-------|-------|
| State machine name | `handson-doc-proc-state-machine` |
| IAM role | **Choose an existing role** → `handson-doc-proc-sfn-role` |
| Logging | **OFF** (simplify for lab) |
| Tracing | **OFF** |

Click **Create state machine**

**Step 4.5: Validate Result**

**Expected Outcome:** State machine created, status = **Active**. You should see the visual workflow diagram automatically rendered from your JSON.

**📸 Screenshot:** Step Functions visual workflow showing all states with correct connections and parallel branches

---

#### Step 5 — Start an Execution

**Step 5.1: Navigate**
1. Click on your state machine `handson-doc-proc-state-machine`
2. Click **Start execution**

**Step 5.2: Enter Input**

```json
{
  "file_key": "documents/invoice-2024.pdf",
  "file_size": 524288,
  "uploaded_by": "alice@example.com"
}
```

Click **Start execution**

**Step 5.3: Watch the Visual Execution**

**Expected View:** The execution graph shows each state highlighted as it runs:
- Green checkmark = state succeeded
- Blue spinner = state currently running
- Red X = state failed

**📸 Screenshot:** Visual execution graph with all states showing green checkmarks (successful execution)

**Step 5.4: Test Failure Path**

Start another execution with invalid input:
```json
{
  "file_key": "documents/malware.exe",
  "file_size": 1024
}
```

**Expected Outcome:** Validate state turns red → routes to ValidationFailed → execution status = FAILED

**📸 Screenshot:** Visual execution showing Validate state red and ValidationFailed path highlighted

### METHOD B — AWS CLI Method

```bash
# ── Set variables ─────────────────────────────────────────────────────────────
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT="handson-doc-proc"

# ── 1. Create Lambda IAM role ─────────────────────────────────────────────────
LAMBDA_ROLE_ARN=$(aws iam create-role \
  --role-name ${PROJECT}-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"}]
  }' \
  --query Role.Arn --output text)

aws iam attach-role-policy \
  --role-name ${PROJECT}-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

sleep 10  # IAM propagation delay
echo "✅ Lambda role: $LAMBDA_ROLE_ARN"

# ── 2. Package and deploy all 6 Lambda functions ──────────────────────────────
cd src && zip ../steps.zip steps.py && cd ..

declare -A HANDLER_MAP=(
  ["validate"]="steps.validate"
  ["extract_text"]="steps.extract_text"
  ["classify"]="steps.classify"
  ["check_compliance"]="steps.check_compliance"
  ["store_results"]="steps.store_results"
  ["notify"]="steps.notify"
)

declare -A LAMBDA_ARNS=()

for STEP in validate extract_text classify check_compliance store_results notify; do
  aws lambda create-function \
    --function-name ${PROJECT}-${STEP} \
    --runtime python3.11 \
    --role $LAMBDA_ROLE_ARN \
    --handler ${HANDLER_MAP[$STEP]} \
    --zip-file fileb://steps.zip \
    --timeout 30

  aws lambda wait function-active --function-name ${PROJECT}-${STEP}

  LAMBDA_ARNS[$STEP]=$(aws lambda get-function \
    --function-name ${PROJECT}-${STEP} \
    --query Configuration.FunctionArn --output text)

  echo "✅ Lambda deployed: ${PROJECT}-${STEP} → ${LAMBDA_ARNS[$STEP]}"
done

# ── 3. Create Step Functions IAM role ─────────────────────────────────────────
SFN_ROLE_ARN=$(aws iam create-role \
  --role-name ${PROJECT}-sfn-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow",
      "Principal": {"Service": "states.amazonaws.com"},
      "Action": "sts:AssumeRole"}]
  }' \
  --query Role.Arn --output text)

# Build Lambda ARN list for the policy
LAMBDA_ARN_LIST=$(python3 -c "
import json
arns = [
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-validate',
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-extract_text',
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-classify',
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-check_compliance',
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-store_results',
  'arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PROJECT}-notify',
]
print(json.dumps(arns))
")

aws iam put-role-policy \
  --role-name ${PROJECT}-sfn-role \
  --policy-name invoke-step-lambdas \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"lambda:InvokeFunction\"],
      \"Resource\": $LAMBDA_ARN_LIST
    }]
  }"

sleep 5
echo "✅ Step Functions role: $SFN_ROLE_ARN"

# ── 4. Create the State Machine ───────────────────────────────────────────────
STATE_MACHINE_ARN=$(aws stepfunctions create-state-machine \
  --name ${PROJECT}-state-machine \
  --type STANDARD \
  --role-arn $SFN_ROLE_ARN \
  --definition "{
    \"Comment\": \"Document processing workflow\",
    \"StartAt\": \"Validate\",
    \"States\": {
      \"Validate\": {
        \"Type\": \"Task\",
        \"Resource\": \"${LAMBDA_ARNS[validate]}\",
        \"Retry\": [{
          \"ErrorEquals\": [\"Lambda.ServiceException\",\"Lambda.TooManyRequestsException\"],
          \"IntervalSeconds\": 2, \"MaxAttempts\": 3, \"BackoffRate\": 2
        }],
        \"Catch\": [
          {\"ErrorEquals\": [\"ValueError\"], \"Next\": \"ValidationFailed\", \"ResultPath\": \"\$.error\"},
          {\"ErrorEquals\": [\"States.ALL\"],  \"Next\": \"ProcessingFailed\", \"ResultPath\": \"\$.error\"}
        ],
        \"Next\": \"ExtractText\"
      },
      \"ExtractText\": {
        \"Type\": \"Task\",
        \"Resource\": \"${LAMBDA_ARNS[extract_text]}\",
        \"Retry\": [{\"ErrorEquals\": [\"States.ALL\"], \"IntervalSeconds\": 2, \"MaxAttempts\": 2, \"BackoffRate\": 1.5}],
        \"Next\": \"ParallelAnalysis\"
      },
      \"ParallelAnalysis\": {
        \"Type\": \"Parallel\",
        \"Branches\": [
          {\"StartAt\": \"Classify\",
           \"States\": {\"Classify\": {\"Type\": \"Task\", \"Resource\": \"${LAMBDA_ARNS[classify]}\", \"End\": true}}},
          {\"StartAt\": \"CheckCompliance\",
           \"States\": {\"CheckCompliance\": {\"Type\": \"Task\", \"Resource\": \"${LAMBDA_ARNS[check_compliance]}\", \"End\": true}}}
        ],
        \"ResultSelector\": {\"classification.\$\": \"\$[0].classification\", \"compliance.\$\": \"\$[1].compliance\"},
        \"ResultPath\": \"\$.analysis\",
        \"Next\": \"StoreResults\"
      },
      \"StoreResults\": {\"Type\": \"Task\", \"Resource\": \"${LAMBDA_ARNS[store_results]}\", \"Next\": \"Notify\"},
      \"Notify\":       {\"Type\": \"Task\", \"Resource\": \"${LAMBDA_ARNS[notify]}\",       \"Next\": \"Success\"},
      \"Success\":          {\"Type\": \"Succeed\"},
      \"ValidationFailed\": {\"Type\": \"Fail\", \"Error\": \"ValidationError\", \"Cause\": \"Document failed validation\"},
      \"ProcessingFailed\":  {\"Type\": \"Fail\", \"Error\": \"ProcessingError\",  \"Cause\": \"Unexpected error\"}
    }
  }" \
  --query stateMachineArn --output text)

echo "✅ State Machine ARN: $STATE_MACHINE_ARN"

# ── 5. Start a test execution ─────────────────────────────────────────────────
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{
    "file_key": "documents/invoice-2024.pdf",
    "file_size": 524288,
    "uploaded_by": "alice@example.com"
  }' \
  --query executionArn --output text)

echo "Execution started: $EXECUTION_ARN"
echo "Waiting 15 seconds for completion..."
sleep 15

# ── 6. Check result ───────────────────────────────────────────────────────────
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query "{Status:status,StartDate:startDate,StopDate:stopDate}"
# Expected: Status=SUCCEEDED

aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query "output" --output text | python3 -m json.tool
# Expected: full merged output with validation, extraction, analysis, storage, notification

# ── 7. Test failure path ──────────────────────────────────────────────────────
FAIL_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"file_key": "documents/malware.exe", "file_size": 1024}' \
  --query executionArn --output text)
sleep 10
aws stepfunctions describe-execution \
  --execution-arn $FAIL_ARN \
  --query "{Status:status,StopDate:stopDate}"
# Expected: Status=FAILED
```

---

## 7. Code Deep Dive

**`src/steps.py` — Key Sections Explained:**

```python
# validate() — raises Python ValueError to trigger Catch in state machine
def validate(event: dict, context) -> dict:
    file_key  = event.get("file_key", "")
    file_size = event.get("file_size", 0)

    allowed_types = (".pdf", ".txt", ".docx", ".csv")
    if not any(file_key.lower().endswith(ext) for ext in allowed_types):
        raise ValueError(f"Unsupported file type: {file_key}")
    # Step Functions catches "ValueError" (the Python class name)
    # The Catch block routes this to the "ValidationFailed" Fail state
    # If we raised Exception instead, it would go to "States.ALL" catch-all

    return {
        **event,                    # ← Pass ALL previous state through
        "validation": {             # ← ADD our results to state
            "status": "passed",
            "file_type": file_key.rsplit(".", 1)[-1].lower(),
        }
    }
    # IMPORTANT: return {**event, ...new data...}
    # This is how data flows through the pipeline — each step adds its results
    # to the state and passes everything to the next step
```

```python
# classify() — Parallel branch (branch 0 of ParallelAnalysis)
def classify(event: dict, context) -> dict:
    # Returns ONLY classification data — not {**event, ...}
    # In a Parallel branch, each branch gets its OWN copy of the input
    # The Parallel state collects outputs as an ARRAY: [$[0], $[1]]
    # ResultSelector then reshapes: "classification.$": "$[0].classification"
    return {
        "classification": {
            "category":   category,
            "confidence": 0.92,
        }
    }
```

```python
# check_compliance() — Parallel branch (branch 1 of ParallelAnalysis)
def check_compliance(event: dict, context) -> dict:
    text = event.get("extraction", {}).get("text_preview", "")
    # Regex-based PII detection
    has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    has_ssn   = bool(re.search(r'\b\d{3}-\d{2}-\d{4}\b', text))
    return {
        "compliance": {
            "status":  "flagged" if (has_email or has_ssn) else "clean",
            "has_pii": has_email or has_ssn,
        }
    }
```

**`state_machine/definition.json` — ASL Key Patterns:**

```json
// Retry with exponential backoff
"Retry": [{
  "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
  "IntervalSeconds": 2,    // Wait 2s before first retry
  "MaxAttempts": 3,        // Retry up to 3 times
  "BackoffRate": 2         // Each retry waits 2× longer: 2s, 4s, 8s
}]
// Total wait before giving up: 2 + 4 + 8 = 14 seconds
```

```json
// Catch block — route specific errors to specific states
"Catch": [
  {
    "ErrorEquals": ["ValueError"],      // Python class name as string
    "Next": "ValidationFailed",         // Which state to go to on error
    "ResultPath": "$.error"             // Where to store error details in state
    // $.error = preserve original input + add error details alongside it
    // "$.":      REPLACE entire input with error details (loses original data!)
  },
  {
    "ErrorEquals": ["States.ALL"],      // Catch-all — any error not caught above
    "Next": "ProcessingFailed",
    "ResultPath": "$.error"
  }
]
```

```json
// Parallel state — run branches simultaneously and collect results
"ParallelAnalysis": {
  "Type": "Parallel",
  "Branches": [...],
  "ResultSelector": {
    "classification.$": "$[0].classification",   // Take branch 0 output
    "compliance.$":     "$[1].compliance"         // Take branch 1 output
  },
  "ResultPath": "$.analysis"    // Store parallel results at $.analysis in state
  // The full state after this: original_input + $.analysis = {classification, compliance}
}
```

**`terraform/main.tf` — Key Patterns:**

```hcl
# for_each pattern — creates 6 Lambda functions with one block
locals {
  handler_map = {
    validate         = "steps.validate"
    extract_text     = "steps.extract_text"
    classify         = "steps.classify"
    check_compliance = "steps.check_compliance"
    store_results    = "steps.store_results"
    notify           = "steps.notify"
  }
}

resource "aws_lambda_function" "step" {
  for_each      = local.handler_map          # Iterates over map keys
  function_name = "${local.name_prefix}-${each.key}"  # e.g. handson-doc-proc-validate
  handler       = each.value                 # e.g. steps.validate
  # All other config is identical for all 6 functions
}
# Result: 6 Lambda functions created from one resource block
```

```hcl
# State machine — Terraform generates definition with actual Lambda ARNs
definition = jsonencode({
  States = {
    Validate = {
      Resource = aws_lambda_function.step["validate"].arn  # Actual ARN injected by Terraform
    }
  }
})
# The state_machine/definition.json file uses "${ValidateLambdaArn}" placeholders
# Terraform generates the real definition with actual ARNs at apply time
```

**Common Mistakes:**

| Mistake | Effect | Fix |
|---------|--------|-----|
| Not returning `{**event, ...}` from Task Lambda | Next state loses previous data | Always spread the event |
| Using Express workflow for long-running tasks | Execution fails after 5 min | Use Standard for tasks > 5 min |
| Forgetting `ResultPath` in Catch | Error replaces entire state — original input lost | Set `ResultPath: "$.error"` |
| Parallel branch returning `{**event, ...}` | Redundant data in array makes ResultSelector complex | Only return the new data from parallel branches |
| Step Functions role missing `lambda:InvokeFunction` | `States.Runtime` error | Add Lambda invoke permission for all function ARNs |

---

## 8. Verification & Validation

```bash
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?name=='handson-doc-proc-state-machine'].stateMachineArn" \
  --output text)

# 1. Verify state machine is ACTIVE
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query "{Name:name,Status:status,Type:type}"
# Expected: Status=ACTIVE, Type=STANDARD

# 2. Start successful execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"file_key":"documents/invoice-2024.pdf","file_size":524288,"uploaded_by":"verify@test.com"}' \
  --query executionArn --output text)
echo "Execution: $EXECUTION_ARN"
sleep 20

# 3. Check execution succeeded
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query "{Status:status,StartDate:startDate,StopDate:stopDate}"
# Expected: Status=SUCCEEDED

# 4. View all state transitions
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --query "events[?type=='TaskStateEntered' || type=='TaskSucceeded'].{Type:type,State:stateEnteredEventDetails.name,Time:timestamp}" \
  --output table
# Expected: Validate → ExtractText → ParallelAnalysis (Classify + CheckCompliance same time) → StoreResults → Notify

# 5. Verify parallel branches ran simultaneously
python3 << 'EOF'
import json, subprocess
from datetime import datetime

result = subprocess.run([
    "aws", "stepfunctions", "get-execution-history",
    "--execution-arn", "PASTE_EXECUTION_ARN_HERE",
    "--query", "events[?type=='TaskStateEntered'].{State:stateEnteredEventDetails.name,Time:timestamp}"
], capture_output=True, text=True)
events = json.loads(result.stdout)
classify_time = next((e["Time"] for e in events if e.get("State") == "Classify"), None)
compliance_time = next((e["Time"] for e in events if e.get("State") == "CheckCompliance"), None)
if classify_time and compliance_time:
    diff = abs((datetime.fromisoformat(classify_time.replace("Z","")) -
                datetime.fromisoformat(compliance_time.replace("Z",""))).total_seconds())
    print(f"Parallel branch time difference: {diff:.3f}s")
    print("✅ Parallel execution confirmed" if diff < 1 else "❌ Sequential — check state machine")
EOF

# 6. View final output
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query "output" --output text | python3 -m json.tool
# Expected: full JSON with validation, extraction, analysis (classification+compliance), storage, notification

# 7. Test failure path
FAIL_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"file_key":"documents/malware.exe","file_size":1024}' \
  --query executionArn --output text)
sleep 10
aws stepfunctions describe-execution \
  --execution-arn $FAIL_ARN \
  --query "{Status:status}"
# Expected: Status=FAILED

# 8. List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query "executions[*].{Name:name,Status:status,StartDate:startDate}" \
  --output table
# Expected: mix of SUCCEEDED and FAILED executions
```

**Console Verification:**

| Resource | Where to Check | Expected State |
|----------|---------------|---------------|
| State Machine | Step Functions → State machines | `handson-doc-proc-state-machine`, Active |
| Visual Graph | State machine → Graph inspector | All states visible with correct connections |
| Executions | State machine → Executions tab | Mix of SUCCEEDED and FAILED |
| Lambda Functions | Lambda → Functions | 6 `handson-doc-proc-*` functions |
| Step Functions Role | IAM → Roles | `handson-doc-proc-sfn-role` with inline policy |

---

## 9. Observations & Learning Notes

1. **Visual execution graph:** The Step Functions console is one of the best debugging tools in AWS. Every state is highlighted in real time. Click on any state in an execution to see its exact input and output JSON. This is invaluable when debugging data flow issues.

2. **State data flow pattern:** Each Task Lambda receives the FULL current state as input and returns its NEW results. The standard pattern is `return {**event, "my_step": {...my results...}}`. This accumulates all data as it flows through the workflow.

3. **Parallel branch data isolation:** Each branch in a Parallel state gets its OWN independent copy of the input — changes in one branch don't affect the other. The Parallel state collects all branch outputs as an array: `[branch0_output, branch1_output]`. Use `ResultSelector` to reshape this array before storing it with `ResultPath`.

4. **Retry vs Catch:** Retry is for transient errors (throttling, service exceptions) — Step Functions retries the same state. Catch is for business logic errors (validation failure) — Step Functions routes to a different state. Use both together.

5. **ResultPath: "$.error"** vs **ResultPath: "$"**: With `"$.error"`, the original input is preserved and the error details are added at `$.error`. With `"$"`, the error details REPLACE the entire state — you lose the original input. Always use `"$.error"` in Catch blocks.

6. **Standard Workflow pricing:** $0.025 per 1,000 state transitions. Our 6-state workflow = 8 transitions per execution (including parallel). 1,000 executions = ~8,000 transitions ≈ $0.20. First 4,000 transitions/month are free.

7. **Execution history (90 days):** Standard workflows store full execution history for 90 days. You can go back and debug any execution from 89 days ago. Express workflows only log to CloudWatch — no history in the console.

---

## 10. Screenshots Guidance

| When | What to Capture |
|------|----------------|
| Before | Lambda Functions list (empty) |
| After Step 2 | Lambda Functions list showing all 6 `handson-doc-proc-*` functions |
| After Step 3 | IAM role `handson-doc-proc-sfn-role` showing inline policy |
| After Step 4 | Step Functions console showing new state machine with visual graph |
| After Step 4 | State machine Definition tab showing ASL JSON |
| After Step 5 | Visual execution graph with all states green (successful run) |
| After Step 5 | Execution Events tab showing state transitions with timestamps |
| Testing | Parallel states (Classify + CheckCompliance) showing same start timestamp |
| Failure test | Visual execution graph showing Validate red → ValidationFailed path |
| Final | Execution output tab showing complete merged JSON result |

---

## 11. Cleanup Steps

```bash
# 1. Delete state machine
aws stepfunctions delete-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN
echo "✅ State machine deleted"

# 2. Delete all 6 Lambda functions
for STEP in validate extract_text classify check_compliance store_results notify; do
  aws lambda delete-function --function-name handson-doc-proc-${STEP}
  echo "✅ Lambda deleted: handson-doc-proc-${STEP}"
done

# 3. Delete IAM roles
aws iam delete-role-policy \
  --role-name handson-doc-proc-sfn-role \
  --policy-name invoke-step-lambdas

aws iam delete-role --role-name handson-doc-proc-sfn-role

aws iam detach-role-policy \
  --role-name handson-doc-proc-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam delete-role --role-name handson-doc-proc-lambda-role

# 4. Delete CloudWatch Log Groups
for STEP in validate extract_text classify check_compliance store_results notify; do
  aws logs delete-log-group \
    --log-group-name /aws/lambda/handson-doc-proc-${STEP} 2>/dev/null
done

echo "✅ All Step Functions resources deleted"

# Verify nothing remains
aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name,'handson-doc-proc')]"
# Expected: empty array
```

**Terraform Cleanup:**
```bash
cd terraform
terraform destroy -auto-approve
# Expected: All 6 Lambda functions + state machine + 2 IAM roles destroyed
```

---

## 12. Estimated AWS Cost

| Resource | Free Tier | After Free Tier |
|----------|-----------|----------------|
| Step Functions Standard | **4,000 state transitions/month free** | $0.025 per 1K transitions |
| Lambda (×6 functions) | 1M requests/month free | $0.20/million |
| SNS (notify step) | 1M publishes/month free | |
| **Lab cost (100 executions × 8 transitions = 800 transitions)** | **$0** | Within free tier |
| **Per 1,000 executions after free tier** | **~$0.20** | 1000 × 8 transitions = 8K → $0.20 |

> **Free tier math:** 4,000 free transitions/month. Our workflow uses 8 transitions per execution (Validate, ExtractText, ParallelAnalysis entry, Classify, CheckCompliance, StoreResults, Notify, Success). You get 500 free executions/month.

> ✅ **Free Tier Eligible for lab usage.** A few hundred test executions costs nothing.

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
