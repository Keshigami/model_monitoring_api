# Limits and next steps

- Traffic is simulated; there is no real client and no Prometheus or Grafana running, only the scrape text.
- The rolling window is in-process memory: it resets on restart and is per worker. Production would push to a
  metrics store or run the drift job over a request log.
- The drift test is a mean shift z-test; it misses variance changes and multivariate drift. Evidently or a PSI/KS
  per feature would be the next step.
- No auth, no rate limiting, no model version in the response beyond the model name.
