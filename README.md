<!-- public-top -->
# Model Monitoring API

The churn model served by FastAPI with Prometheus request, latency and score histograms, plus a z-score drift check on the last 200 inputs. Portfolio, ML Engineer.

**Watch it first:** [the 90-second film](demo/film.mp4) (what it does, how it is built, the proof, the answer) or the [60-second cut](demo/film-60s.mp4). The plain walkthrough with captions is [demo/demo.mp4](demo/demo.mp4).

## Try it in three commands

```bash
git clone https://github.com/Keshigami/model_monitoring_api.git && cd model_monitoring_api
just setup        # creates the venv with uv (Python 3.11)
just up           # http://127.0.0.1:8115/  (just down to stop)
```

You need [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just) (`brew install uv just` on a Mac). Everything the app needs is in the repo (synthetic sample data where a dataset is used). No API key is needed anywhere in this project. `just test` runs the lint and the offline tests.

Step by step: [docs/Getting-Started.md](docs/Getting-Started.md), then [how it was built](docs/How-It-Was-Built.md), [results](docs/Results.md), [limits](docs/Limits-and-Next-Steps.md) and [the film](docs/The-Film.md). The same pages are on the [wiki](https://github.com/Keshigami/model_monitoring_api/wiki).
<!-- /public-top -->
# Model-in-Production Demo with Monitoring

## Demo walkthrough
<!-- demo:auto -->
![demo](demo/demo.gif)

Full walkthrough with captions: [demo/demo.mp4](demo/demo.mp4) (76 s, 1280x800, animated intro and end card). Run it yourself: `just setup && just up`, then open http://localhost:8115/.

Two-minute walkthrough:
1. Model monitoring: fire 50 requests at the churn model
2. Live numbers: predictions served, p50 and p99 inference time, drift status
3. Churn probability histogram over the last window
4. Drift table: training mean versus recent mean, per feature
5. Now 50 drifted requests: the flags change
6. The drift rows flagged
7. The raw Prometheus scrape at /metrics
8. Back on the page: the tiles keep counting
<!-- /demo:auto -->

A FastAPI prediction service with Prometheus metrics and a drift check. The model behind `/predict` is the real churn
classifier trained by `../churn_predictor/train.py`, not a random number. Port **8115**.

## 1. Problem statement and business impact
- **The problem**: models in production fail silently: latency creeps up, the input distribution drifts, the score
  distribution shifts, and nobody notices until the business metric moves.
- **Goal**: a prediction API where every request is counted and timed, scores are histogrammed for Prometheus, and the
  inputs are compared with the training distribution on demand.
- **Metric of success (original brief)**: p99 latency < 100 ms, full visibility into request and error trends.
  Measured here: p99 **14.9 ms** end to end over 200 real HTTP requests.

## 2. Technical solution
- **Stack**: Python 3.11 via uv, FastAPI, `prometheus_client` (middleware + `/metrics` mount), pydantic, joblib,
  scikit-learn (to unpickle the churn bundle), uvicorn. Status page in plain HTML on `common/ui.css`.
- **Endpoints**
  - `GET /` status page: fire 50 requests (or 50 drifted ones), score one customer, live stat tiles, score histogram,
    per-feature drift table.
  - `GET /health` -> `{"ok": true, "service": "model_monitoring_api", "model_loaded": true}`.
  - `POST /predict` body = customer fields (all optional, validated enums) -> churn probability, class, model name,
    inference ms.
  - `POST /simulate?n=50&shifted=false` scores n random customers in-process (the button on the status page);
    `shifted=true` adds 36 months of tenure and $60 of charges so the drift check has something to flag.
  - `GET /drift` z-score of each numeric feature's recent mean against the training mean (standard error of the mean
    over the last N = 200 requests), plus category share shifts; `status` is `stable` or `drift`.
  - `GET /metrics` Prometheus text: `api_requests_total{endpoint,method,status}`,
    `api_request_duration_seconds` histogram per endpoint, `model_prediction_score` histogram (10 buckets).
  - `GET /summary` the JSON the status page reads.
- **Model**: `CHURN_MODEL_PATH` (default `../churn_predictor/models/churn.joblib`), the champion pipeline in the bundle.

## 3. Results on this machine
`uv run python simulate_load.py --n 200` against the running service:

| Measure | Value |
|---|---|
| Throughput (sequential client) | 114 req/s |
| HTTP latency p50 / p95 / p99 | 7.99 / 13.33 / 14.93 ms |
| In-process inference (logistic regression) | about 2 ms, first call about 20 ms |
| Status codes | 200 x 200 |
| Drift on random traffic | stable, all |z| < 2 |
| Drift on shifted traffic (`--shifted`) | `drift`, Tenure and TotalCharges flagged (z > 3) |

## 4. How to run
```bash
just model_monitoring_api-setup    # uv sync, copies common/ui.css, trains the churn model if missing
just model_monitoring_api-test     # ruff + pytest (6 tests with TestClient)
just model_monitoring_api-up       # http://127.0.0.1:8115/
just model_monitoring_api-load     # 200 real requests, prints latency, score and drift summary
just model_monitoring_api-down
```

## 5. Two-minute interviewer walkthrough
1. Open http://127.0.0.1:8115/. The badge says which model is loaded.
2. Press **Fire 50 requests**: tiles update (count, p50, p99, mean score), the histogram fills, the drift table shows
   z near 0 and green "ok" pills.
3. Press **Fire 50 drifted requests** twice: Tenure and TotalCharges turn amber, status flips to `drift`. That is the
   z-test on the rolling window doing its job.
4. Open `/metrics` and search for `model_prediction_score_bucket` and `api_request_duration_seconds_bucket`: that is
   what Prometheus would scrape. `/docs` shows the OpenAPI page.

## 6. What is real and what is simulated
- Real: the model, the predictions, the metrics, the latencies, the drift arithmetic.
- Simulated: the traffic. `random_customer()` draws plausible customers; `shifted=true` is a deliberate distribution
  shift. There is no Prometheus server or Grafana in this repo; the `/metrics` text is what one would scrape.
- The original `main.py` returned `random.random()` as the prediction and slept a random 10-100 ms; both are gone.
- The rolling window lives in process memory, so it resets on restart and would not be shared across workers.

## Standalone repo

Exported from Max's `caltech-capstone` workspace. `common/` is vendored (LLM door, UI tokens). Run: `just setup && just test && just up`.
LLM-backed features read `ANTHROPIC_API_KEY` (or `LLM_PROVIDER` + `OPENAI_API_KEY` / `GOOGLE_API_KEY`); with no key they run in a deterministic offline mode.
Film: `demo/film.mp4` (90 s, what it does, how it is built, the proof, the answer) and `demo/film-60s.mp4` (60 s cut); `demo/demo.mp4` is the plain walkthrough.
