# Steps — Project 4.6 Step Functions Workflow

## Phase 1 — Deploy

```bash
cd terraform
terraform init && terraform apply -auto-approve
STATE_MACHINE_ARN=$(terraform output -raw state_machine_arn)
echo "State Machine: $STATE_MACHINE_ARN"
```

---

## Phase 2 — Start an Execution

```bash
# Start a workflow execution
EXECUTION=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{
    "file_key": "documents/invoice-2024.pdf",
    "file_size": 524288,
    "uploaded_by": "alice@example.com"
  }' \
  --query "executionArn" --output text)

echo "Execution: $EXECUTION"
```

---

## Phase 3 — Monitor Execution

```bash
# Check execution status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION \
  --query "{Status:status,StartDate:startDate,StopDate:stopDate}"

# Get execution history (all state transitions)
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --query "events[*].{Type:type,Timestamp:timestamp}" \
  --output table

# View final output
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION \
  --query "output" --output text | python3 -m json.tool
```

---

## Phase 4 — Test Failure Handling

```bash
# Trigger validation failure (unsupported file type)
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{
    "file_key": "documents/malware.exe",
    "file_size": 1024
  }'

# Watch it fail at the Validate step and transition to ValidationFailed
```

---

## Phase 5 — View in Console

1. Go to **Step Functions** → **State machines**
2. Click your state machine
3. Click on an execution
4. See the **visual workflow** — each state highlighted as it runs
5. Click on a state to see input/output

---

## Screenshots to Take
- [ ] Step Functions visual workflow diagram in console
- [ ] Successful execution with all states green
- [ ] Parallel branches running simultaneously
- [ ] Failed execution showing which state failed
- [ ] Execution history showing all state transitions
- [ ] Final output JSON with all results merged
