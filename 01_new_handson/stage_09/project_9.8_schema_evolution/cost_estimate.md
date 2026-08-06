# Cost Estimate — Project 9.8 Schema Evolution & Partitioning

> Pricing based on us-east-1 as of 2024.

---

## Free Tier Coverage

| Service | Free Tier | This Project Usage | Charged? |
|---------|-----------|-------------------|---------|
| **Glue Schema Registry** | ✅ 10M schema versions/month | 2 versions | **$0** |
| **Glue Data Catalog** | ✅ 1M objects/month free | 1 DB + 1 table | **$0** |
| **S3** | ✅ 5 GB/month | ~1 MB Parquet files | **$0** |
| **Athena** | ❌ No free tier | ~1 MB scanned | **~$0.000005** |

**Total for this project: ~$0.00–$0.01**

---

## Glue Schema Registry Pricing

```
Free tier:   First 10,000,000 schema versions/month = $0
After:       $0.025 per 100,000 schema versions

This project:   2 versions → $0.00 always

At production scale (1,000 schemas × 100 versions/yr = 100,000 versions):
  100,000 / 100,000 × $0.025 = $0.025/month  → still nearly free
```

---

## Athena Partition Pruning — Cost Savings

```
Without partitioning (full table scan):
  1 TB table, query scans all = 1 TB × $5/TB = $5.00 per query
  50 queries/day = $250/day = $7,500/month

With year/month/day partitioning (99% savings):
  1 TB table, query scans 1 day = 1/365 TB × $5/TB = $0.014 per query
  50 queries/day = $0.68/day = $20/month

Savings: $7,500/month → $20/month = 99.7% cost reduction
This is why partitioning is not optional — it's critical at scale
```

---

## Learning Session Estimate

| Activity | Cost |
|----------|------|
| Run Python demo (write/read Parquet) | $0 (no Athena) |
| Create Glue registry + schema v1 + v2 | $0 (free tier) |
| Create Glue table with partition projection | $0 (free tier) |
| Athena query comparisons (~10 queries, 1 MB each) | ~$0.00005 |
| S3 storage (2 small Parquet files) | ~$0.00001 |
| **Total session cost** | **< $0.01** |

---

## Cleanup to Zero Cost

```powershell
# Delete all resources → $0.00/month ongoing
aws glue delete-schema --schema-id "RegistryName=handson-registry,SchemaName=orders-schema"
aws glue delete-registry --registry-id "RegistryName=handson-registry"
aws glue delete-table --database-name handson_schema_demo --name orders_partitioned
aws glue delete-database --name handson_schema_demo
aws s3 rm s3://BUCKET/schema-demo/ --recursive
```
