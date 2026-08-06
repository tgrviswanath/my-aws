# Project 4.6 — Step Functions Workflow Orchestration

**Stage:** 04 | **Level:** Intermediate–Advanced | **Est. Time:** 3–4 hours | **Cost:** ~$0.30/month

This project orchestrates a multi-step order fulfillment process using AWS Step Functions Standard
Workflow. Four Lambda functions are chained together as states in an Amazon States Language (ASL)
JSON definition: `ValidateOrder` checks the payload structure, `CheckInventory` queries stock and
branches via a Choice state — routing to an `OutOfStock` terminal state if quantity is zero —
`ProcessPayment` charges the customer with a Catch block for payment failures, and
`SendNotification` publishes a success or failure message to SNS. Every state transition is
durably recorded and visible in the Step Functions console as an execution timeline, providing
built-in auditability that would otherwise require custom logging across four independent Lambda
functions. Final order status is written to DynamoDB by the last successful state.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Step Functions (Standard) | Orchestrates state machine; stores execution history for 90 days | $0.000025/state transition |
| Lambda — ValidateOrder | Checks required fields, returns validated order object | ~$0.20/1M requests |
| Lambda — CheckInventory | Queries DynamoDB stock table; returns `{"in_stock": true/false}` | ~$0.20/1M requests |
| Lambda — ProcessPayment | Charges payment; raises `PaymentFailedException` on decline | ~$0.20/1M requests |
| Lambda — SendNotification | Publishes success or failure message to SNS topic | ~$0.20/1M requests |
| SNS | Delivers order confirmation or failure alert to subscribers | ~$0.50/1M publishes |
| DynamoDB | Stores final order record with status (CONFIRMED, OUT_OF_STOCK, PAYMENT_FAILED) | Free tier / ~$0.25/WCU |
| IAM | Step Functions execution role; per-Lambda execution roles | Free |
| CloudWatch Logs | Lambda logs + optional Step Functions execution logging | ~$0.50/GB ingested |

---

## Input / Output

### Input

| Field | Value | Notes |
|---|---|---|
| Trigger | `aws stepfunctions start-execution` or EventBridge | Submits order JSON as input |
| Payload format | JSON | `{"order_id": "ORD-007", "customer_id": "C-88", "sku": "WIDGET-XL", "qty": 2, "payment_token": "tok_visa_4242"}` |
| State machine ARN | `arn:aws:states:us-east-1:123456789012:stateMachine:OrderFulfillment` | Target for execution |
| Execution name | Optional string | Defaults to UUID; must be unique per state machine |

### Output

| Artifact | Location | Details |
|---|---|---|
| Execution ARN | Returned by `start-execution` | Use to query status with `describe-execution` |
| State history | Step Functions console / `get-execution-history` API | Each state: input, output, duration, status |
| DynamoDB order record | Table `orders`, PK = `order_id` | Final status: CONFIRMED, OUT_OF_STOCK, or PAYMENT_FAILED |
| SNS notification | Topic `order-notifications` | Success: order summary. Failure: reason + order_id |

---

## Architecture

```
  Client
    |
    | start-execution (order JSON input)
    v
+------------------------------------------+
|   Step Functions Standard Workflow        |
|   OrderFulfillment state machine          |
|                                           |
|  [ValidateOrder]                          |
|   Lambda: validate-order                  |
|   --> returns validated order object      |
|        |                                  |
|        v                                  |
|  [CheckInventory]                         |
|   Lambda: check-inventory                 |
|   --> returns {in_stock: true/false}      |
|        |                                  |
|        v                                  |
|  [Choice: InventoryCheck]                 |
|   in_stock == false --> [OutOfStock] --+  |
|   in_stock == true  --> [ProcessPayment]  |
|                              |            |
|            Catch: PaymentFailed           |
|            --> [PaymentFailed] --------+  |
|                              |         |  |
|                              v         |  |
|                    [SendNotification]  |  |
|                     Lambda: notify     |  |
|                     SNS success msg    |  |
|                              |         |  |
|                              v         v  |
|                           [End]  [ErrorNotify]
|                                  Lambda: notify
|                                  SNS failure msg
+------------------------------------------+
         |                    |
         v                    v
   +----------+       +------------------+
   | DynamoDB |       |  SNS Topic       |
   |  orders  |       | order-notifications|
   +----------+       +------------------+
```

---

## Quick Start

```cmd
REM 1. Create DynamoDB orders table
aws dynamodb create-table ^
  --table-name orders ^
  --attribute-definitions AttributeName=order_id,AttributeType=S ^
  --key-schema AttributeName=order_id,KeyType=HASH ^
  --billing-mode PAY_PER_REQUEST ^
  --region us-east-1

REM 2. Create SNS topic for notifications
aws sns create-topic --name order-notifications --region us-east-1

REM 3. Deploy all four Lambda functions (repeat for each)
aws lambda create-function ^
  --function-name validate-order ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/lambda-exec-role ^
  --handler validate_order.lambda_handler ^
  --zip-file fileb://validate_order.zip ^
  --timeout 10 --region us-east-1

aws lambda create-function ^
  --function-name check-inventory ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/lambda-exec-role ^
  --handler check_inventory.lambda_handler ^
  --zip-file fileb://check_inventory.zip ^
  --timeout 10 --region us-east-1

aws lambda create-function ^
  --function-name process-payment ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/lambda-exec-role ^
  --handler process_payment.lambda_handler ^
  --zip-file fileb://process_payment.zip ^
  --timeout 30 --region us-east-1

aws lambda create-function ^
  --function-name send-notification ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/lambda-exec-role ^
  --handler send_notification.lambda_handler ^
  --zip-file fileb://send_notification.zip ^
  --timeout 10 --region us-east-1

REM 4. Create Step Functions execution role
aws iam create-role ^
  --role-name stepfunctions-exec-role ^
  --assume-role-policy-document file://sfn-trust-policy.json

aws iam attach-role-policy ^
  --role-name stepfunctions-exec-role ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole

REM 5. Create the state machine from ASL definition file
aws stepfunctions create-state-machine ^
  --name OrderFulfillment ^
  --definition file://order-fulfillment.asl.json ^
  --role-arn arn:aws:iam::123456789012:role/stepfunctions-exec-role ^
  --type STANDARD ^
  --region us-east-1

REM 6. Run a test execution (happy path)
aws stepfunctions start-execution ^
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:OrderFulfillment ^
  --name test-run-001 ^
  --input "{\"order_id\":\"ORD-007\",\"customer_id\":\"C-88\",\"sku\":\"WIDGET-XL\",\"qty\":2,\"payment_token\":\"tok_visa_4242\"}"

REM 7. Check execution result
aws stepfunctions describe-execution ^
  --execution-arn arn:aws:states:us-east-1:123456789012:execution:OrderFulfillment:test-run-001
```

---

## Data Flow

1. A client calls `stepfunctions:StartExecution` with the order JSON; Step Functions returns an execution ARN immediately.
2. The `ValidateOrder` state invokes the `validate-order` Lambda synchronously; if required fields are missing, Lambda raises a `ValidationException` which bubbles up as an execution failure.
3. Output from `ValidateOrder` flows into `CheckInventory` via `ResultPath: "$.validation"`. The `check-inventory` Lambda queries DynamoDB and appends `{"in_stock": true}` or `{"in_stock": false}` to the state data.
4. The `InventoryCheck` Choice state evaluates `$.in_stock`. If `false`, execution transitions to `OutOfStock`, writes `status=OUT_OF_STOCK` to DynamoDB, and calls `send-notification` with a stock-out message before ending.
5. If `in_stock` is `true`, the `ProcessPayment` state invokes `process-payment`. A Catch block on `PaymentFailedException` redirects to the `PaymentFailed` error branch, which writes `status=PAYMENT_FAILED` and sends an SNS failure alert.
6. On successful payment, `SendNotification` invokes `send-notification`, which publishes an order confirmation to the `order-notifications` SNS topic and writes `status=CONFIRMED` to DynamoDB.
7. The workflow reaches the `End` state; the full execution history — input/output per state, timestamps, durations — is stored for 90 days and queryable via `get-execution-history`.

---

## Project Files

| File | Description |
|---|---|
| `order-fulfillment.asl.json` | Amazon States Language definition — all states, choices, catch blocks |
| `validate_order.py` | Lambda 1 — checks required fields; raises `ValidationException` on bad input |
| `check_inventory.py` | Lambda 2 — queries DynamoDB stock table; returns `in_stock` boolean |
| `process_payment.py` | Lambda 3 — simulates payment charge; raises `PaymentFailedException` on decline |
| `send_notification.py` | Lambda 4 — publishes SNS message for success or failure path |
| `sfn-trust-policy.json` | IAM trust policy allowing Step Functions service to assume execution role |
| `README.md` | This file |

---

## Lessons Learned

- **Standard vs Express workflows** — Standard stores full execution history for 90 days and supports exactly-once execution semantics, making it auditable. Express is cheaper and handles thousands of executions per second but has no guaranteed history. For order fulfillment — where auditability matters — Standard is the right choice.
- **State transition cost adds up at scale** — each state transition costs $0.000025. The happy path (5 transitions) costs $0.000125 per order. At 1M orders/month that is $125; design the state machine to minimize unnecessary pass-through states.
- **`Catch` on Task state is not a try/except** — `Catch` matches specific error names like `Lambda.AWSLambdaException` or a custom error string raised by the function. Use `States.ALL` as a fallback to catch any unhandled error and avoid silent stuck executions.
- **`ResultPath` and `OutputPath` control data flow between states** — without `ResultPath`, each Lambda's return value replaces the entire state input. Setting `ResultPath: "$.payment"` merges the Lambda output into the existing data under a named key, preserving upstream fields.
- **`WaitForTaskToken` enables human-in-the-loop** — a Wait state with `HeartbeatSeconds` pauses the workflow indefinitely until an external system calls `SendTaskSuccess` with the token. This is the clean pattern for approval workflows without polling.
- **Console execution timeline is the best debugging tool** — unlike individual Lambda logs, the Step Functions console shows each state's exact input, output, error, and duration in a visual graph. Diagnosing why a Choice branched incorrectly takes seconds instead of correlating log entries across four CloudWatch log groups.
- **ASL JSON is declarative but strict** — `InputPath`, `OutputPath`, `ResultPath`, and `Parameters` each filter at different stages of state processing and their interaction is non-obvious. Test each state in isolation using `TestState` API (available in console) before wiring the full machine.
