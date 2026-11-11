from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "validation"
    / "api_performance_report.json"
)

ENDPOINTS = [
    ("GET", "/reports/overview", {}),
    ("GET", "/reports/credential-lifecycle", {}),
    ("GET", "/reports/verification-analytics", {}),
    ("GET", "/reports/academic-analytics", {"limit": 100}),
    ("GET", "/reports/data-quality", {}),
    ("GET", "/learners", {"limit": 100, "offset": 0}),
    ("GET", "/learners", {"limit": 100, "offset": 10000}),
    ("GET", "/learners", {"limit": 100, "offset": 19900}),
    ("GET", "/courses", {"limit": 100, "offset": 0}),
    ("GET", "/courses", {"limit": 100, "offset": 500}),
    ("GET", "/courses", {"limit": 100, "offset": 900}),
    ("GET", "/credentials", {"limit": 100, "offset": 0}),
    ("GET", "/credentials", {"limit": 100, "offset": 5000}),
    ("GET", "/credentials", {"limit": 100, "offset": 9900}),
    ("GET", "/enrollments", {"limit": 100, "offset": 0}),
    ("GET", "/completions", {"limit": 100, "offset": 0}),
    ("GET", "/assessment-attempts", {"limit": 100, "offset": 0}),
    ("GET", "/verification/requests", {"limit": 100, "offset": 0}),
    ("GET", "/revocations", {"limit": 100, "offset": 0}),
    ("GET", "/audit", {"limit": 100, "offset": 0}),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure bounded, authenticated API read workloads against the full dataset."
    )
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 26))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(0.95 * len(ordered) + 0.999999) - 1)]


def main() -> int:
    args = parse_args()
    base_url = os.environ.get(
        "ANALYTICS_API_BASE_URL", "http://127.0.0.1:8000/api/v1"
    ).rstrip("/")
    principal = os.environ.get("ANALYTICS_DEMO_USER")
    password = os.environ.get("ANALYTICS_DEMO_PASSWORD")
    if not principal or not password:
        raise RuntimeError(
            "Set ANALYTICS_DEMO_USER and ANALYTICS_DEMO_PASSWORD for a read-only API benchmark."
        )
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("ANALYTICS_API_BASE_URL must be an absolute HTTP(S) URL.")
    if parsed_url.username or parsed_url.password:
        raise ValueError("Do not embed API credentials in ANALYTICS_API_BASE_URL.")

    client = httpx.Client(base_url=base_url, timeout=args.timeout)
    login = client.post(
        "/auth/login",
        json={"principal_key": principal, "password": password},
    )
    if login.status_code != 200:
        raise RuntimeError(f"Benchmark login failed with HTTP {login.status_code}.")
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    samples: list[dict[str, object]] = []
    for method, path, params in ENDPOINTS:
        response = client.request(method, path, params=params)
        if response.status_code != 200:
            raise RuntimeError(
                f"Benchmark warm-up failed for {path} with HTTP {response.status_code}."
            )
    for _ in range(args.repeats):
        for method, path, params in ENDPOINTS:
            started = time.perf_counter()
            response = client.request(method, path, params=params)
            elapsed_ms = (time.perf_counter() - started) * 1000
            samples.append(
                {
                    "method": method,
                    "endpoint": path,
                    "status_code": response.status_code,
                    "response_ms": round(elapsed_ms, 3),
                }
            )

    client.close()
    durations = [float(item["response_ms"]) for item in samples]
    status_distribution: dict[str, int] = {}
    endpoint_durations: dict[str, list[float]] = {}
    successful = 0
    for item in samples:
        status = str(item["status_code"])
        status_distribution[status] = status_distribution.get(status, 0) + 1
        if 200 <= int(status) < 300:
            successful += 1
        endpoint = str(item["endpoint"])
        endpoint_durations.setdefault(endpoint, []).append(float(item["response_ms"]))
    slowest_endpoint = max(
        endpoint_durations,
        key=lambda endpoint: max(endpoint_durations[endpoint]),
    )
    completed_at = datetime.now(timezone.utc).isoformat()
    report = {
        "status": "passed" if successful == len(samples) else "failed",
        "completed_at": completed_at,
        "base_url": base_url,
        "repeats_per_endpoint": args.repeats,
        "warmups_per_endpoint": 1,
        "average_response_ms": round(statistics.fmean(durations), 3),
        "median_response_ms": round(statistics.median(durations), 3),
        "p95_response_ms": round(percentile95(durations), 3),
        "maximum_response_ms": round(max(durations), 3),
        "slowest_endpoint": slowest_endpoint,
        "slowest_endpoint_maximum_ms": round(
            max(endpoint_durations[slowest_endpoint]), 3
        ),
        "total_tested_requests": len(samples),
        "successful_request_percent": round(successful * 100 / len(samples), 3),
        "status_distribution": status_distribution,
        "endpoints": {
            endpoint: {
                "samples": len(values),
                "average_response_ms": round(statistics.fmean(values), 3),
                "median_response_ms": round(statistics.median(values), 3),
                "p95_response_ms": round(percentile95(values), 3),
                "maximum_response_ms": round(max(values), 3),
            }
            for endpoint, values in sorted(endpoint_durations.items())
        },
        "samples": samples,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "samples"},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
