"""
waf_tester.py — Test WAF rules by sending malicious and legitimate requests.

Usage:
    python waf_tester.py --url https://your-alb-url
    python waf_tester.py --url https://your-alb-url --path /api/search --verbose

What this script does:
    1. Sends a legitimate request → expects HTTP 200
    2. Sends SQL injection payloads → expects HTTP 403 (WAF block)
    3. Sends XSS payloads → expects HTTP 403 (WAF block)
    4. Sends bad bot user-agents → expects HTTP 403 (WAF block)
    5. Sends path traversal payloads → expects HTTP 403 (WAF block)
    6. Prints a formatted PASS/FAIL results table

Prerequisites:
    pip install requests
    A WAF-protected ALB or CloudFront distribution URL
"""

import argparse
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.exceptions import RequestException


# ── Test case definition ──────────────────────────────────────────────────────

@dataclass
class TestCase:
    """Represents a single WAF test case."""
    name: str                          # Human-readable test name
    category: str                      # Category: LEGIT, SQLI, XSS, BOT, TRAVERSAL
    method: str                        # HTTP method: GET or POST
    path: str                          # URL path to request
    params: dict = field(default_factory=dict)   # Query string parameters
    headers: dict = field(default_factory=dict)  # Extra request headers
    body: Optional[dict] = None        # POST body (JSON)
    expected_status: int = 200         # Expected HTTP status code
    description: str = ""              # What this test is checking


# ── Test suite ────────────────────────────────────────────────────────────────

def build_test_suite(base_path: str = "/") -> list[TestCase]:
    """
    Build the full WAF test suite.

    Args:
        base_path: The URL path to target (default: '/')

    Returns:
        List of TestCase objects covering all WAF rule categories
    """
    return [
        # ── Legitimate requests (should pass through) ──────────────────────
        TestCase(
            name="Legitimate GET request",
            category="LEGIT",
            method="GET",
            path=base_path,
            expected_status=200,
            description="Normal request — WAF should allow",
        ),
        TestCase(
            name="Legitimate search query",
            category="LEGIT",
            method="GET",
            path=base_path,
            params={"q": "blue running shoes", "page": "1"},
            expected_status=200,
            description="Normal search — WAF should allow",
        ),

        # ── SQL Injection (should be blocked) ──────────────────────────────
        TestCase(
            name="SQL injection — classic OR 1=1",
            category="SQLI",
            method="GET",
            path=base_path,
            params={"id": "1' OR '1'='1"},
            expected_status=403,
            description="Classic SQL injection in query param",
        ),
        TestCase(
            name="SQL injection — UNION SELECT",
            category="SQLI",
            method="GET",
            path=base_path,
            params={"search": "' UNION SELECT username, password FROM users--"},
            expected_status=403,
            description="UNION-based SQL injection",
        ),
        TestCase(
            name="SQL injection — DROP TABLE",
            category="SQLI",
            method="POST",
            path=base_path,
            body={"username": "admin'; DROP TABLE users;--", "password": "x"},
            expected_status=403,
            description="Destructive SQL injection in POST body",
        ),
        TestCase(
            name="SQL injection — time-based blind",
            category="SQLI",
            method="GET",
            path=base_path,
            params={"id": "1; WAITFOR DELAY '0:0:5'--"},
            expected_status=403,
            description="Time-based blind SQL injection",
        ),

        # ── Cross-Site Scripting (should be blocked) ───────────────────────
        TestCase(
            name="XSS — script tag",
            category="XSS",
            method="GET",
            path=base_path,
            params={"q": "<script>alert('xss')</script>"},
            expected_status=403,
            description="Basic XSS script tag injection",
        ),
        TestCase(
            name="XSS — img onerror",
            category="XSS",
            method="GET",
            path=base_path,
            params={"name": "<img src=x onerror=alert(1)>"},
            expected_status=403,
            description="XSS via img onerror attribute",
        ),
        TestCase(
            name="XSS — javascript: URI",
            category="XSS",
            method="GET",
            path=base_path,
            params={"redirect": "javascript:alert(document.cookie)"},
            expected_status=403,
            description="XSS via javascript: URI scheme",
        ),

        # ── Bad Bot User-Agents (should be blocked) ────────────────────────
        TestCase(
            name="Bad bot — sqlmap",
            category="BOT",
            method="GET",
            path=base_path,
            headers={"User-Agent": "sqlmap/1.7.8#stable (https://sqlmap.org)"},
            expected_status=403,
            description="sqlmap automated SQL injection tool",
        ),
        TestCase(
            name="Bad bot — Nikto scanner",
            category="BOT",
            method="GET",
            path=base_path,
            headers={"User-Agent": "Nikto/2.1.6"},
            expected_status=403,
            description="Nikto web vulnerability scanner",
        ),
        TestCase(
            name="Bad bot — Masscan",
            category="BOT",
            method="GET",
            path=base_path,
            headers={"User-Agent": "masscan/1.3 (https://github.com/robertdavidgraham/masscan)"},
            expected_status=403,
            description="Masscan port scanner",
        ),

        # ── Path Traversal (should be blocked) ────────────────────────────
        TestCase(
            name="Path traversal — ../etc/passwd",
            category="TRAVERSAL",
            method="GET",
            path=base_path,
            params={"file": "../../../../etc/passwd"},
            expected_status=403,
            description="Directory traversal to read /etc/passwd",
        ),
        TestCase(
            name="Path traversal — Windows system32",
            category="TRAVERSAL",
            method="GET",
            path=base_path,
            params={"path": "..\\..\\..\\windows\\system32\\cmd.exe"},
            expected_status=403,
            description="Windows path traversal",
        ),
    ]


# ── Test runner ───────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    """Stores the outcome of a single test case."""
    test: TestCase
    actual_status: Optional[int]
    passed: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0


def run_test(base_url: str, test: TestCase, timeout: int = 10, verbose: bool = False) -> TestResult:
    """
    Execute a single WAF test case and return the result.

    Args:
        base_url: Base URL of the target (e.g. 'https://my-alb.example.com')
        test:     The TestCase to execute
        timeout:  Request timeout in seconds
        verbose:  Print request/response details

    Returns:
        TestResult with pass/fail status
    """
    url = base_url.rstrip("/") + test.path

    # Merge test-specific headers with a default browser-like User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/json",
    }
    headers.update(test.headers)  # Test-specific headers override defaults

    if verbose:
        print(f"\n  → {test.method} {url}")
        if test.params:
            print(f"    params: {test.params}")
        if test.body:
            print(f"    body:   {test.body}")
        if test.headers:
            print(f"    headers: {test.headers}")

    start = time.time()
    try:
        if test.method == "GET":
            response = requests.get(
                url, params=test.params, headers=headers, timeout=timeout,
                allow_redirects=False,  # Don't follow redirects — we want the raw WAF response
            )
        else:  # POST
            response = requests.post(
                url, json=test.body, headers=headers, timeout=timeout,
                allow_redirects=False,
            )

        elapsed_ms = (time.time() - start) * 1000
        passed = response.status_code == test.expected_status

        if verbose:
            print(f"    ← HTTP {response.status_code} ({elapsed_ms:.0f}ms) — {'PASS ✓' if passed else 'FAIL ✗'}")

        return TestResult(
            test=test,
            actual_status=response.status_code,
            passed=passed,
            response_time_ms=elapsed_ms,
        )

    except RequestException as e:
        elapsed_ms = (time.time() - start) * 1000
        return TestResult(
            test=test,
            actual_status=None,
            passed=False,
            error=str(e),
            response_time_ms=elapsed_ms,
        )


# ── Results table ─────────────────────────────────────────────────────────────

def print_results_table(results: list[TestResult]) -> None:
    """
    Print a formatted PASS/FAIL results table grouped by category.

    Args:
        results: List of TestResult objects from the test run
    """
    # Group results by category
    categories: dict[str, list[TestResult]] = {}
    for r in results:
        categories.setdefault(r.test.category, []).append(r)

    category_labels = {
        "LEGIT":    "Legitimate Requests (expect 200)",
        "SQLI":     "SQL Injection (expect 403)",
        "XSS":      "Cross-Site Scripting (expect 403)",
        "BOT":      "Bad Bot User-Agents (expect 403)",
        "TRAVERSAL":"Path Traversal (expect 403)",
    }

    print("\n" + "=" * 80)
    print("  WAF TEST RESULTS")
    print("=" * 80)

    total_pass = 0
    total_fail = 0

    for category, label in category_labels.items():
        cat_results = categories.get(category, [])
        if not cat_results:
            continue

        print(f"\n  {label}")
        print("  " + "-" * 76)

        for r in cat_results:
            status_str = f"HTTP {r.actual_status}" if r.actual_status else f"ERROR: {r.error}"
            expected_str = f"(expected {r.test.expected_status})"
            result_icon = "✓ PASS" if r.passed else "✗ FAIL"
            time_str = f"{r.response_time_ms:.0f}ms"

            print(f"  {result_icon}  {r.test.name:<45} {status_str:<12} {expected_str:<16} {time_str}")

            if r.passed:
                total_pass += 1
            else:
                total_fail += 1

    # Summary
    total = total_pass + total_fail
    score = int((total_pass / total) * 100) if total > 0 else 0

    print("\n" + "=" * 80)
    print(f"  SUMMARY: {total_pass}/{total} tests passed  ({score}% WAF coverage)")
    if total_fail > 0:
        print(f"  ⚠  {total_fail} test(s) FAILED — review WAF rules for those categories")
    else:
        print("  ✓  All tests passed — WAF is correctly blocking malicious requests")
    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test WAF rules by sending malicious and legitimate requests"
    )
    parser.add_argument(
        "--url", required=True,
        help="Base URL of the WAF-protected endpoint (e.g. https://my-alb.example.com)"
    )
    parser.add_argument(
        "--path", default="/",
        help="URL path to target (default: /)"
    )
    parser.add_argument(
        "--timeout", type=int, default=10,
        help="Request timeout in seconds (default: 10)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print request/response details for each test"
    )
    parser.add_argument(
        "--delay", type=float, default=0.2,
        help="Delay between requests in seconds (default: 0.2) — avoids rate limiting"
    )
    args = parser.parse_args()

    print(f"\n=== WAF Rule Tester ===")
    print(f"  Target: {args.url}{args.path}")
    print(f"  Running {len(build_test_suite(args.path))} test cases...\n")

    test_suite = build_test_suite(args.path)
    results = []

    for i, test in enumerate(test_suite, 1):
        print(f"  [{i:02d}/{len(test_suite)}] {test.name}...", end=" ", flush=True)
        result = run_test(args.url, test, timeout=args.timeout, verbose=args.verbose)
        icon = "✓" if result.passed else "✗"
        print(f"{icon}")
        results.append(result)
        time.sleep(args.delay)  # Be polite — avoid triggering rate limiting

    print_results_table(results)

    # Exit with non-zero code if any tests failed (useful in CI pipelines)
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
