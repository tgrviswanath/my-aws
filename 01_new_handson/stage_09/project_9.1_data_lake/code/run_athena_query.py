"""
run_athena_query.py — Run Athena SQL queries and display results

Usage:
    # Run a predefined query
    python run_athena_query.py --bucket handson-data-lake-123 --database raw_db

    # Run a custom query
    python run_athena_query.py --bucket handson-data-lake-123 --database raw_db \
        --query "SELECT product_name, SUM(amount) FROM orders GROUP BY 1 ORDER BY 2 DESC"

    # Run all demo queries
    python run_athena_query.py --bucket handson-data-lake-123 --database raw_db --demo
"""

import argparse
import time

import boto3


# ── Demo queries ──────────────────────────────────────────────────────────────

DEMO_QUERIES = [
    {
        "name": "Row count",
        "sql": "SELECT COUNT(*) AS total_orders FROM orders;",
        "purpose": "Verify data was loaded — count all rows",
    },
    {
        "name": "Top products by revenue",
        "sql": """
            SELECT
                product_name,
                COUNT(*) AS order_count,
                ROUND(SUM(amount), 2) AS total_revenue
            FROM orders
            WHERE status = 'completed'
            GROUP BY product_name
            ORDER BY total_revenue DESC
            LIMIT 5;
        """,
        "purpose": "Business query: best-selling products",
    },
    {
        "name": "Partition pruning demo",
        "sql": """
            SELECT COUNT(*) AS jan_orders
            FROM orders
            WHERE year = '2024' AND month = '01';
        """,
        "purpose": "Partition filter — Athena skips other months",
    },
    {
        "name": "Daily revenue trend",
        "sql": """
            SELECT
                order_date,
                COUNT(*) AS orders,
                ROUND(SUM(amount), 2) AS revenue
            FROM orders
            WHERE status = 'completed'
            GROUP BY order_date
            ORDER BY order_date;
        """,
        "purpose": "Time series: daily revenue",
    },
    {
        "name": "Status breakdown",
        "sql": """
            SELECT
                status,
                COUNT(*) AS count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
            FROM orders
            GROUP BY status
            ORDER BY count DESC;
        """,
        "purpose": "Order status distribution",
    },
]


# ── Athena runner ─────────────────────────────────────────────────────────────

def run_query(
    athena_client,
    sql: str,
    database: str,
    results_bucket: str,
    workgroup: str = "primary",
    timeout_seconds: int = 60,
) -> dict:
    """Execute an Athena query and return results."""

    # Start query
    response = athena_client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={
            "OutputLocation": f"s3://{results_bucket}/athena-query-results/"
        },
        WorkGroup=workgroup,
    )
    query_id = response["QueryExecutionId"]

    # Poll for completion
    start = time.time()
    while True:
        status = athena_client.get_query_execution(
            QueryExecutionId=query_id
        )["QueryExecution"]["Status"]

        state = status["State"]
        if state == "SUCCEEDED":
            break
        elif state in ("FAILED", "CANCELLED"):
            reason = status.get("StateChangeReason", "Unknown error")
            raise RuntimeError(f"Query {state}: {reason}")

        elapsed = time.time() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Query timed out after {timeout_seconds}s")

        time.sleep(2)

    # Get execution stats
    exec_info = athena_client.get_query_execution(QueryExecutionId=query_id)
    stats = exec_info["QueryExecution"]["Statistics"]
    data_scanned_kb = stats.get("DataScannedInBytes", 0) / 1024
    runtime_ms = stats.get("TotalExecutionTimeInMillis", 0)

    # Fetch results
    results_pages = athena_client.get_paginator("get_query_results").paginate(
        QueryExecutionId=query_id
    )

    rows = []
    headers = []
    for page in results_pages:
        for i, row in enumerate(page["ResultSet"]["Rows"]):
            values = [col.get("VarCharValue", "") for col in row["Data"]]
            if i == 0 and not headers:
                headers = values
            else:
                rows.append(values)

    return {
        "query_id": query_id,
        "headers": headers,
        "rows": rows,
        "data_scanned_kb": data_scanned_kb,
        "runtime_ms": runtime_ms,
    }


def print_results(result: dict, query_name: str = "") -> None:
    """Pretty-print query results as a table."""
    headers = result["headers"]
    rows = result["rows"]

    if not headers:
        print("  (no results)")
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))

    # Print header
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(
        f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)
    ) + "|"

    print(f"\n  {sep}")
    print(f"  {header_row}")
    print(f"  {sep}")

    # Print data rows
    for row in rows:
        padded = []
        for i, val in enumerate(row):
            if i < len(col_widths):
                padded.append(f" {str(val):<{col_widths[i]}} ")
        print(f"  |{'|'.join(padded)}|")

    print(f"  {sep}")
    print(f"  Rows: {len(rows)} | "
          f"Scanned: {result['data_scanned_kb']:.1f} KB | "
          f"Runtime: {result['runtime_ms']}ms")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run Athena queries on the data lake")
    parser.add_argument("--bucket",    required=True, help="S3 bucket (data lake bucket)")
    parser.add_argument("--database",  default="raw_db", help="Glue database name")
    parser.add_argument("--workgroup", default="handson-data-lake", help="Athena workgroup")
    parser.add_argument("--query",     default=None, help="Custom SQL query to run")
    parser.add_argument("--demo",      action="store_true", help="Run all demo queries")
    parser.add_argument("--region",    default="us-east-1")
    parser.add_argument("--profile",   default=None)
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    athena = session.client("athena")

    print(f"\n{'='*60}")
    print(f"  Athena Query Runner — Data Lake Project 9.1")
    print(f"  Database : {args.database}")
    print(f"  Workgroup: {args.workgroup}")
    print(f"{'='*60}")

    queries_to_run = []

    if args.query:
        queries_to_run = [{"name": "Custom query", "sql": args.query, "purpose": ""}]
    elif args.demo:
        queries_to_run = DEMO_QUERIES
    else:
        # Default: run row count
        queries_to_run = [DEMO_QUERIES[0]]

    total_scanned_kb = 0
    for q in queries_to_run:
        print(f"\n  Query: {q['name']}")
        if q.get("purpose"):
            print(f"  Purpose: {q['purpose']}")
        print(f"  SQL: {q['sql'].strip()[:80]}...")

        try:
            result = run_query(
                athena_client=athena,
                sql=q["sql"],
                database=args.database,
                results_bucket=args.bucket,
                workgroup=args.workgroup,
            )
            print_results(result, q["name"])
            total_scanned_kb += result["data_scanned_kb"]
        except Exception as e:
            print(f"\n  ❌ Query failed: {e}")

    # Total cost estimate
    total_tb = total_scanned_kb / (1024 ** 3)
    cost_usd = total_tb * 5.0  # $5 per TB
    print(f"\n{'='*60}")
    print(f"  Total data scanned: {total_scanned_kb:.1f} KB")
    print(f"  Estimated cost: ${cost_usd:.8f} (at $5/TB)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
