"""Model-in-production demo: the churn champion model (logistic regression, picked by train.py) behind FastAPI,
instrumented with Prometheus, with a z-score drift check on the last N inputs.

    uv run uvicorn main:app --port 8115

Endpoints: GET / (status page), GET /health, POST /predict, POST /simulate, GET /drift, GET /metrics.
The model is the bundle trained by ../churn_predictor/train.py (CHURN_MODEL_PATH overrides the location).
"""
from __future__ import annotations

import math
import os
import random
import statistics
import time
from collections import deque
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
SERVICE = "model_monitoring_api"
MODEL_PATH = Path(os.getenv("CHURN_MODEL_PATH", HERE.parent / "churn_predictor" / "models" / "churn.joblib"))
WINDOW = int(os.getenv("DRIFT_WINDOW", "200"))

REQUEST_COUNT = Counter("api_requests_total", "Total number of requests", ["endpoint", "method", "status"])
REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds",
    "Request latency",
    ["endpoint"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
PREDICTION_SCORE = Histogram(
    "model_prediction_score", "Distribution of churn probabilities", buckets=[i / 10 for i in range(11)]
)


class Customer(BaseModel):
    Tenure: int = Field(6, ge=0, le=120)
    MonthlyCharges: float = Field(95.0, ge=0)
    TotalCharges: float = Field(570.0, ge=0)
    SeniorCitizen: int = Field(0, ge=0, le=1)
    InternetService: Literal["DSL", "Fiber optic", "No"] = "Fiber optic"
    Contract: Literal["Month-to-month", "One year", "Two year"] = "Month-to-month"
    PaymentMethod: Literal["Electronic check", "Mailed check", "Bank transfer", "Credit card"] = (
        "Electronic check"
    )
    PaperlessBilling: Literal["Yes", "No"] = "Yes"
    Gender: Literal["Female", "Male"] = "Female"
    Partner: Literal["Yes", "No"] = "No"
    Dependents: Literal["Yes", "No"] = "No"


class State:
    """Model bundle plus rolling windows of recent inputs, latencies and scores (in-process, by design)."""

    def __init__(self) -> None:
        self.bundle = None
        self.error: str | None = None
        self.recent: deque[dict] = deque(maxlen=WINDOW)
        self.latencies_ms: deque[float] = deque(maxlen=WINDOW)
        self.scores: deque[float] = deque(maxlen=WINDOW)
        self.requests = 0
        self.load()

    def load(self) -> None:
        try:
            self.bundle = joblib.load(MODEL_PATH)
            self.error = None
        except Exception as e:  # noqa: BLE001 - surfaced on /health and /predict
            self.bundle, self.error = None, f"model not loaded from {MODEL_PATH}: {e}"

    @property
    def loaded(self) -> bool:
        return self.bundle is not None

    def predict(self, customer: Customer) -> dict:
        if not self.loaded:
            raise HTTPException(503, self.error or "model not loaded; run `just churn_predictor-train`")
        row = customer.model_dump()
        frame = pd.DataFrame([row], columns=self.bundle["features"])
        name = self.bundle["champion"]
        t0 = time.perf_counter()
        score = float(self.bundle["models"][name].predict_proba(frame)[0][1])
        ms = (time.perf_counter() - t0) * 1000
        self.recent.append(row)
        self.latencies_ms.append(ms)
        self.scores.append(score)
        self.requests += 1
        PREDICTION_SCORE.observe(score)
        return {"prediction": score, "churn": score >= 0.5, "model": name, "inference_ms": round(ms, 3)}


STATE = State()
app = FastAPI(title="Model Monitoring API", version="0.1.0", description=__doc__)
app.mount("/metrics", make_asgi_app())
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    endpoint = request.url.path if not request.url.path.startswith("/static") else "/static"
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
    REQUEST_COUNT.labels(endpoint=endpoint, method=request.method, status=str(response.status_code)).inc()
    return response


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": SERVICE, "model_loaded": STATE.loaded, "model_path": str(MODEL_PATH),
            "model": STATE.bundle["champion"] if STATE.loaded else None}


@app.post("/predict")
def predict(customer: Customer) -> dict:
    return STATE.predict(customer)


def random_customer(rng: random.Random, shifted: bool = False) -> Customer:
    """A plausible customer; `shifted` pushes tenure and charges up so /drift has something to flag."""
    tenure = rng.randint(1, 71) + (36 if shifted else 0)
    monthly = rng.uniform(20, 120) + (60 if shifted else 0)
    return Customer(
        Tenure=tenure,
        MonthlyCharges=round(monthly, 2),
        TotalCharges=round(tenure * monthly + rng.gauss(0, 10), 2),
        SeniorCitizen=rng.choice([0, 1]),
        InternetService=rng.choice(["DSL", "Fiber optic", "No"]),
        Contract=rng.choice(["Month-to-month", "One year", "Two year"]),
        PaymentMethod=rng.choice(["Electronic check", "Mailed check", "Bank transfer", "Credit card"]),
        PaperlessBilling=rng.choice(["Yes", "No"]),
        Gender=rng.choice(["Female", "Male"]),
        Partner=rng.choice(["Yes", "No"]),
        Dependents=rng.choice(["Yes", "No"]),
    )


@app.post("/simulate")
def simulate(n: int = 50, shifted: bool = False, seed: int | None = None) -> dict:
    """Score n random customers in-process (the status page button). `shifted=true` injects drift."""
    n = max(1, min(n, 1000))
    rng = random.Random(seed)
    t0 = time.perf_counter()
    scores = [STATE.predict(random_customer(rng, shifted))["prediction"] for _ in range(n)]
    return {
        "n": n,
        "shifted": shifted,
        "seconds": round(time.perf_counter() - t0, 3),
        "mean_score": round(statistics.fmean(scores), 4),
        "churn_rate": round(sum(s >= 0.5 for s in scores) / n, 4),
        "summary": summary(),
    }


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = min(len(s) - 1, max(0, math.ceil(p / 100 * len(s)) - 1))
    return s[k]


def summary() -> dict:
    lat = list(STATE.latencies_ms)
    buckets = [0] * 10
    for s in STATE.scores:
        buckets[min(9, int(s * 10))] += 1
    return {
        "requests": STATE.requests,
        "window": len(lat),
        "p50_ms": round(percentile(lat, 50), 3),
        "p95_ms": round(percentile(lat, 95), 3),
        "p99_ms": round(percentile(lat, 99), 3),
        "mean_score": round(statistics.fmean(STATE.scores), 4) if STATE.scores else None,
        "score_histogram": buckets,
    }


@app.get("/summary")
def get_summary() -> dict:
    return summary()


@app.get("/drift")
def drift(threshold: float = 3.0) -> dict:
    """z-score of each numeric feature's recent mean against the training mean (standard error of the mean).
    Categoricals: absolute shift of each level's share against the training frequency."""
    if not STATE.loaded:
        raise HTTPException(503, STATE.error)
    stats = STATE.bundle["training_stats"]
    n = len(STATE.recent)
    if n == 0:
        return {"n": 0, "window": WINDOW, "status": "no data", "features": {}}
    recent = pd.DataFrame(list(STATE.recent))
    features: dict[str, dict] = {}
    drifted: list[str] = []
    for c in STATE.bundle["numeric"]:
        mu, sd = stats[c]["mean"], stats[c]["std"] or 1e-9
        recent_mean = float(recent[c].mean())
        z = (recent_mean - mu) / (sd / math.sqrt(n))
        features[c] = {
            "train_mean": round(mu, 4),
            "train_std": round(sd, 4),
            "recent_mean": round(recent_mean, 4),
            "z": round(z, 3),
            "drifted": abs(z) > threshold,
        }
        if abs(z) > threshold:
            drifted.append(c)
    for c in STATE.bundle["categorical"]:
        train = stats[c]["frequencies"]
        rec = recent[c].value_counts(normalize=True).to_dict()
        shift = {k: round(float(rec.get(k, 0.0)) - v, 4) for k, v in train.items()}
        worst = max(abs(v) for v in shift.values())
        features[c] = {"share_shift": shift, "max_abs_shift": round(worst, 4), "drifted": worst > 0.2}
        if worst > 0.2:
            drifted.append(c)
    return {
        "n": n,
        "window": WINDOW,
        "threshold_z": threshold,
        "status": "drift" if drifted else "stable",
        "drifted_features": drifted,
        "features": features,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (HERE / "index.html").read_text()
