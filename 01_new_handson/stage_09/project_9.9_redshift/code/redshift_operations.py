"""
redshift_operations.py — Redshift data warehouse operations.

Usage:
    python redshift_operations.py setup   — Create tables (fact + dimension)
    python redshift_operations.py load    — COPY data from S3 Parquet files
    python redshift_operations.py query   — Run analytical queries
    python redshift_operations.py report  — Print formatted query results

Environment variables (required):
    REDSHIFT_HOST      — Redshift Serverless endpoint or cluster endpoint
    REDSHIFT_PORT      — Port (default: 5439)
    REDSHIFT_DB        — Database name (default: dev)
    REDSHIFT_USER      — Database user
    REDSHIFT_PASSWORD  — Database password
    S3_BUCKET          — S3 bucket containing Parquet data files
    IAM_ROLE_ARN       — IAM role ARN with S3 read access (for COPY command)

Prerequisites:
    pip install psycopg2-binary boto3
"""

import argparse
import os
import sys
import textwrap
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras


# ── Connection configuration ──────────────────────────────────────────────────

def get_connection_config() -> dict:
    """
    Build Redshift connection config from environment variables.

    Returns:
        Dict with host, port, dbname, user, password

    Raises:
        SystemExit: If required environment variables are missing
    """
    required = ["REDSHIFT_HOST", "REDSHIFT_USER", "REDSHIFT_PASSWORD"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"  ✗ Missing required environment variables: {', '.join(missing)}")
        print("  Set them with: export REDSHIFT_HOST=... REDSHIFT_USER=... REDSHIFT_PASSWORD=...")
        sys.exit(1)

    return {
        "host":     os.environ["REDSHIFT_HOST"],
        "port":     int(os.environ.get("REDSHIFT_PORT", "5439")),
        "dbname":   os.environ.get("REDSHIFT_DB", "dev"),
        "user":     os.environ["REDSHIFT_USER"],
        "password": os.environ["REDSHIFT_PASSWORD"],
        "connect_timeout": 30,
        "sslmode": "require",  # Always use SSL for Redshift connections
    }


@contextmanager
def get_connection():
    """
    Context manager that provides a psycopg2 connection to Redshift.

    Automatically commits on success and rolls back on exception.
    Always closes the connection when done.

    Yields:
        psycopg2 connection object
    """
    config = get_connection_config()
    conn = psycopg2.connect(**config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_sql(conn, sql: str, params=None, fetch: bool = False) -> list[dict] | None:
    """
    Execute a SQL statement and optionally return results as a list of dicts.

    Args:
        conn:   psycopg2 connection
        sql:    SQL statement to execute
        params: Optional query parameters (for parameterized queries)
        fetch:  If True, return query results as list of dicts

    Returns:
        List of row dicts if fetch=True, else None
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetch:
            return [dict(row) for row in cur.fetchall()]
    return None


# ── Setup: Create tables ──────────────────────────────────────────────────────

ORDERS_FACT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS analytics.fact_orders (
    order_id        VARCHAR(50)     NOT NULL ENCODE zstd,
    customer_id     VARCHAR(50)     NOT NULL ENCODE zstd,
    order_date      DATE            NOT NULL ENCODE az64,
    product_id      VARCHAR(50)     NOT NULL ENCODE zstd,
    quantity        INTEGER         NOT NULL ENCODE az64,
    unit_price      DECIMAL(10, 2)  NOT NULL ENCODE az64,
    total_amount    DECIMAL(12, 2)  NOT NULL ENCODE az64,
    status          VARCHAR(20)     NOT NULL ENCODE zstd,
    region          VARCHAR(50)              ENCODE zstd,
    loaded_at       TIMESTAMP       DEFAULT GETDATE() ENCODE az64,
    PRIMARY KEY (order_id)
)
DISTSTYLE KEY
DISTKEY (customer_id)          -- Distribute by customer for customer-centric queries
SORTKEY (order_date, region);  -- Sort by date for time-series queries
"""

DATE_DIMENSION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key        INTEGER         NOT NULL,   -- YYYYMMDD integer key
    full_date       DATE            NOT NULL,
    year            SMALLINT        NOT NULL,
    quarter         SMALLINT        NOT NULL,
    month           SMALLINT        NOT NULL,
    month_name      VARCHAR(10)     NOT NULL,
    week_of_year    SMALLINT        NOT NULL,
    day_of_month    SMALLINT        NOT NULL,
    day_of_week     SMALLINT        NOT NULL,   -- 0=Sunday, 6=Saturday
    day_name        VARCHAR(10)     NOT NULL,
    is_weekend      BOOLEAN         NOT NULL,
    is_holiday      BOOLEAN         DEFAULT FALSE,
    PRIMARY KEY (date_key)
)
DISTSTYLE ALL    -- Small dimension table — replicate to all nodes for fast joins
SORTKEY (full_date);
"""

SCHEMA_DDL = "CREATE SCHEMA IF NOT EXISTS analytics;"


def setup_tables() -> None:
    """
    Create the analytics schema, orders fact table, and date dimension table.

    Uses IF NOT EXISTS so it's safe to run multiple times (idempotent).
    """
    print("\n=== Setup: Creating Tables ===\n")

    with get_connection() as conn:
        # Create schema
        print("  Creating schema: analytics")
        execute_sql(conn, SCHEMA_DDL)
        print("  ✓ Schema ready")

        # Create fact table
        print("  Creating table: analytics.fact_orders")
        execute_sql(conn, ORDERS_FACT_TABLE_DDL)
        print("  ✓ fact_orders ready")

        # Create dimension table
        print("  Creating table: analytics.dim_date")
        execute_sql(conn, DATE_DIMENSION_TABLE_DDL)
        print("  ✓ dim_date ready")

        # Populate dim_date with dates from 2020-01-01 to 2030-12-31
        print("  Populating dim_date (2020–2030)...")
        populate_date_dimension(conn)
        print("  ✓ dim_date populated")

    print("\n  ✓ Setup complete")


def populate_date_dimension(conn) -> None:
    """
    Populate the date dimension table using a Redshift SQL generator.

    Uses a recursive CTE to generate all dates in the range without
    needing to insert rows one by one from Python.

    Args:
        conn: psycopg2 connection
    """
    populate_sql = """
    INSERT INTO analytics.dim_date
    SELECT
        TO_NUMBER(TO_CHAR(d, 'YYYYMMDD'), '99999999')::INTEGER AS date_key,
        d::DATE                                                  AS full_date,
        EXTRACT(YEAR    FROM d)::SMALLINT                        AS year,
        EXTRACT(QUARTER FROM d)::SMALLINT                        AS quarter,
        EXTRACT(MONTH   FROM d)::SMALLINT                        AS month,
        TO_CHAR(d, 'Month')                                      AS month_name,
        EXTRACT(WEEK    FROM d)::SMALLINT                        AS week_of_year,
        EXTRACT(DAY     FROM d)::SMALLINT                        AS day_of_month,
        EXTRACT(DOW     FROM d)::SMALLINT                        AS day_of_week,
        TO_CHAR(d, 'Day')                                        AS day_name,
        CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
        FALSE                                                    AS is_holiday
    FROM (
        SELECT DATEADD(day, seq, '2020-01-01'::DATE) AS d
        FROM (
            SELECT ROW_NUMBER() OVER () - 1 AS seq
            FROM stl_scan LIMIT 4018  -- ~11 years of dates
        )
    )
    WHERE d <= '2030-12-31'
    AND NOT EXISTS (SELECT 1 FROM analytics.dim_date WHERE full_date = d::DATE);
    """
    execute_sql(conn, populate_sql)


# ── Load: COPY from S3 ────────────────────────────────────────────────────────

def load_from_s3() -> None:
    """
    Load orders data from S3 Parquet files into Redshift using the COPY command.

    The COPY command is the most efficient way to load data into Redshift.
    It reads directly from S3 in parallel across all Redshift nodes.

    Requires:
        S3_BUCKET env var — S3 bucket with Parquet files
        IAM_ROLE_ARN env var — IAM role with s3:GetObject permission
    """
    s3_bucket = os.environ.get("S3_BUCKET")
    iam_role_arn = os.environ.get("IAM_ROLE_ARN")

    if not s3_bucket or not iam_role_arn:
        print("  ✗ S3_BUCKET and IAM_ROLE_ARN environment variables are required for load")
        sys.exit(1)

    s3_path = f"s3://{s3_bucket}/processed/orders/"

    print(f"\n=== Load: COPY from S3 ===\n")
    print(f"  Source: {s3_path}")
    print(f"  Target: analytics.fact_orders")
    print(f"  IAM Role: {iam_role_arn}")

    # COPY command for Parquet format
    # Parquet files include schema information, so column mapping is automatic
    copy_sql = f"""
    COPY analytics.fact_orders (
        order_id, customer_id, order_date, product_id,
        quantity, unit_price, total_amount, status, region
    )
    FROM '{s3_path}'
    IAM_ROLE '{iam_role_arn}'
    FORMAT AS PARQUET
    SERIALIZETOJSON
    COMPUPDATE OFF    -- Skip compression analysis (already encoded in DDL)
    STATUPDATE ON;    -- Update table statistics after load (improves query plans)
    """

    with get_connection() as conn:
        print("  Running COPY command (this may take a few minutes)...")
        execute_sql(conn, copy_sql)

        # Check how many rows were loaded
        count_result = execute_sql(conn, "SELECT COUNT(*) AS row_count FROM analytics.fact_orders;", fetch=True)
        row_count = count_result[0]["row_count"] if count_result else 0
        print(f"  ✓ Load complete — {row_count:,} total rows in fact_orders")

        # Run VACUUM and ANALYZE to optimize query performance after bulk load
        print("  Running VACUUM SORT ONLY (reclaims space, re-sorts data)...")
        execute_sql(conn, "VACUUM SORT ONLY analytics.fact_orders;")
        print("  Running ANALYZE (updates query planner statistics)...")
        execute_sql(conn, "ANALYZE analytics.fact_orders;")
        print("  ✓ Post-load optimization complete")


# ── Query: Analytical queries ─────────────────────────────────────────────────

ANALYTICAL_QUERIES = {
    "daily_revenue": {
        "title": "Daily Revenue (Last 30 Days)",
        "sql": """
            SELECT
                o.order_date,
                d.day_name,
                COUNT(DISTINCT o.order_id)  AS order_count,
                SUM(o.total_amount)         AS revenue,
                AVG(o.total_amount)         AS avg_order_value
            FROM analytics.fact_orders o
            JOIN analytics.dim_date d ON d.full_date = o.order_date
            WHERE o.order_date >= DATEADD(day, -30, CURRENT_DATE)
              AND o.status != 'cancelled'
            GROUP BY o.order_date, d.day_name
            ORDER BY o.order_date DESC
            LIMIT 30;
        """,
    },
    "top_products": {
        "title": "Top 10 Products by Revenue",
        "sql": """
            SELECT
                product_id,
                COUNT(DISTINCT order_id)    AS order_count,
                SUM(quantity)               AS units_sold,
                SUM(total_amount)           AS total_revenue,
                AVG(unit_price)             AS avg_price
            FROM analytics.fact_orders
            WHERE status != 'cancelled'
              AND order_date >= DATEADD(month, -3, CURRENT_DATE)
            GROUP BY product_id
            ORDER BY total_revenue DESC
            LIMIT 10;
        """,
    },
    "customer_ltv": {
        "title": "Customer Lifetime Value (Top 20 Customers)",
        "sql": """
            SELECT
                customer_id,
                COUNT(DISTINCT order_id)                    AS total_orders,
                SUM(total_amount)                           AS lifetime_value,
                AVG(total_amount)                           AS avg_order_value,
                MIN(order_date)                             AS first_order_date,
                MAX(order_date)                             AS last_order_date,
                DATEDIFF(day, MIN(order_date), MAX(order_date)) AS customer_age_days
            FROM analytics.fact_orders
            WHERE status != 'cancelled'
            GROUP BY customer_id
            HAVING COUNT(DISTINCT order_id) >= 2   -- Only repeat customers
            ORDER BY lifetime_value DESC
            LIMIT 20;
        """,
    },
    "regional_performance": {
        "title": "Revenue by Region",
        "sql": """
            SELECT
                region,
                COUNT(DISTINCT order_id)    AS order_count,
                COUNT(DISTINCT customer_id) AS unique_customers,
                SUM(total_amount)           AS total_revenue,
                AVG(total_amount)           AS avg_order_value,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancellations,
                ROUND(
                    100.0 * SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)
                    / NULLIF(COUNT(*), 0), 2
                ) AS cancellation_rate_pct
            FROM analytics.fact_orders
            WHERE order_date >= DATEADD(month, -1, CURRENT_DATE)
            GROUP BY region
            ORDER BY total_revenue DESC;
        """,
    },
}


def run_queries() -> dict[str, list[dict]]:
    """
    Run all analytical queries and return results.

    Returns:
        Dict mapping query name → list of result row dicts
    """
    print("\n=== Query: Running Analytical Queries ===\n")
    results = {}

    with get_connection() as conn:
        for query_name, query_info in ANALYTICAL_QUERIES.items():
            print(f"  Running: {query_info['title']}...", end=" ", flush=True)
            try:
                rows = execute_sql(conn, query_info["sql"], fetch=True)
                results[query_name] = rows or []
                print(f"✓ ({len(results[query_name])} rows)")
            except Exception as e:
                print(f"✗ Error: {e}")
                results[query_name] = []

    return results


# ── Report: Print formatted results ──────────────────────────────────────────

def print_table(title: str, rows: list[dict], max_col_width: int = 20) -> None:
    """
    Print query results as a formatted ASCII table.

    Args:
        title:         Table title
        rows:          List of row dicts
        max_col_width: Maximum column width before truncation
    """
    if not rows:
        print(f"\n  {title}: No data")
        return

    columns = list(rows[0].keys())

    # Calculate column widths
    col_widths = {}
    for col in columns:
        header_width = len(col)
        max_data_width = max(len(str(row.get(col, ""))) for row in rows)
        col_widths[col] = min(max(header_width, max_data_width), max_col_width)

    # Build separator line
    separator = "+-" + "-+-".join("-" * col_widths[c] for c in columns) + "-+"

    print(f"\n  {title}")
    print("  " + separator)

    # Header row
    header = "| " + " | ".join(col.upper()[:col_widths[c]].ljust(col_widths[c]) for c in columns) + " |"
    print("  " + header)
    print("  " + separator)

    # Data rows
    for row in rows:
        data_row = "| " + " | ".join(
            str(row.get(col, ""))[:col_widths[col]].ljust(col_widths[col])
            for col in columns
        ) + " |"
        print("  " + data_row)

    print("  " + separator)
    print(f"  ({len(rows)} row(s))")


def print_report() -> None:
    """
    Run all analytical queries and print formatted results tables.
    """
    print("\n=== Report: Analytical Query Results ===")
    results = run_queries()

    for query_name, query_info in ANALYTICAL_QUERIES.items():
        rows = results.get(query_name, [])
        print_table(query_info["title"], rows)

    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Redshift data warehouse operations"
    )
    parser.add_argument(
        "command",
        choices=["setup", "load", "query", "report"],
        help=(
            "setup  — Create tables\n"
            "load   — COPY data from S3\n"
            "query  — Run analytical queries\n"
            "report — Print formatted query results"
        ),
    )
    args = parser.parse_args()

    print(f"\n=== Redshift Operations: {args.command.upper()} ===")

    if args.command == "setup":
        setup_tables()
    elif args.command == "load":
        load_from_s3()
    elif args.command == "query":
        results = run_queries()
        for name, rows in results.items():
            print(f"  {name}: {len(rows)} rows")
    elif args.command == "report":
        print_report()


if __name__ == "__main__":
    main()
