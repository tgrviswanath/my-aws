"""
platform_health.py — Check health of all services in the microservices platform.

Usage:
    python platform_health.py
    python platform_health.py --region us-east-1
    python platform_health.py --watch 30   # Refresh every 30 seconds

What this script checks:
    1. ECS services — desired count == running count
    2. RDS instances — status is 'available'
    3. ElastiCache clusters — status is 'available'
    4. API Gateway — recent 5xx error rate < 1%
    5. Kinesis streams — no shard iterator age > 5 minutes

Output:
    Platform health dashboard with status icons and metrics

Prerequisites:
    pip install boto3
    AWS credentials with ECS, RDS, ElastiCache, APIGateway, Kinesis, CloudWatch permissions
"""

import argparse
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
ecs = boto3.client("ecs")
rds = boto3.client("rds")
elasticache = boto3.client("elasticache")
apigateway = boto3.client("apigateway")
kinesis = boto3.client("kinesis")
cloudwatch = boto3.client("cloudwatch")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ServiceHealth:
    """Health status of a single service or resource."""
    service_type: str      # ECS, RDS, ELASTICACHE, APIGATEWAY, KINESIS
    name: str              # Resource name/identifier
    status: str            # HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
    detail: str            # Human-readable status detail
    metrics: dict = field(default_factory=dict)  # Key metrics (e.g. running_count, error_rate)


# ── ECS health check ──────────────────────────────────────────────────────────

def check_ecs_services() -> list[ServiceHealth]:
    """
    Check all ECS services across all clusters.

    A service is HEALTHY if running_count == desired_count.
    A service is DEGRADED if running_count < desired_count but > 0.
    A service is UNHEALTHY if running_count == 0 and desired_count > 0.

    Returns:
        List of ServiceHealth objects for each ECS service
    """
    results = []

    try:
        # List all ECS clusters
        cluster_arns = []
        paginator = ecs.get_paginator("list_clusters")
        for page in paginator.paginate():
            cluster_arns.extend(page.get("clusterArns", []))

        if not cluster_arns:
            return [ServiceHealth("ECS", "No clusters", "UNKNOWN", "No ECS clusters found")]

        for cluster_arn in cluster_arns:
            cluster_name = cluster_arn.split("/")[-1]

            # List services in this cluster
            service_arns = []
            paginator = ecs.get_paginator("list_services")
            for page in paginator.paginate(cluster=cluster_arn):
                service_arns.extend(page.get("serviceArns", []))

            if not service_arns:
                continue

            # Describe services in batches of 10 (API limit)
            for i in range(0, len(service_arns), 10):
                batch = service_arns[i:i + 10]
                response = ecs.describe_services(cluster=cluster_arn, services=batch)

                for svc in response.get("services", []):
                    svc_name = svc["serviceName"]
                    desired = svc.get("desiredCount", 0)
                    running = svc.get("runningCount", 0)
                    pending = svc.get("pendingCount", 0)

                    # Determine health status
                    if desired == 0:
                        status = "UNKNOWN"
                        detail = "Service is scaled to 0 (intentional?)"
                    elif running == desired:
                        status = "HEALTHY"
                        detail = f"{running}/{desired} tasks running"
                    elif running > 0:
                        status = "DEGRADED"
                        detail = f"Only {running}/{desired} tasks running ({pending} pending)"
                    else:
                        status = "UNHEALTHY"
                        detail = f"0/{desired} tasks running ({pending} pending)"

                    results.append(ServiceHealth(
                        service_type="ECS",
                        name=f"{cluster_name}/{svc_name}",
                        status=status,
                        detail=detail,
                        metrics={
                            "desired": desired,
                            "running": running,
                            "pending": pending,
                        },
                    ))

    except ClientError as e:
        results.append(ServiceHealth("ECS", "Error", "UNKNOWN", f"API error: {e}"))

    return results


# ── RDS health check ──────────────────────────────────────────────────────────

def check_rds_instances() -> list[ServiceHealth]:
    """
    Check all RDS instances and clusters.

    A database is HEALTHY if status is 'available'.
    Other statuses (backing-up, modifying) are DEGRADED.
    Stopped/failed instances are UNHEALTHY.

    Returns:
        List of ServiceHealth objects for each RDS instance
    """
    results = []
    healthy_statuses = {"available", "backing-up"}
    degraded_statuses = {"modifying", "upgrading", "maintenance", "rebooting", "resetting-master-credentials"}

    try:
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                db_id = instance["DBInstanceIdentifier"]
                db_status = instance["DBInstanceStatus"]
                db_class = instance["DBInstanceClass"]
                engine = f"{instance['Engine']} {instance.get('EngineVersion', '')}"
                multi_az = instance.get("MultiAZ", False)

                if db_status in healthy_statuses:
                    status = "HEALTHY"
                    detail = f"Status: {db_status} | {db_class} | {engine}"
                elif db_status in degraded_statuses:
                    status = "DEGRADED"
                    detail = f"Status: {db_status} (temporary) | {db_class}"
                elif db_status == "stopped":
                    status = "UNKNOWN"
                    detail = f"Instance is stopped (intentional?)"
                else:
                    status = "UNHEALTHY"
                    detail = f"Status: {db_status} | {db_class}"

                results.append(ServiceHealth(
                    service_type="RDS",
                    name=db_id,
                    status=status,
                    detail=detail,
                    metrics={
                        "engine": engine,
                        "multi_az": multi_az,
                        "db_class": db_class,
                    },
                ))

    except ClientError as e:
        results.append(ServiceHealth("RDS", "Error", "UNKNOWN", f"API error: {e}"))

    return results


# ── ElastiCache health check ──────────────────────────────────────────────────

def check_elasticache_clusters() -> list[ServiceHealth]:
    """
    Check all ElastiCache clusters (Redis and Memcached).

    Returns:
        List of ServiceHealth objects for each ElastiCache cluster
    """
    results = []

    try:
        paginator = elasticache.get_paginator("describe_cache_clusters")
        for page in paginator.paginate(ShowCacheNodeInfo=True):
            for cluster in page.get("CacheClusters", []):
                cluster_id = cluster["CacheClusterId"]
                cluster_status = cluster["CacheClusterStatus"]
                engine = f"{cluster['Engine']} {cluster.get('EngineVersion', '')}"
                node_type = cluster.get("CacheNodeType", "unknown")
                num_nodes = cluster.get("NumCacheNodes", 0)

                if cluster_status == "available":
                    status = "HEALTHY"
                    detail = f"Status: available | {node_type} | {num_nodes} node(s)"
                elif cluster_status in ("modifying", "rebooting cluster nodes", "snapshotting"):
                    status = "DEGRADED"
                    detail = f"Status: {cluster_status} (temporary)"
                else:
                    status = "UNHEALTHY"
                    detail = f"Status: {cluster_status}"

                results.append(ServiceHealth(
                    service_type="ELASTICACHE",
                    name=cluster_id,
                    status=status,
                    detail=detail,
                    metrics={
                        "engine": engine,
                        "node_type": node_type,
                        "num_nodes": num_nodes,
                    },
                ))

    except ClientError as e:
        results.append(ServiceHealth("ELASTICACHE", "Error", "UNKNOWN", f"API error: {e}"))

    return results


# ── API Gateway health check ──────────────────────────────────────────────────

def get_api_error_rate(api_id: str, stage_name: str, minutes: int = 5) -> float:
    """
    Calculate the 5xx error rate for an API Gateway stage using CloudWatch metrics.

    Args:
        api_id:     API Gateway REST API ID
        stage_name: Stage name (e.g. 'prod')
        minutes:    Lookback window in minutes

    Returns:
        Error rate as a percentage (0.0–100.0), or -1.0 if no data
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)

    try:
        # Fetch 5xx count
        errors_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/ApiGateway",
            MetricName="5XXError",
            Dimensions=[
                {"Name": "ApiName", "Value": api_id},
                {"Name": "Stage",   "Value": stage_name},
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=minutes * 60,
            Statistics=["Sum"],
        )

        # Fetch total request count
        requests_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/ApiGateway",
            MetricName="Count",
            Dimensions=[
                {"Name": "ApiName", "Value": api_id},
                {"Name": "Stage",   "Value": stage_name},
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=minutes * 60,
            Statistics=["Sum"],
        )

        error_points = errors_response.get("Datapoints", [])
        request_points = requests_response.get("Datapoints", [])

        if not request_points:
            return -1.0  # No data

        total_requests = sum(p["Sum"] for p in request_points)
        total_errors = sum(p["Sum"] for p in error_points) if error_points else 0

        if total_requests == 0:
            return 0.0

        return (total_errors / total_requests) * 100

    except ClientError:
        return -1.0


def check_api_gateways() -> list[ServiceHealth]:
    """
    Check all API Gateway REST APIs for recent 5xx error rates.

    An API is HEALTHY if 5xx rate < 1%.
    An API is DEGRADED if 5xx rate is 1–5%.
    An API is UNHEALTHY if 5xx rate > 5%.

    Returns:
        List of ServiceHealth objects for each API Gateway
    """
    results = []

    try:
        # List all REST APIs
        response = apigateway.get_rest_apis(limit=500)
        apis = response.get("items", [])

        for api in apis:
            api_id = api["id"]
            api_name = api["name"]

            # Get stages for this API
            try:
                stages_response = apigateway.get_stages(restApiId=api_id)
                stages = stages_response.get("item", [])
            except ClientError:
                stages = []

            if not stages:
                results.append(ServiceHealth(
                    service_type="APIGATEWAY",
                    name=api_name,
                    status="UNKNOWN",
                    detail="No stages deployed",
                ))
                continue

            for stage in stages:
                stage_name = stage["stageName"]
                error_rate = get_api_error_rate(api_id, stage_name)

                if error_rate < 0:
                    status = "UNKNOWN"
                    detail = f"Stage: {stage_name} | No metrics data (no recent traffic?)"
                elif error_rate < 1.0:
                    status = "HEALTHY"
                    detail = f"Stage: {stage_name} | 5xx rate: {error_rate:.2f}%"
                elif error_rate < 5.0:
                    status = "DEGRADED"
                    detail = f"Stage: {stage_name} | 5xx rate: {error_rate:.2f}% (threshold: 1%)"
                else:
                    status = "UNHEALTHY"
                    detail = f"Stage: {stage_name} | 5xx rate: {error_rate:.2f}% (CRITICAL)"

                results.append(ServiceHealth(
                    service_type="APIGATEWAY",
                    name=f"{api_name}/{stage_name}",
                    status=status,
                    detail=detail,
                    metrics={"error_rate_pct": error_rate},
                ))

    except ClientError as e:
        results.append(ServiceHealth("APIGATEWAY", "Error", "UNKNOWN", f"API error: {e}"))

    return results


# ── Kinesis health check ──────────────────────────────────────────────────────

def get_kinesis_iterator_age(stream_name: str) -> float:
    """
    Get the maximum iterator age for a Kinesis stream from CloudWatch.

    Iterator age > 5 minutes indicates consumers are falling behind.

    Args:
        stream_name: Kinesis stream name

    Returns:
        Maximum iterator age in milliseconds, or -1 if no data
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=10)

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Kinesis",
            MetricName="GetRecords.IteratorAgeMilliseconds",
            Dimensions=[{"Name": "StreamName", "Value": stream_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=["Maximum"],
        )
        points = response.get("Datapoints", [])
        if not points:
            return -1.0
        return max(p["Maximum"] for p in points)
    except ClientError:
        return -1.0


def check_kinesis_streams() -> list[ServiceHealth]:
    """
    Check all Kinesis data streams for consumer lag (iterator age).

    A stream is HEALTHY if max iterator age < 5 minutes.
    A stream is DEGRADED if iterator age is 5–15 minutes.
    A stream is UNHEALTHY if iterator age > 15 minutes.

    Returns:
        List of ServiceHealth objects for each Kinesis stream
    """
    results = []
    max_healthy_age_ms = 5 * 60 * 1000    # 5 minutes in milliseconds
    max_degraded_age_ms = 15 * 60 * 1000  # 15 minutes in milliseconds

    try:
        paginator = kinesis.get_paginator("list_streams")
        stream_names = []
        for page in paginator.paginate():
            stream_names.extend(page.get("StreamNames", []))

        for stream_name in stream_names:
            # Get stream details
            try:
                summary = kinesis.describe_stream_summary(StreamName=stream_name)
                stream_desc = summary["StreamDescriptionSummary"]
                stream_status = stream_desc.get("StreamStatus", "UNKNOWN")
                shard_count = stream_desc.get("OpenShardCount", 0)
            except ClientError:
                stream_status = "UNKNOWN"
                shard_count = 0

            iterator_age_ms = get_kinesis_iterator_age(stream_name)
            iterator_age_min = iterator_age_ms / 60000 if iterator_age_ms >= 0 else -1

            if stream_status != "ACTIVE":
                status = "UNHEALTHY" if stream_status == "DELETING" else "DEGRADED"
                detail = f"Stream status: {stream_status}"
            elif iterator_age_ms < 0:
                status = "UNKNOWN"
                detail = f"Active | {shard_count} shard(s) | No consumer metrics"
            elif iterator_age_ms <= max_healthy_age_ms:
                status = "HEALTHY"
                detail = f"Active | {shard_count} shard(s) | Iterator age: {iterator_age_min:.1f}min"
            elif iterator_age_ms <= max_degraded_age_ms:
                status = "DEGRADED"
                detail = f"Active | {shard_count} shard(s) | Iterator age: {iterator_age_min:.1f}min (>5min)"
            else:
                status = "UNHEALTHY"
                detail = f"Active | {shard_count} shard(s) | Iterator age: {iterator_age_min:.1f}min (CRITICAL)"

            results.append(ServiceHealth(
                service_type="KINESIS",
                name=stream_name,
                status=status,
                detail=detail,
                metrics={
                    "shard_count": shard_count,
                    "iterator_age_ms": iterator_age_ms,
                },
            ))

    except ClientError as e:
        results.append(ServiceHealth("KINESIS", "Error", "UNKNOWN", f"API error: {e}"))

    return results


# ── Dashboard printer ─────────────────────────────────────────────────────────

def print_health_dashboard(all_services: list[ServiceHealth]) -> None:
    """
    Print a formatted platform health dashboard.

    Args:
        all_services: Combined list of ServiceHealth objects from all checks
    """
    status_icons = {
        "HEALTHY":   "✓ HEALTHY  ",
        "DEGRADED":  "⚠ DEGRADED ",
        "UNHEALTHY": "✗ UNHEALTHY",
        "UNKNOWN":   "? UNKNOWN  ",
    }
    status_colors = {
        "HEALTHY":   "🟢",
        "DEGRADED":  "🟡",
        "UNHEALTHY": "🔴",
        "UNKNOWN":   "⚪",
    }

    # Count by status
    counts = {"HEALTHY": 0, "DEGRADED": 0, "UNHEALTHY": 0, "UNKNOWN": 0}
    for svc in all_services:
        counts[svc.status] = counts.get(svc.status, 0) + 1

    # Overall platform status
    if counts["UNHEALTHY"] > 0:
        overall = "🔴 UNHEALTHY"
    elif counts["DEGRADED"] > 0:
        overall = "🟡 DEGRADED"
    elif counts["UNKNOWN"] > 0:
        overall = "⚪ UNKNOWN"
    else:
        overall = "🟢 HEALTHY"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n" + "=" * 80)
    print(f"  PLATFORM HEALTH DASHBOARD  —  {ts}")
    print("=" * 80)
    print(f"\n  Overall Status: {overall}")
    print(f"  Services: {len(all_services)} total  |  "
          f"🟢 {counts['HEALTHY']} healthy  |  "
          f"🟡 {counts['DEGRADED']} degraded  |  "
          f"🔴 {counts['UNHEALTHY']} unhealthy  |  "
          f"⚪ {counts['UNKNOWN']} unknown")
    print()

    # Group by service type
    service_types = ["ECS", "RDS", "ELASTICACHE", "APIGATEWAY", "KINESIS"]
    type_labels = {
        "ECS":         "ECS Services",
        "RDS":         "RDS Databases",
        "ELASTICACHE": "ElastiCache Clusters",
        "APIGATEWAY":  "API Gateway",
        "KINESIS":     "Kinesis Streams",
    }

    by_type: dict[str, list[ServiceHealth]] = {}
    for svc in all_services:
        by_type.setdefault(svc.service_type, []).append(svc)

    for svc_type in service_types:
        services = by_type.get(svc_type, [])
        if not services:
            continue

        label = type_labels.get(svc_type, svc_type)
        type_healthy = sum(1 for s in services if s.status == "HEALTHY")
        print(f"  ── {label} ({type_healthy}/{len(services)} healthy) ──")

        for svc in sorted(services, key=lambda s: (s.status != "UNHEALTHY", s.status != "DEGRADED", s.name)):
            icon = status_colors.get(svc.status, "⚪")
            status_str = status_icons.get(svc.status, svc.status)
            print(f"  {icon} {status_str}  {svc.name:<35}  {svc.detail}")

        print()

    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Check health of all services in the microservices platform"
    )
    parser.add_argument(
        "--region", default=None,
        help="AWS region (default: from AWS config/env)"
    )
    parser.add_argument(
        "--watch", type=int, default=None, metavar="SECONDS",
        help="Continuously refresh every N seconds (e.g. --watch 30)"
    )
    args = parser.parse_args()

    global ecs, rds, elasticache, apigateway, kinesis, cloudwatch
    if args.region:
        ecs = boto3.client("ecs", region_name=args.region)
        rds = boto3.client("rds", region_name=args.region)
        elasticache = boto3.client("elasticache", region_name=args.region)
        apigateway = boto3.client("apigateway", region_name=args.region)
        kinesis = boto3.client("kinesis", region_name=args.region)
        cloudwatch = boto3.client("cloudwatch", region_name=args.region)

    def run_checks():
        print("\n  Running health checks...", end=" ", flush=True)
        all_services = []

        checks = [
            ("ECS",         check_ecs_services),
            ("RDS",         check_rds_instances),
            ("ElastiCache", check_elasticache_clusters),
            ("API Gateway", check_api_gateways),
            ("Kinesis",     check_kinesis_streams),
        ]

        for name, check_fn in checks:
            print(f"{name}...", end=" ", flush=True)
            results = check_fn()
            all_services.extend(results)

        print("done")
        print_health_dashboard(all_services)

    if args.watch:
        print(f"  Watching platform health (refresh every {args.watch}s) — Ctrl+C to stop")
        try:
            while True:
                run_checks()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n  Stopped.")
    else:
        run_checks()


if __name__ == "__main__":
    main()
