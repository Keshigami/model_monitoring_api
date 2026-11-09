"""Fire N real HTTP requests at the running API and print a latency/score summary plus the drift verdict.

    uv run python simulate_load.py [--n 200] [--url http://127.0.0.1:8115] [--shifted]
"""
from __future__ import annotations

import argparse
import random
import statistics
import time

import requests

from main import percentile, random_customer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--url", default="http://127.0.0.1:8115")
    ap.add_argument("--shifted", action="store_true", help="push tenure and charges up to trigger drift")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    print(f"firing {args.n} POST {args.url}/predict ...")
    lat, scores, statuses = [], [], {}
    t0 = time.perf_counter()
    for i in range(args.n):
        payload = random_customer(rng, args.shifted).model_dump()
        s = time.perf_counter()
        try:
            r = requests.post(f"{args.url}/predict", json=payload, timeout=10)
        except requests.RequestException as e:
            print(f"connection failed on request {i}: {e}")
            return
        lat.append((time.perf_counter() - s) * 1000)
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        if r.ok:
            scores.append(r.json()["prediction"])
    wall = time.perf_counter() - t0
    print(f"done in {wall:.2f}s ({args.n / wall:.0f} req/s); status codes: {statuses}")
    p50, p95, p99 = (percentile(lat, p) for p in (50, 95, 99))
    print(f"HTTP latency ms  p50={p50:.2f}  p95={p95:.2f}  p99={p99:.2f}")
    if scores:
        rate = sum(s >= 0.5 for s in scores) / len(scores)
        print(f"churn score      mean={statistics.fmean(scores):.3f}  predicted churn rate={rate:.1%}")
    d = requests.get(f"{args.url}/drift", timeout=10).json()
    print(f"drift: {d['status']} over last {d['n']}; flagged={d['drifted_features']}")
    for k, v in d["features"].items():
        if "z" in v:
            print(f"  {k:15s} train={v['train_mean']:9.2f} recent={v['recent_mean']:9.2f} z={v['z']:7.2f}")
    m = requests.get(f"{args.url}/metrics", timeout=10).text
    served = [ln for ln in m.splitlines() if ln.startswith("model_prediction_score_count")]
    print(f"prometheus: {served[0] if served else 'model_prediction_score_count missing'}")
    print(f"full text at {args.url}/metrics")


if __name__ == "__main__":
    main()
