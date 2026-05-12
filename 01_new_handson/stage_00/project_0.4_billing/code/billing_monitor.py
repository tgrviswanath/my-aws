"""
billing_monitor.py — Monitor AWS costs and free tier usage.

Prerequisites:
    pip install boto3

IAM Permissions Required:
    - ce:GetCostAndUsage
    - ce:GetCostForecast
    - budgets:DescribeBudgets
    - freetier:GetFreeTierUsage (if available in your region)

Usage:
    python billing_monitor.py [--profile <aws-profile>] [--region <region>]

What this script does:
    1. Fetch current month-to-date costs using Cost Explorer
    2. List top 5 services by cost
    3. Get cost forecast for the rest of the month
    4. Check budget thresholds (if budgets are configured)
    5. Print a summary report
"""

import argparse
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_month_range() -> tuple[str, str]:
    """
    Return (start_date, end_date) for the current month in YYYY-MM-DD format.
    start_date = first day of the month
    end_date   = today (inclusive)
    """
    today = datetime.utcnow().date()
    start = today.replace(day=1)
    return start.isoformat(), today.isoformat()


def get_forecast_range() -> tuple[str, str]:
    """
    Return (start_date, end_date) for cost forecast.
    start_date = tomorrow
    end_date   = last day of the current month
    """
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    # Last day of the month = first day of next month - 1 day
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return tomorrow.isoformat(), last_day.isoformat()


def format_currency(amount: Decimal | float | str) -> str:
    """Format a numeric amount as USD currency."""
    return f"${float(amount):,.2f}"


# ── Cost Explorer: current month spend ───────────────────────────────────────
def get_current_month_cost(ce_client) -> dict[str, Any]:
    """
    Fetch month-to-date cost and usage from Cost Explorer.
    Returns a dict with 'total', 'by_service', and 'start'/'end' dates.
    """
    start_date, end_date = get_month_range()

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
    except ClientError as e:
        print(f"[ERROR] Failed to fetch cost data: {e}")
        sys.exit(1)

    # Parse results
    results = response.get("ResultsByTime", [])
    if not results:
        return {
            "total": Decimal("0"),
            "by_service": [],
            "start": start_date,
            "end": end_date,
        }

    groups = results[0].get("Groups", [])
    by_service = []
    total = Decimal("0")

    for group in groups:
        service = group["Keys"][0]
        amount = Decimal(group["Metrics"]["UnblendedCost"]["Amount"])
        total += amount
        by_service.append({"service": service, "cost": amount})

    # Sort by cost descending
    by_service.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "total": total,
        "by_service": by_service,
        "start": start_date,
        "end": end_date,
    }


# ── Cost Explorer: forecast ───────────────────────────────────────────────────
def get_cost_forecast(ce_client) -> dict[str, Any]:
    """
    Fetch cost forecast for the remainder of the month.
    Returns a dict with 'forecasted_total', 'start', 'end'.
    """
    start_date, end_date = get_forecast_range()

    # If we're on the last day of the month, no forecast is possible
    if start_date > end_date:
        return {
            "forecasted_total": Decimal("0"),
            "start": start_date,
            "end": end_date,
        }

    try:
        response = ce_client.get_cost_forecast(
            TimePeriod={"Start": start_date, "End": end_date},
            Metric="UNBLENDED_COST",
            Granularity="MONTHLY",
        )
    except ClientError as e:
        # Forecast may not be available for short time ranges
        print(f"[WARN] Cost forecast unavailable: {e}")
        return {
            "forecasted_total": Decimal("0"),
            "start": start_date,
            "end": end_date,
        }

    forecasted = Decimal(response.get("Total", {}).get("Amount", "0"))
    return {
        "forecasted_total": forecasted,
        "start": start_date,
        "end": end_date,
    }


# ── Budgets: check thresholds ─────────────────────────────────────────────────
def check_budgets(budgets_client, account_id: str) -> list[dict[str, Any]]:
    """
    List all budgets and check if any thresholds are breached.
    Returns a list of budget summaries.
    """
    try:
        response = budgets_client.describe_budgets(AccountId=account_id)
    except ClientError as e:
        print(f"[WARN] Failed to fetch budgets: {e}")
        return []

    budgets = response.get("Budgets", [])
    summaries = []

    for budget in budgets:
        name = budget["BudgetName"]
        limit = Decimal(budget["BudgetLimit"]["Amount"])
        actual = Decimal(budget.get("CalculatedSpend", {}).get("ActualSpend", {}).get("Amount", "0"))
        forecasted = Decimal(budget.get("CalculatedSpend", {}).get("ForecastedSpend", {}).get("Amount", "0"))

        percent_used = (actual / limit * 100) if limit > 0 else Decimal("0")
        breached = percent_used >= 100

        summaries.append({
            "name": name,
            "limit": limit,
            "actual": actual,
            "forecasted": forecasted,
            "percent_used": percent_used,
            "breached": breached,
        })

    return summaries


# ── Print report ──────────────────────────────────────────────────────────────
def print_report(cost_data: dict, forecast_data: dict, budget_data: list):
    """Print a formatted cost summary report."""
    print("\n" + "=" * 70)
    print("  AWS Billing Monitor — Cost Summary Report")
    print("=" * 70)

    # Current month spend
    print(f"\n  Period: {cost_data['start']} to {cost_data['end']}")
    print(f"  Total Month-to-Date Cost: {format_currency(cost_data['total'])}")

    # Top 5 services
    print("\n  ── Top 5 Services by Cost ──")
    top_services = cost_data["by_service"][:5]
    if not top_services:
        print("    (No usage recorded)")
    else:
        for i, svc in enumerate(top_services, start=1):
            print(f"    {i}. {svc['service']:<40} {format_currency(svc['cost']):>12}")

    # Forecast
    if forecast_data["forecasted_total"] > 0:
        print(f"\n  ── Cost Forecast (rest of month) ──")
        print(f"    Forecasted: {format_currency(forecast_data['forecasted_total'])}")
        projected_total = cost_data["total"] + forecast_data["forecasted_total"]
        print(f"    Projected month-end total: {format_currency(projected_total)}")
    else:
        print("\n  ── Cost Forecast ──")
        print("    (No forecast available)")

    # Budgets
    if budget_data:
        print("\n  ── Budget Status ──")
        for budget in budget_data:
            status = "🔴 BREACHED" if budget["breached"] else "🟢 OK"
            print(f"    {budget['name']:<30} {status}")
            print(f"      Limit      : {format_currency(budget['limit'])}")
            print(f"      Actual     : {format_currency(budget['actual'])} ({budget['percent_used']:.1f}%)")
            print(f"      Forecasted : {format_currency(budget['forecasted'])}")
    else:
        print("\n  ── Budget Status ──")
        print("    (No budgets configured)")

    print("\n" + "=" * 70 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Monitor AWS costs and budgets.")
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region", help="AWS region", default="us-east-1")
    args = parser.parse_args()

    # Create boto3 session
    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Configure with 'aws configure'.")
        sys.exit(1)

    # Cost Explorer is only available in us-east-1
    ce_client = session.client("ce", region_name="us-east-1")
    budgets_client = session.client("budgets", region_name="us-east-1")

    # Get AWS account ID (needed for budgets API)
    sts_client = session.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]

    # Fetch data
    print("[*] Fetching cost data from AWS Cost Explorer...")
    cost_data = get_current_month_cost(ce_client)

    print("[*] Fetching cost forecast...")
    forecast_data = get_cost_forecast(ce_client)

    print("[*] Checking budget thresholds...")
    budget_data = check_budgets(budgets_client, account_id)

    # Print report
    print_report(cost_data, forecast_data, budget_data)


if __name__ == "__main__":
    main()
