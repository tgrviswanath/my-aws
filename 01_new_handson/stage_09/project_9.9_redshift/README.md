# Project 9.9 — Redshift Data Warehouse

## What This Does
Deploys Amazon Redshift Serverless as an OLAP data warehouse. Loads processed data from S3, runs complex analytical queries, and connects to BI tools.

## Data Lake vs Data Warehouse
| Feature | Data Lake (S3+Athena) | Data Warehouse (Redshift) |
|---------|----------------------|--------------------------|
| Data format | Any (raw + processed) | Structured only |
| Query speed | Seconds to minutes | Sub-second to seconds |
| Cost model | Pay per query | Pay per compute |
| Schema | Schema-on-read | Schema-on-write |
| Use case | Exploration, ML | Dashboards, reports |
| Best for | Data scientists | Business analysts |

## Architecture
```
S3 (processed Parquet)
  → Redshift COPY command
    → Redshift tables (columnar storage)
      → SQL queries (sub-second)
        → BI tools (QuickSight, Tableau, Power BI)
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output redshift_endpoint
```

## Lessons Learned
- Redshift Serverless: no cluster to manage, pay per RPU-second — best for learning
- COPY command: bulk load from S3 — much faster than INSERT
- Distribution keys: choose columns that are frequently joined
- Sort keys: choose columns that are frequently filtered
- Vacuum and Analyze: run after large loads to reclaim space and update statistics
- Redshift Spectrum: query S3 data directly from Redshift without loading

## Code

### `code/redshift_operations.py` — Redshift data warehouse operations

```bash
pip install psycopg2-binary boto3

# Set connection environment variables
export REDSHIFT_HOST=my-cluster.abc123.us-east-1.redshift.amazonaws.com
export REDSHIFT_USER=admin
export REDSHIFT_PASS=yourpassword
export REDSHIFT_DB=analytics

# Create tables (fact + dimension)
python code/redshift_operations.py setup

# Load data from S3 Parquet files
python code/redshift_operations.py load --bucket my-data-lake --prefix processed/orders/

# Run analytical queries
python code/redshift_operations.py query

# Print full analytics report
python code/redshift_operations.py report
```

Queries included:
- Daily revenue trend (last 30 days)
- Top 10 products by revenue
- Customer lifetime value (LTV)
- Order status distribution
