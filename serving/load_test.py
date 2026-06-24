"""Lightweight load test for the /predict endpoint (standard library only).

Sends N requests across C concurrent threads and reports p50/p95/p99 latency and
throughput (RPS). No additional dependencies.

Usage:
    python serving/load_test.py --url http://localhost:17100/predict -n 2000 -c 50
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PAYLOAD = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 2,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 89.5,
    "TotalCharges": 179.0,
}


def one_request(url: str, body: bytes) -> tuple[float, bool]:
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            ok = 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        ok = False
    return (time.perf_counter() - start) * 1000.0, ok


def percentile(vals: list[float], pct: float) -> float:
    if not vals:
        return 0.0
    k = (len(vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test for /predict (churn)")
    parser.add_argument("--url", default="http://localhost:17100/predict")
    parser.add_argument("-n", "--requests", type=int, default=2000)
    parser.add_argument("-c", "--concurrency", type=int, default=50)
    args = parser.parse_args()

    body = json.dumps(PAYLOAD).encode("utf-8")
    print(f"Target: {args.url} | requests: {args.requests} | concurrency: {args.concurrency}\n")

    latencies: list[float] = []
    errors = 0
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(one_request, args.url, body) for _ in range(args.requests)]
        for fut in as_completed(futures):
            ms, ok = fut.result()
            if ok:
                latencies.append(ms)
            else:
                errors += 1
    wall = time.perf_counter() - wall_start

    latencies.sort()
    rps = args.requests / wall if wall > 0 else 0.0
    print("=" * 44)
    print(f"Successful:   {len(latencies)}")
    print(f"Errors:       {errors}")
    print(f"Time:         {wall:.2f} s")
    print(f"Throughput:   {rps:.1f} req/s")
    if latencies:
        print("-" * 44)
        print(f"p50: {percentile(latencies, 50):.2f} ms")
        print(f"p95: {percentile(latencies, 95):.2f} ms")
        print(f"p99: {percentile(latencies, 99):.2f} ms")
    print("=" * 44)


if __name__ == "__main__":
    main()
