# Step Functions — Real-World Use Cases

## Use Case 1: Order Processing Workflow

**Business Problem**: Order processing involves 6 steps that must run in sequence, with retries, parallel execution, and human approval for large orders.

```json
{
  "Comment": "E-commerce order processing workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:validate-order",
      "Retry": [{
        "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2
      }],
      "Catch": [{
        "ErrorEquals": ["ValidationError"],
        "Next": "OrderFailed",
        "ResultPath": "$.error"
      }],
      "Next": "CheckOrderValue"
    },

    "CheckOrderValue": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.total",
          "NumericGreaterThan": 10000,
          "Next": "RequireManagerApproval"
        }
      ],
      "Default": "ProcessPayment"
    },

    "RequireManagerApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": {
        "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789/manager-approvals",
        "MessageBody": {
          "orderId.$": "$.orderId",
          "total.$": "$.total",
          "taskToken.$": "$$.Task.Token"
        }
      },
      "HeartbeatSeconds": 86400,
      "Next": "ProcessPayment"
    },

    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:process-payment",
      "Retry": [{
        "ErrorEquals": ["PaymentRetryableError"],
        "IntervalSeconds": 5,
        "MaxAttempts": 3
      }],
      "Catch": [{
        "ErrorEquals": ["PaymentDeclined"],
        "Next": "NotifyPaymentFailed"
      }],
      "Next": "ParallelFulfillment"
    },

    "ParallelFulfillment": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "UpdateInventory",
          "States": {
            "UpdateInventory": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789:function:update-inventory",
              "End": true
            }
          }
        },
        {
          "StartAt": "SendConfirmationEmail",
          "States": {
            "SendConfirmationEmail": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789:function:send-email",
              "End": true
            }
          }
        },
        {
          "StartAt": "NotifyWarehouse",
          "States": {
            "NotifyWarehouse": {
              "Type": "Task",
              "Resource": "arn:aws:states:::sqs:sendMessage",
              "Parameters": {
                "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789/warehouse",
                "MessageBody.$": "$"
              },
              "End": true
            }
          }
        }
      ],
      "Next": "OrderComplete"
    },

    "OrderComplete": {
      "Type": "Succeed"
    },

    "OrderFailed": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:handle-order-failure",
      "Next": "Fail"
    },

    "NotifyPaymentFailed": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:notify-payment-failed",
      "Next": "Fail"
    },

    "Fail": {
      "Type": "Fail",
      "Error": "OrderProcessingFailed"
    }
  }
}
```

```bash
# Deploy state machine
aws stepfunctions create-state-machine \
  --name "order-processing" \
  --definition file://order-workflow.json \
  --role-arn arn:aws:iam::123456789:role/StepFunctionsRole \
  --type STANDARD \
  --logging-configuration '{
    "level": "ALL",
    "includeExecutionData": true,
    "destinations": [{
      "cloudWatchLogsLogGroup": {
        "logGroupArn": "arn:aws:logs:us-east-1:123456789:log-group:/aws/states/order-processing"
      }
    }]
  }'

# Start execution
EXEC_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789:stateMachine:order-processing \
  --input '{
    "orderId": "ord-123",
    "userId": "usr-456",
    "items": [{"productId": "p1", "qty": 2}],
    "total": 59.98
  }' \
  --query 'executionArn' --output text)

# Monitor execution
aws stepfunctions describe-execution --execution-arn $EXEC_ARN
aws stepfunctions get-execution-history --execution-arn $EXEC_ARN
```

**What you learn**: State machine design, Choice states, Parallel branches, waitForTaskToken for human approval, retry/catch.

---

## Use Case 2: ETL Pipeline Orchestration

**Business Problem**: Nightly ETL: extract from 5 sources in parallel, transform, validate, load to warehouse, notify team.

```json
{
  "Comment": "Nightly ETL pipeline",
  "StartAt": "ExtractAllSources",
  "States": {
    "ExtractAllSources": {
      "Type": "Parallel",
      "Branches": [
        {"StartAt": "ExtractCRM", "States": {"ExtractCRM": {"Type": "Task", "Resource": "arn:aws:lambda:::function:extract-crm", "End": true}}},
        {"StartAt": "ExtractERP", "States": {"ExtractERP": {"Type": "Task", "Resource": "arn:aws:lambda:::function:extract-erp", "End": true}}},
        {"StartAt": "ExtractAnalytics", "States": {"ExtractAnalytics": {"Type": "Task", "Resource": "arn:aws:lambda:::function:extract-analytics", "End": true}}}
      ],
      "Next": "ValidateExtractedData"
    },

    "ValidateExtractedData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:::function:validate-data",
      "Next": "QualityCheck"
    },

    "QualityCheck": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.qualityScore",
        "NumericLessThan": 0.95,
        "Next": "AlertDataQualityIssue"
      }],
      "Default": "TransformData"
    },

    "TransformData": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {
        "JobName": "nightly-transform",
        "Arguments": {
          "--execution-date.$": "$.executionDate"
        }
      },
      "Next": "LoadToWarehouse"
    },

    "LoadToWarehouse": {
      "Type": "Task",
      "Resource": "arn:aws:states:::redshift-data:executeStatement.sync",
      "Parameters": {
        "ClusterIdentifier": "prod-redshift",
        "Database": "analytics",
        "Sql.$": "States.Format('COPY transactions FROM s3://bucket/processed/{}/  IAM_ROLE arn:aws:iam::123456789:role/RedshiftRole FORMAT AS PARQUET', $.executionDate)"
      },
      "Next": "NotifySuccess"
    },

    "NotifySuccess": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:123456789:data-team",
        "Message.$": "States.Format('ETL complete for {}. Rows loaded: {}', $.executionDate, $.rowsLoaded)"
      },
      "End": true
    },

    "AlertDataQualityIssue": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:123456789:data-team",
        "Message.$": "States.Format('Data quality issue: score={}. Pipeline halted.', $.qualityScore)"
      },
      "Next": "Fail"
    },

    "Fail": {"Type": "Fail"}
  }
}
```

**What you learn**: Parallel extraction, Glue integration, Redshift integration, SNS notifications from state machine.

---

## Use Case 3: Map State for Bulk Processing

**Business Problem**: Process 10,000 images — run the same Lambda for each image in parallel (up to 40 concurrent).

```json
{
  "StartAt": "GetImageList",
  "States": {
    "GetImageList": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:::function:list-images",
      "Next": "ProcessAllImages"
    },

    "ProcessAllImages": {
      "Type": "Map",
      "ItemsPath": "$.images",
      "MaxConcurrency": 40,
      "Iterator": {
        "StartAt": "ProcessSingleImage",
        "States": {
          "ProcessSingleImage": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:::function:process-image",
            "Retry": [{
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 2
            }],
            "End": true
          }
        }
      },
      "Next": "GenerateReport"
    },

    "GenerateReport": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:::function:generate-report",
      "End": true
    }
  }
}
```

**What you learn**: Map state for parallel iteration, MaxConcurrency to control parallelism, retry within Map.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No retry on Lambda tasks | Transient failures cause pipeline failure | Add retry with exponential backoff |
| Not using Express workflows for high-volume | Standard workflows cost $0.025/1000 state transitions | Use Express for > 1M executions/month |
| Passing large data between states | State size limit 256KB | Store large data in S3, pass S3 key |
| No logging enabled | Can't debug failed executions | Enable CloudWatch logging |
| Not handling partial failures in Parallel | One branch failure fails all | Add Catch on Parallel state |
| Hardcoding ARNs in state machine | Not portable across environments | Use CloudFormation parameters or SSM |
