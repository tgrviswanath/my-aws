# Steps — Project 9.9 Redshift Data Warehouse

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="admin_password=Admin@1234!" \
  -var="vpc_id=vpc-xxxxxxxxxx" \
  -var='private_subnet_ids=["subnet-xxx","subnet-yyy"]'

ENDPOINT=$(terraform output -raw redshift_endpoint)
IAM_ROLE=$(terraform output -raw iam_role_arn)
```

---

## Phase 2 — Connect to Redshift

```bash
# Install psql client
sudo apt-get install -y postgresql-client

# Connect
psql -h $ENDPOINT -p 5439 -U admin -d analytics
```

---

## Phase 3 — Create Tables and Load Data

```sql
-- Create orders fact table
CREATE TABLE fct_orders (
    order_id     VARCHAR(50)    NOT NULL,
    customer_id  VARCHAR(50)    NOT NULL,
    product      VARCHAR(100),
    amount       DECIMAL(10,2)  NOT NULL,
    order_date   DATE           NOT NULL,
    order_year   SMALLINT,
    order_month  SMALLINT
)
DISTSTYLE KEY
DISTKEY (customer_id)    -- distribute by customer for join performance
SORTKEY (order_date);    -- sort by date for range queries

-- Load from S3 using COPY (bulk load — much faster than INSERT)
COPY fct_orders
FROM 's3://handson-data-lake-ACCOUNTID/processed/orders/'
IAM_ROLE 'arn:aws:iam::ACCOUNTID:role/handson-redshift-role'
FORMAT AS PARQUET;

-- Verify load
SELECT COUNT(*) FROM fct_orders;
SELECT * FROM fct_orders LIMIT 5;
```

---

## Phase 4 — Run Analytical Queries

```sql
-- Revenue by product (fast — columnar storage)
SELECT
    product,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_order_value
FROM fct_orders
GROUP BY product
ORDER BY total_revenue DESC;

-- Monthly revenue trend
SELECT
    order_year,
    order_month,
    SUM(amount) AS monthly_revenue,
    COUNT(*) AS order_count
FROM fct_orders
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- Top customers by lifetime value
SELECT
    customer_id,
    COUNT(*) AS total_orders,
    SUM(amount) AS lifetime_value,
    MIN(order_date) AS first_order,
    MAX(order_date) AS last_order
FROM fct_orders
GROUP BY customer_id
ORDER BY lifetime_value DESC
LIMIT 10;
```

---

## Phase 5 — Redshift Spectrum (Query S3 Directly)

```sql
-- Create external schema pointing to Glue catalog
CREATE EXTERNAL SCHEMA spectrum_schema
FROM DATA CATALOG
DATABASE 'handson_data_lake'
IAM_ROLE 'arn:aws:iam::ACCOUNTID:role/handson-redshift-role'
CREATE EXTERNAL DATABASE IF NOT EXISTS;

-- Query S3 data directly without loading
SELECT * FROM spectrum_schema.orders LIMIT 10;

-- Join Redshift table with S3 data
SELECT r.customer_id, r.lifetime_value, s.product
FROM fct_orders_summary r
JOIN spectrum_schema.orders s ON r.customer_id = s.customer_id
LIMIT 10;
```

---

## Screenshots to Take
- [ ] Redshift Serverless workgroup created
- [ ] COPY command loading data from S3
- [ ] Analytical query results (revenue by product)
- [ ] Query execution time (sub-second for aggregations)
- [ ] Redshift Spectrum querying S3 directly
