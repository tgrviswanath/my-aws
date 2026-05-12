# Project 4.6 — Step Functions Workflow

## What This Does
Orchestrates a multi-step document processing workflow using AWS Step Functions. Each step is a Lambda function. Step Functions handles retries, error handling, parallel execution, and state management.

## Workflow
```
Upload Document
  → Validate (check file type, size)
  → Extract Text (parse content)
  → Parallel:
      ├── Classify (categorize document)
      └── Check Compliance (scan for sensitive data)
  → Store Results (save to DynamoDB)
  → Notify (send SNS notification)
```

## Services Used
| Service | Role |
|---------|------|
| Step Functions | Orchestrate the workflow |
| Lambda | Each step's business logic |
| S3 | Document storage |
| DynamoDB | Results storage |
| SNS | Completion notification |

## Key Concepts
| Concept | Description |
|---------|-------------|
| State machine | The workflow definition (JSON/YAML) |
| Task state | Invokes a Lambda or other service |
| Choice state | Conditional branching |
| Parallel state | Run multiple branches simultaneously |
| Wait state | Pause for a duration or until a timestamp |
| Catch/Retry | Error handling per state |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output state_machine_arn
```

## Lessons Learned
- Step Functions Express vs Standard: Express is cheaper for high-volume short workflows; Standard for long-running (up to 1 year)
- Use `ResultPath` to merge Lambda output into the state without overwriting input
- `Catch` blocks handle specific error types — always catch `States.ALL` as a fallback
- Parallel branches must all succeed for the workflow to continue
- Step Functions console shows a visual execution graph — invaluable for debugging

## Code

### `src/workflow_handlers.py` — Step Functions task Lambda handlers

```bash
pip install boto3

# Start a workflow execution
export STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789:stateMachine:handson-workflow
python -c "
import boto3, json
sf = boto3.client('stepfunctions')
resp = sf.start_execution(
    stateMachineArn='$STATE_MACHINE_ARN',
    input=json.dumps({'file_key': 'uploads/data.csv', 'bucket': 'my-bucket'})
)
print(resp['executionArn'])
"
```

States: Upload → Validate → Process → Notify. Each state is a separate Lambda function.
