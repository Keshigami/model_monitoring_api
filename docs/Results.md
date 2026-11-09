# Results

Measured on this machine against the running service (`just model_monitoring_api-load`):

| Measure | Value |
|---|---|
| HTTP latency p50 / p95 / p99 | 7.99 / 13.33 / 14.93 ms |
| Throughput, one sequential client | 114 req/s |
| Random traffic drift | stable (all |z| < 2) |
| Shifted traffic (+36 months, +$60) | `drift`, Tenure and TotalCharges z > 3 |

p99 under 15 ms clears the original "p99 < 100 ms" target with room to spare; a good production number for a tabular
model behind an HTTP hop is anything under about 50 ms.
