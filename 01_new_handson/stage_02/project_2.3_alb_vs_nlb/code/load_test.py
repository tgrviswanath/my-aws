"""
load_test.py — Send HTTP requests to ALB/NLB and measure response times.

Prerequisites:
    pip install requests

Usage:
    python load_test.py --url https://your-alb-url --requests 100
    python load_test.py --url https://your-alb-url --requests 200 --concurrency 20
    python load_test.py --url https://your-alb-url --requests 100 --compare-url https://your-nlb-url

Arguments:
    --url          Target URL (ALB or NLB endpoint)
    --requests     Total number of requests to send (default: 100)
    --concurrency  Number of concurrent workers (default: 10)
    --compare-url  Optional second URL to compare (e.g. NLB vs ALB)
    --timeout      Request timeout in seconds (default: 10)
    --path         URL path to append (default: /)

What this script measures:
    - Min / Max / Mean / Median / P95 / P99 latency
    - Requests per second (throughput)
    - Success rate (2xx responses)
    - Error breakdown by status code
"""

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("[ERROR] requests is not installed. Run: pip install requests")
    sys.exit(1)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class RequestResult:
    """Result of a single HTTP request."""
    url: str
    status_code: int
    latency_ms: float          # Response time in milliseconds
    error: Optional[str] = None
    is_success: bool = False

    def __post_init__(self):
        self.is_success = 200 <= self.status_code < 300


@dataclass
class LoadTestStats:
    """Aggregated statistics for a load test run."""
    url: str
    total_requests: int
    successful: int
    failed: int
    latencies: list[float] = field(default_factory=list)
    status_codes: dict[int, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_requests * 100) if self.total_requests else 0.0

    @property
    def requests_per_second(self) -> float:
        return self.total_requests / self.duration_seconds if self.duration_seconds else 0.0

    @property
    def min_ms(self) -> float:
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.latencies) if self.latencies else 0.0

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0.0

    @property
    def p95_ms(self) -> float:
        return self._percentile(95)

    @property
    def p99_ms(self) -> float:
        return self._percentile(99)

    @property
    def stdev_ms(self) -> float:
        return statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0.0

    def _percentile(self, p: int) -> float:
        """Calculate the p-th percentile of latencies."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * p / 100)
        index = min(index, len(sorted_latencies) - 1)
        return sorted_latencies[index]


# ── HTTP session factory ──────────────────────────────────────────────────────

def create_session(timeout: int) -> requests.Session:
    """
    Create a requests Session with connection pooling and retry logic.
    Using a session per thread avoids connection overhead.
    """
    session = requests.Session()

    # Retry on connection errors and 5xx responses (not on 4xx)
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# ── Single request ────────────────────────────────────────────────────────────

def send_request(url: str, timeout: int, session: requests.Session) -> RequestResult:
    """
    Send a single GET request and return timing + status.
    Catches all exceptions so the thread pool never crashes.
    """
    start = time.perf_counter()
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            url=url,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
    except requests.exceptions.Timeout:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(url=url, status_code=0, latency_ms=latency_ms, error="Timeout")
    except requests.exceptions.ConnectionError as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(url=url, status_code=0, latency_ms=latency_ms, error=f"ConnectionError: {e}")
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(url=url, status_code=0, latency_ms=latency_ms, error=str(e))


# ── Load test runner ──────────────────────────────────────────────────────────

def run_load_test(
    url: str,
    total_requests: int,
    concurrency: int,
    timeout: int,
) -> LoadTestStats:
    """
    Run a load test against the given URL.

    Uses a thread pool to send requests concurrently.
    Each thread gets its own requests.Session for connection pooling.
    """
    print(f"\n  Sending {total_requests} requests to {url}")
    print(f"  Concurrency: {concurrency} workers | Timeout: {timeout}s")
    print("  " + "─" * 50)

    stats = LoadTestStats(
        url=url,
        total_requests=total_requests,
        successful=0,
        failed=0,
    )

    # Thread-local sessions (one per worker)
    sessions: dict[int, requests.Session] = {}

    def worker(request_num: int) -> RequestResult:
        """Worker function — reuses a session per thread."""
        import threading
        thread_id = threading.get_ident()
        if thread_id not in sessions:
            sessions[thread_id] = create_session(timeout)
        return send_request(url, timeout, sessions[thread_id])

    completed = 0
    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(worker, i): i for i in range(total_requests)}

        for future in as_completed(futures):
            result = future.result()
            completed += 1

            # Progress indicator
            if completed % max(1, total_requests // 10) == 0:
                pct = completed / total_requests * 100
                print(f"  Progress: {completed}/{total_requests} ({pct:.0f}%)")

            # Accumulate stats
            stats.latencies.append(result.latency_ms)
            stats.status_codes[result.status_code] = (
                stats.status_codes.get(result.status_code, 0) + 1
            )

            if result.is_success:
                stats.successful += 1
            else:
                stats.failed += 1
                if result.error:
                    stats.errors.append(result.error)

    stats.duration_seconds = time.perf_counter() - start_time

    # Close all sessions
    for session in sessions.values():
        session.close()

    return stats


# ── Print results ─────────────────────────────────────────────────────────────

def print_stats(stats: LoadTestStats, label: str = ""):
    """Print a formatted results table."""
    title = f"Results — {label}" if label else "Results"
    print(f"\n  ── {title} ──")
    print(f"  URL              : {stats.url}")
    print(f"  Total Requests   : {stats.total_requests}")
    print(f"  Successful       : {stats.successful} ({stats.success_rate:.1f}%)")
    print(f"  Failed           : {stats.failed}")
    print(f"  Duration         : {stats.duration_seconds:.2f}s")
    print(f"  Throughput       : {stats.requests_per_second:.1f} req/s")
    print()
    print(f"  Latency (ms):")
    print(f"    Min    : {stats.min_ms:>8.2f} ms")
    print(f"    Mean   : {stats.mean_ms:>8.2f} ms")
    print(f"    Median : {stats.median_ms:>8.2f} ms")
    print(f"    P95    : {stats.p95_ms:>8.2f} ms")
    print(f"    P99    : {stats.p99_ms:>8.2f} ms")
    print(f"    Max    : {stats.max_ms:>8.2f} ms")
    print(f"    StdDev : {stats.stdev_ms:>8.2f} ms")

    if stats.status_codes:
        print()
        print(f"  Status Codes:")
        for code, count in sorted(stats.status_codes.items()):
            bar = "█" * min(count, 40)
            print(f"    {code:>5} : {count:>5}  {bar}")

    if stats.errors:
        unique_errors = list(set(stats.errors))[:5]
        print()
        print(f"  Errors (sample):")
        for err in unique_errors:
            print(f"    - {err}")


def print_comparison(stats1: LoadTestStats, stats2: LoadTestStats, label1: str, label2: str):
    """Print a side-by-side comparison of two load test results."""
    print("\n" + "=" * 70)
    print("  Comparison Report")
    print("=" * 70)
    print(f"  {'Metric':<20} {label1:>20} {label2:>20}")
    print("  " + "─" * 62)

    metrics = [
        ("Success Rate",  f"{stats1.success_rate:.1f}%",    f"{stats2.success_rate:.1f}%"),
        ("Throughput",    f"{stats1.requests_per_second:.1f} req/s", f"{stats2.requests_per_second:.1f} req/s"),
        ("Min Latency",   f"{stats1.min_ms:.2f} ms",        f"{stats2.min_ms:.2f} ms"),
        ("Mean Latency",  f"{stats1.mean_ms:.2f} ms",       f"{stats2.mean_ms:.2f} ms"),
        ("Median Latency",f"{stats1.median_ms:.2f} ms",     f"{stats2.median_ms:.2f} ms"),
        ("P95 Latency",   f"{stats1.p95_ms:.2f} ms",        f"{stats2.p95_ms:.2f} ms"),
        ("P99 Latency",   f"{stats1.p99_ms:.2f} ms",        f"{stats2.p99_ms:.2f} ms"),
        ("Max Latency",   f"{stats1.max_ms:.2f} ms",        f"{stats2.max_ms:.2f} ms"),
    ]

    for name, v1, v2 in metrics:
        print(f"  {name:<20} {v1:>20} {v2:>20}")

    print("=" * 70 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HTTP load test for ALB/NLB comparison.")
    parser.add_argument("--url",         required=True, help="Target URL")
    parser.add_argument("--requests",    type=int, default=100, help="Total requests (default: 100)")
    parser.add_argument("--concurrency", type=int, default=10,  help="Concurrent workers (default: 10)")
    parser.add_argument("--timeout",     type=int, default=10,  help="Request timeout in seconds (default: 10)")
    parser.add_argument("--compare-url", help="Second URL to compare (e.g. NLB endpoint)", default=None)
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  HTTP Load Test — ALB / NLB Comparison")
    print("=" * 60)

    # Run primary load test
    stats1 = run_load_test(
        url=args.url,
        total_requests=args.requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
    )
    print_stats(stats1, label="Primary URL")

    # Run comparison load test if provided
    if args.compare_url:
        stats2 = run_load_test(
            url=args.compare_url,
            total_requests=args.requests,
            concurrency=args.concurrency,
            timeout=args.timeout,
        )
        print_stats(stats2, label="Compare URL")
        print_comparison(stats1, stats2, label1="Primary", label2="Compare")
    else:
        print("\n" + "=" * 60)
        print("  Test Complete")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
