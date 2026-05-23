# Verification & Validation — Project 4.6 Step Functions Workflow

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| State Machine | Step Functions → State machines | `handson-document-workflow`, Status = **Active** |
| State Machine Type | Details tab | Type = Standard |
| Visual Workflow | State machine → Definition tab | All states visible in graph |
| Executions | State machine → Executions tab | Successful executions listed |
| Lambda Functions | Lambda → Functions | One function per workflow step |

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
# aws_sfn_state_machine.document_workflow
# aws_lambda_function.validate
# aws_lambda_function.extract_text
# aws_lambda_function.classify
# aws_lambda_function.check_compliance
# aws_lambda_function.store_results
# aws_lambda_function.notify
# aws_iam_role.step_functions_exec
# aws_iam_role.lambda_exec

terraform state show aws_sfn_state_machine.document_workflow
# Shows: type=STANDARD, definition (JSON state machine definition)

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
{ "Name": "handson-document-workflow", "Status": "ACTIVE", "Type": "STANDARD" }
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
