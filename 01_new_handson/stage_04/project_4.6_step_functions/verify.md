# Verification & Validation — Project 4.6 Step Functions Workflow

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| State Machine | Step Functions → State machines | `handson-doc-proc-state-machine`, Status = **Active** |
| State Machine Type | Details tab | Type = Standard |
| Visual Workflow | State machine → Definition tab | All states visible in graph: Validate → ExtractText → ParallelAnalysis → StoreResults → Notify |
| Executions | State machine → Executions tab | Successful executions listed |
| Lambda Functions | Lambda → Functions | 6 functions: `handson-doc-proc-validate`, `handson-doc-proc-extract_text`, `handson-doc-proc-classify`, `handson-doc-proc-check_compliance`, `handson-doc-proc-store_results`, `handson-doc-proc-notify` |

📸 Screenshot: Step Functions visual workflow diagram showing all states  
📸 Screenshot: Successful execution with all states green  
📸 Screenshot: Parallel branches running simultaneously  
📸 Screenshot: Failed execution showing which state failed (validation error)

---

## 2. AWS CLI Verification

```bash
STATE_MACHINE_ARN=$(cd terraform && terraform output -raw state_machine_arn)

# 2.1 State machine active
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query "{Name:name,Status:status,Type:type}"
# Expected: Status=ACTIVE, Type=STANDARD

# 2.2 Start a successful execution
EXECUTION=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"file_key":"documents/invoice-2024.pdf","file_size":524288,"uploaded_by":"verify@example.com"}' \
  --query "executionArn" --output text)
echo "Execution: $EXECUTION"

# 2.3 Wait for completion
sleep 15
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION \
  --query "{Status:status,StartDate:startDate,StopDate:stopDate}"
# Expected: Status=SUCCEEDED

# 2.4 View all state transitions
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --query "events[?type=='TaskStateEntered' || type=='TaskSucceeded'].{Type:type,State:stateEnteredEventDetails.name,Timestamp:timestamp}" \
  --output table
# Expected: Validate → ExtractText → Parallel(Classify+Compliance) → StoreResults → Notify

# 2.5 View final output
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION \
  --query "output" --output text | python3 -m json.tool
# Expected: merged output from all steps

# 2.6 Test failure path — unsupported file type
FAILED_EXEC=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"file_key":"documents/malware.exe","file_size":1024}' \
  --query "executionArn" --output text)
sleep 10
aws stepfunctions describe-execution \
  --execution-arn $FAILED_EXEC \
  --query "{Status:status,Error:cause}"
# Expected: Status=FAILED, Error mentions validation failure

# 2.7 List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query "executions[*].{Name:name,Status:status,StartDate:startDate}" \
  --output table
# Expected: mix of SUCCEEDED and FAILED executions
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_sfn_state_machine.doc_processor
# aws_lambda_function.step["validate"]
# aws_lambda_function.step["extract_text"]
# aws_lambda_function.step["classify"]
# aws_lambda_function.step["check_compliance"]
# aws_lambda_function.step["store_results"]
# aws_lambda_function.step["notify"]
# aws_iam_role.sfn
# aws_iam_role.lambda
# aws_iam_role_policy.sfn_lambda
# aws_iam_role_policy_attachment.lambda_basic

terraform state show aws_sfn_state_machine.doc_processor
# Shows: type=STANDARD, name=handson-doc-proc-state-machine, definition JSON

terraform output
# Expected: state_machine_arn, state_machine_name

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Parallel Branch Timing

```bash
# Verify parallel branches ran simultaneously (not sequentially)
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --query "events[?type=='TaskStateEntered'].{State:stateEnteredEventDetails.name,Time:timestamp}"

# Classify and CheckCompliance should have nearly identical timestamps
# If sequential, they'd be seconds apart; if parallel, they'd be within milliseconds
python3 << 'EOF'
import json, subprocess
from datetime import datetime

result = subprocess.run([
    "aws", "stepfunctions", "get-execution-history",
    "--execution-arn", "PASTE_EXECUTION_ARN",
    "--query", "events[?type=='TaskStateEntered'].{State:stateEnteredEventDetails.name,Time:timestamp}"
], capture_output=True, text=True)

events = json.loads(result.stdout)
classify_time = next((e["Time"] for e in events if e["State"] == "Classify"), None)
compliance_time = next((e["Time"] for e in events if e["State"] == "CheckCompliance"), None)

if classify_time and compliance_time:
    diff = abs((datetime.fromisoformat(classify_time.replace("Z","")) -
                datetime.fromisoformat(compliance_time.replace("Z",""))).total_seconds())
    print(f"Parallel branch time difference: {diff:.3f}s")
    print("✅ Parallel" if diff < 1 else "❌ Sequential (check state machine definition)")
EOF
```

---

## 5. Expected Successful Outputs

**State machine status:**
```json
{ "Name": "handson-doc-proc-state-machine", "Status": "ACTIVE", "Type": "STANDARD" }
```

**Execution history (state transitions):**
```
Type                  State             Timestamp
TaskStateEntered      Validate          2024-01-01T12:00:00Z
TaskSucceeded         Validate          2024-01-01T12:00:01Z
TaskStateEntered      ExtractText       2024-01-01T12:00:01Z
TaskSucceeded         ExtractText       2024-01-01T12:00:02Z
TaskStateEntered      Classify          2024-01-01T12:00:02Z  ← parallel
TaskStateEntered      CheckCompliance   2024-01-01T12:00:02Z  ← parallel (same time)
TaskSucceeded         Classify          2024-01-01T12:00:03Z
TaskSucceeded         CheckCompliance   2024-01-01T12:00:03Z
TaskStateEntered      StoreResults      2024-01-01T12:00:03Z
TaskStateEntered      Notify            2024-01-01T12:00:04Z
```

**Failed execution (validation error):**
```json
{ "Status": "FAILED", "Error": "ValidationError: Unsupported file type: .exe" }
```

---

## 6. Verification Checklist

- [ ] State machine status = ACTIVE, type = STANDARD
- [ ] All Lambda step functions deployed
- [ ] Successful execution: status = SUCCEEDED
- [ ] All states appear in execution history (Validate → Extract → Parallel → Store → Notify)
- [ ] Parallel branches (Classify + CheckCompliance) start at same timestamp
- [ ] Final output contains merged results from all steps
- [ ] Failed execution (`.exe` file): status = FAILED at Validate step
- [ ] Visual workflow in console shows all states with correct connections
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
