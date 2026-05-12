# Architecture — Project 4.3 URL Shortener

## Request Flow

```
POST /shorten {"url": "https://very-long-url.com/..."}
    → Lambda generates 6-char code (e.g. "abc123")
    → Stores in DynamoDB: {code: "abc123", original_url: "...", ttl: +30days}
    → Returns: {"short_url": "https://api.../abc123"}

GET /abc123
    → Lambda looks up code in DynamoDB
    → Increments click counter (atomic ADD)
    → Returns 302 redirect to original URL

GET /stats/abc123
    → Lambda returns: {code, original_url, clicks, created_at}
```

## DynamoDB Design

```
Table: handson-url-shortener-urls
PK: code (String)  ← "abc123"

Item:
{
  "code":         "abc123",
  "original_url": "https://very-long-url.com/...",
  "created_at":   "2024-01-15T10:00:00Z",
  "clicks":       42,
  "ttl":          1737000000   ← Unix timestamp, auto-deleted by DynamoDB
}
```

## Collision Avoidance

```
Generate random 6-char code
    │
    ├── DynamoDB PutItem with ConditionExpression: attribute_not_exists(code)
    │     ├── Success → code is unique, item stored
    │     └── ConditionalCheckFailedException → collision, retry with new code
    │
    └── Max 5 retries → return error
```
