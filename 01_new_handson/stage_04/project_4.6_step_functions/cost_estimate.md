# Cost Estimate — Project 4.6: Step Functions Express Workflow

## Architecture Summary
Step Functions Express Workflow orchestrates multiple Lambda functions with parallel execution states, conditional branching (Choice state), retry/catch error handling, and a final aggregation Lambda — all coordinated as a serverless state machine.

---

## Free Tier Coverage

| Service | Free Tier Allowance | Type | Notes |
|---|---|---|---|
| AWS Step Functions (Express) | 4,000 state transitions/month | Always free (perpetual) | Express Workflows only |
| AWS Step Functions (Standard) | ~~— none~~  | No free tier | Standard has no free tier |
| AWS Lambda | 1,000,000 requests/month | Always free (perpetual) | All orchestrated functions |
| AWS Lambda | 400,000 GB-seconds compute/month | Always free (perpetual) | Shared across functions |
| CloudWatch Logs | 5 GB ingestion/month | First 12 months | Step Functions execution logs |
| CloudWatch Logs Insights | Free queries during free tier | First 12 months | Query execution history |
| X-Ray (basic tracing) | 100,000 traces/month | Always free | First 1M traces/month free |

---

## Express vs Standard Workflow — Key Difference

| Feature | Express Workflow | Standard Workflow |
|---|---|---|
| Duration | Up to 5 minutes | Up to 1 year |
| Execution model | At-least-once | Exactly-once |
| Free tier | ✅ 4,000 transitions/month | ❌ No free tier |
| Cost beyond free | $0.00001 per state transition | $0.025 per 1,000 transitions |
| Use case | High-volume, short workflows | Long-running, transactional |
| **Best for this lab** | ✅ Recommended | ❌ Avoid (costs money) |

> ⚠️ **Use Express Workflows for this lab** to stay within the free tier.

---

## State Transition Count Estimate

A typical Express Workflow execution with parallel states:
```
Start → Task1 (Lambda) → Parallel State [Branch A + Branch B] → Choice State → Task2 → End
= 7 state transitions per execution

4,000 free transitions ÷ 7 transitions per execution = ~571 free executions/month
```

For a lab with 50-100 test executions, well within free tier.

---

## Estimated Monthly Cost for This Lab

| Component | Usage (Lab Scale) | Cost |
|---|---|---|
| Step Functions (Express) | < 4,000 state transitions | **$0.00** (Free Tier) |
| Lambda — step-1-validate | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — step-2a-process (parallel) | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — step-2b-notify (parallel) | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — step-3-aggregate | < 1M invocations, 128MB | **$0.00** (Free Tier) |
| Lambda — error-handler | Rare invocations | **$0.00** (Free Tier) |
| CloudWatch Logs | Execution logs | **$0.00** (Free Tier) |
| X-Ray Tracing | < 100,000 traces | **$0.00** (Free Tier) |
| **Total** | | **$0.00** |

> ✅ **This lab runs entirely within AWS Free Tier — $0 cost for typical hands-on usage.**

---

## Cost Beyond Free Tier

| Service | Pricing |
|---|---|
| Step Functions Express (beyond 4,000 transitions) | $0.00001 per state transition |
| Step Functions Express duration | $0.00001 per GB-second |
| Step Functions Standard (no free tier) | $0.025 per 1,000 state transitions |
| Lambda requests (beyond 1M) | $0.20 per million |
| Lambda compute (beyond free) | $0.0000166667 per GB-second |
| CloudWatch Logs (beyond free) | $0.50 per GB ingestion |
| X-Ray (beyond 100K traces) | $0.05 per trace |

### Example: 10,000 Express Workflow executions at 7 transitions each
```
10,000 × 7 = 70,000 transitions
Free tier: 4,000 transitions
Billable: 66,000 × $0.00001 = $0.66/month
```

---

## State Machine Definition Size Note

Step Functions charges apply only to executions, not to the size of the state machine definition (ASL JSON). Complex parallel states with many branches are free to define.

---

## Cleanup Commands

### Delete State Machines
```bash
# List state machines to find ARNs
aws stepfunctions list-state-machines \
  --query "stateMachines[?starts_with(name, 'order-processing') || starts_with(name, 'image-pipeline')].{Name:name,Arn:stateMachineArn}" \
  --output table

# Stop any running executions first
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?name=='order-processing-workflow'].stateMachineArn" \
  --output text)

# List running executions
aws stepfunctions list-executions \
  --state-machine-arn ${STATE_MACHINE_ARN} \
  --status-filter RUNNING \
  --query "executions[].executionArn" --output text

# Stop each running execution (replace EXECUTION_ARN)
# aws stepfunctions stop-execution --execution-arn <EXECUTION_ARN>

# Delete the state machine
aws stepfunctions delete-state-machine --state-machine-arn ${STATE_MACHINE_ARN}
echo "State machine deleted"
```

### Delete Lambda Functions
```bash
# Delete all orchestrated Lambda functions
for FUNCTION in step-validate step-process-a step-process-b step-aggregate step-error-handler; do
  echo "Deleting Lambda: ${FUNCTION}"
  aws lambda delete-function --function-name ${FUNCTION} 2>/dev/null || \
    echo "${FUNCTION} not found, skipping"
done
```

### Delete IAM Roles
```bash
# Step Functions execution role
aws iam detach-role-policy \
  --role-name stepfunctions-execution-role \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaRole 2>/dev/null

aws iam detach-role-policy \
  --role-name stepfunctions-execution-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess 2>/dev/null

aws iam delete-role --role-name stepfunctions-execution-role

# Lambda execution roles
for ROLE in step-validate-role step-process-role step-aggregate-role; do
  aws iam detach-role-policy \
    --role-name ${ROLE} \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null
  aws iam delete-role --role-name ${ROLE} 2>/dev/null
  echo "Deleted: ${ROLE}"
done
```

### Delete CloudWatch Log Groups
```bash
# Step Functions execution logs
aws logs delete-log-group --log-group-name /aws/states/order-processing-workflow

# Lambda function logs
for FUNCTION in step-validate step-process-a step-process-b step-aggregate; do
  aws logs delete-log-group --log-group-name /aws/lambda/${FUNCTION}
done
echo "All log groups deleted"
```

---

## Cleanup Verification
```bash
echo "=== Step Functions State Machines ==="
aws stepfunctions list-state-machines \
  --query "stateMachines[?contains(name, 'step') || contains(name, 'workflow')].name" \
  --output text

echo "=== Lambda Functions ==="
aws lambda list-functions \
  --query "Functions[?starts_with(FunctionName, 'step-')].FunctionName" \
  --output text

echo "=== CloudWatch Log Groups ==="
aws logs describe-log-groups \
  --query "logGroups[?contains(logGroupName, 'states') || starts_with(logGroupName, '/aws/lambda/step')].logGroupName" \
  --output text

echo "All clear if outputs are empty."
```

---

*Region: us-east-1 | Prices as of 2024 — verify at https://aws.amazon.com/pricing/*
