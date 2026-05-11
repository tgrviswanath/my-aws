# Architecture — Project 4.6 Step Functions Workflow

## State Machine Diagram

```
[START]
   │
   ▼
┌──────────┐   ValueError    ┌──────────────────┐
│ Validate │ ──────────────► │ ValidationFailed │ [FAIL]
└────┬─────┘                 └──────────────────┘
     │ success
     ▼
┌─────────────┐
│ ExtractText │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│              ParallelAnalysis                 │
│                                               │
│  ┌──────────────┐    ┌───────────────────┐   │
│  │   Classify   │    │  CheckCompliance  │   │
│  └──────────────┘    └───────────────────┘   │
│  (runs simultaneously)                        │
└──────────────────────┬───────────────────────┘
                       │ both branches complete
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

## State Types Used

| State | Type | Purpose |
|-------|------|---------|
| Validate | Task | Invoke Lambda |
| ExtractText | Task | Invoke Lambda |
| ParallelAnalysis | Parallel | Run 2 branches simultaneously |
| StoreResults | Task | Invoke Lambda |
| Notify | Task | Invoke Lambda |
| Success | Succeed | Terminal success state |
| ValidationFailed | Fail | Terminal failure state |

## Error Handling Pattern

```
Task State
  Retry:
    - Lambda.ServiceException → retry 3x with exponential backoff
  Catch:
    - ValueError → go to ValidationFailed state
    - States.ALL  → go to ProcessingFailed state (catch-all)
```

## Standard vs Express Workflows

| Feature | Standard | Express |
|---------|----------|---------|
| Duration | Up to 1 year | Up to 5 minutes |
| Execution model | At-least-once | At-least-once |
| Price | $0.025/1K transitions | $1/million executions |
| Use case | Long-running, human approval | High-volume, short workflows |
| Audit history | 90 days | CloudWatch only |
