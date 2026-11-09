def test_health_and_index(client):
    h = client.get("/health").json()
    assert h["ok"] is True and h["service"] == "model_monitoring_api" and h["model_loaded"] is True
    r = client.get("/")
    assert r.status_code == 200 and "Model Monitoring API" in r.text and 'id="run"' in r.text
    assert client.get("/static/ui.css").status_code == 200


def test_predict_returns_probability(client):
    r = client.post("/predict", json={"Tenure": 2, "MonthlyCharges": 110, "Contract": "Month-to-month"})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["prediction"] <= 1.0 and body["model"] in ("random_forest", "logistic_regression")
    low = client.post("/predict", json={"Tenure": 70, "MonthlyCharges": 25, "Contract": "Two year"}).json()
    assert low["prediction"] < body["prediction"], "long tenure on a two-year contract should look safer"


def test_predict_validates_input(client):
    assert client.post("/predict", json={"Contract": "Lifetime"}).status_code == 422


def test_metrics_contains_custom_histograms(client):
    client.post("/predict", json={})
    text = client.get("/metrics").text
    assert "model_prediction_score_bucket" in text
    assert "api_request_duration_seconds_bucket" in text
    assert 'api_requests_total{endpoint="/predict",method="POST",status="200"}' in text


def test_drift_reports_per_feature_numbers(client):
    r = client.post("/simulate", json=None, params={"n": 30, "seed": 1}).json()
    assert r["n"] == 30 and r["summary"]["requests"] >= 30
    d = client.get("/drift").json()
    assert d["n"] >= 30 and d["status"] in ("stable", "drift")
    for f in ("Tenure", "MonthlyCharges", "TotalCharges"):
        row = d["features"][f]
        assert {"train_mean", "recent_mean", "z", "drifted"} <= set(row)
        assert isinstance(row["z"], float)
    assert "share_shift" in d["features"]["Contract"]


def test_shifted_traffic_is_flagged(client):
    client.post("/simulate", params={"n": 200, "shifted": "true", "seed": 2})
    d = client.get("/drift").json()
    assert d["status"] == "drift" and "Tenure" in d["drifted_features"]
    assert d["features"]["Tenure"]["z"] > 3
