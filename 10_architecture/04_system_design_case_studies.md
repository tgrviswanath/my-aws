# AWS System Design Case Studies

## Case Study 1: Design Netflix-like Video Streaming on AWS

```
Requirements:
  - 200M users, 100M daily active
  - Stream 4K video globally
  - Upload and transcode videos
  - < 2 second start time

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │                    Upload Path                           │
  │  Creator → S3 (raw) → MediaConvert → S3 (HLS segments) │
  └─────────────────────────────────────────────────────────┘
                              ↓
  ┌─────────────────────────────────────────────────────────┐
  │                   Delivery Path                          │
  │  Viewer → CloudFront (400+ PoPs) → S3 (HLS segments)   │
  │  Adaptive bitrate: 240p/480p/720p/1080p/4K              │
  └─────────────────────────────────────────────────────────┘
                              ↓
  ┌─────────────────────────────────────────────────────────┐
  │                  Metadata & Auth                         │
  │  API Gateway → Lambda → DynamoDB (video metadata)       │
  │  Cognito (auth) → CloudFront signed URLs                │
  └─────────────────────────────────────────────────────────┘

Key AWS services:
  S3:           Video storage (raw + transcoded)
  MediaConvert: Video transcoding (HLS, DASH, MP4)
  CloudFront:   Global CDN (< 50ms to 99% of users)
  DynamoDB:     Video metadata (title, description, thumbnails)
  ElastiCache:  User session, watch history cache
  Kinesis:      Real-time view count, analytics
  Lambda:       Trigger transcoding on upload
```

---

## Case Study 2: Design Twitter/X on AWS

```
Scale:
  500M tweets/day = 5,787 tweets/sec
  Read:write ratio = 100:1 (read-heavy)
  Timeline generation is the hard problem

Architecture:
  Tweet Creation:
    POST /tweet → API Gateway → Lambda → SQS
                                           ↓
                                    Fan-out Service
                                    (write tweet to all followers' timelines)
                                           ↓
                                    ElastiCache (timeline cache)
                                    DynamoDB (persistent storage)

  Timeline Read:
    GET /timeline → API Gateway → Lambda → ElastiCache (cache hit: 95%)
                                                ↓ (cache miss)
                                           DynamoDB → rebuild cache

  Fan-out strategies:
    Push (fan-out on write):  Write to all followers' caches on tweet
      Pros: Fast reads
      Cons: Expensive for users with 10M followers (Lady Gaga problem)

    Pull (fan-out on read):   Merge followed users' tweets on read
      Pros: No write amplification
      Cons: Slow reads for users following many people

    Hybrid: Push for normal users, pull for celebrities (> 1M followers)

Key AWS services:
  DynamoDB:     Tweets, user data, follow graph
  ElastiCache:  Timeline cache (Redis sorted sets by timestamp)
  SQS:          Fan-out queue (decouple tweet creation from delivery)
  Lambda:       Fan-out workers, timeline generation
  S3:           Media storage (images, videos)
  CloudFront:   Media CDN
  Kinesis:      Real-time trending topics
```

---

## Case Study 3: Design Uber/Lyft on AWS

```
Core challenges:
  1. Real-time location tracking (drivers update every 4 seconds)
  2. Matching riders to nearby drivers (geospatial search)
  3. Dynamic pricing (surge pricing)
  4. Trip management (state machine)

Architecture:
  Location Service:
    Driver App → API Gateway → Kinesis → Location Processor (Lambda)
                                                ↓
                                         ElastiCache (Redis GEO)
                                         DynamoDB (location history)

  Matching Service:
    Rider requests ride → API Gateway → Matching Lambda
                                              ↓
                                    Redis GEORADIUS (find nearby drivers)
                                    → Rank by ETA, rating, car type
                                    → Send offer to best driver

  Trip State Machine:
    REQUESTED → ACCEPTED → DRIVER_ARRIVING → IN_PROGRESS → COMPLETED
    Each state transition → DynamoDB update + SNS notification

  Surge Pricing:
    Kinesis → Lambda → analyze supply/demand ratio
    → Update pricing in ElastiCache
    → Apply to new ride requests

Key AWS services:
  ElastiCache (Redis GEO): Real-time driver locations
  DynamoDB:                Trip data, user profiles
  Kinesis:                 Location stream processing
  SNS:                     Push notifications (driver/rider)
  SQS:                     Trip request queue
  Lambda:                  Matching, pricing, notifications
  API Gateway:             WebSocket for real-time updates
```

---

## Case Study 4: Design a Global E-Commerce Platform

```
Requirements:
  - 10M products, 100M users
  - Black Friday: 10x normal traffic
  - < 100ms product page load
  - Inventory accuracy (no overselling)

Architecture:
  Product Catalog (read-heavy):
    CloudFront → API Gateway → Lambda → ElastiCache
                                              ↓ (miss)
                                         DynamoDB (product data)
    Cache TTL: 1 hour (products rarely change)

  Inventory (write-heavy, consistency critical):
    Add to cart → SQS → Inventory Lambda → DynamoDB (conditional write)
    DynamoDB condition: quantity >= requested_quantity
    If fails: notify user "out of stock"

  Order Processing:
    Checkout → Step Functions (orchestrate):
      1. Reserve inventory (DynamoDB conditional update)
      2. Process payment (Stripe API)
      3. Confirm order (DynamoDB)
      4. Send confirmation (SES)
      5. Trigger fulfillment (SQS → warehouse)

  Black Friday scaling:
    Auto Scaling: Lambda scales automatically
    DynamoDB: On-demand capacity (no pre-provisioning)
    ElastiCache: Read replicas for cache
    SQS: Buffer traffic spikes (queue absorbs bursts)

Key AWS services:
  DynamoDB:     Products, inventory, orders (on-demand capacity)
  ElastiCache:  Product cache, session store
  SQS:          Order queue, inventory updates
  Step Functions: Order workflow orchestration
  Lambda:       All compute (auto-scales)
  CloudFront:   Product images, static assets
  SES:          Order confirmation emails
```

---

## System Design Interview Framework for AWS

```
1. CLARIFY (5 min)
   - Scale: users, requests/sec, data volume
   - Latency requirements: real-time vs batch
   - Consistency: strong vs eventual
   - Availability: 99.9% vs 99.99%

2. ESTIMATE (5 min)
   - QPS: daily_active_users × requests_per_user / 86400
   - Storage: objects/day × object_size × retention_days
   - Bandwidth: QPS × response_size

3. HIGH-LEVEL DESIGN (10 min)
   - Draw the architecture
   - Identify main components
   - Choose AWS services

4. DEEP DIVE (20 min)
   - Database schema
   - API design
   - Bottlenecks and solutions
   - Failure scenarios

5. TRADE-OFFS (5 min)
   - What you chose and why
   - What you'd do differently at 10x scale
   - Cost considerations
```

---

## Interview Q&A

### Q1: How do you design for 99.99% availability on AWS?
1. **Multi-AZ**: Deploy all stateful services (RDS, ElastiCache) across 3 AZs
2. **Multi-region**: Route 53 failover routing for critical services
3. **Auto Scaling**: Replace failed instances automatically
4. **Circuit breakers**: Prevent cascade failures
5. **Health checks**: ALB + Route 53 health checks
6. **Chaos engineering**: AWS FIS to test failure scenarios
99.99% = 52 minutes downtime/year. Requires: no single points of failure, automated recovery, tested runbooks.

### Q2: When would you use SQS vs SNS vs EventBridge?
**SQS**: Work queue — one consumer per message, retry logic, DLQ. Use for: task distribution, decoupling services.
**SNS**: Fan-out — one message to many subscribers simultaneously. Use for: notifications, broadcasting events.
**EventBridge**: Event routing with filtering and transformation. Use for: complex event routing, SaaS integrations, scheduled events.
Common pattern: SNS → multiple SQS queues (fan-out to multiple consumers, each with their own queue and retry logic).

### Q3: How do you handle a DynamoDB hot partition?
Hot partition = one partition key receiving disproportionate traffic. Solutions: (1) Add random suffix to key (write sharding): `user_id + "_" + random(0,9)`, (2) Use DAX for read-heavy hot keys, (3) Increase RCU/WCU for the table, (4) Redesign partition key to distribute load, (5) Use DynamoDB Adaptive Capacity (automatic, but has limits).
