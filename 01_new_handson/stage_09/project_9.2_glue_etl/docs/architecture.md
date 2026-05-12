# Architecture — Project 9.2 Glue ETL Pipeline

## Pipeline Flow

```
S3 raw/ (CSV/JSON)
    │
    │ Glue Job (PySpark, 2 workers G.1X)
    ▼
┌──────────────────────────────────────────────┐
│              Glue ETL Job                     │
│                                               │
│  Extract:   Read CSV from S3 raw/             │
│  Transform: Clean nulls, fix types, dedup     │
│             Add year/month/day columns        │
│             Aggregate daily summaries         │
│  Load:      Write Parquet to S3 processed/   │
└──────────────────────────────────────────────┘
    │
    ▼
S3 processed/ (Parquet, partitioned by year/month)
    │
    ▼
Athena queries (fast, cheap — columnar format)
```

## Glue Job Bookmark

```
Without bookmark:
  Run 1: processes files A, B, C
  Run 2: processes files A, B, C, D, E  ← reprocesses A, B, C!

With bookmark enabled:
  Run 1: processes files A, B, C → bookmark saved
  Run 2: processes only D, E     ← only new files
```

## Worker Types

| Type | vCPU | Memory | Use Case |
|------|------|--------|---------|
| G.1X | 4 | 16 GB | Standard ETL |
| G.2X | 8 | 32 GB | Memory-intensive |
| G.4X | 16 | 64 GB | Large datasets |
| G.8X | 32 | 128 GB | Very large datasets |
