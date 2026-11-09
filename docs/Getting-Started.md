# Getting started

## What you need
- [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just). On a Mac: `brew install uv just`.
- Python 3.11 is installed by uv.
- No API key is needed anywhere in this project.

## Three commands
```bash
git clone https://github.com/Keshigami/model_monitoring_api.git && cd model_monitoring_api
just setup
just up           # http://127.0.0.1:8115/  (just down to stop)
```
Everything the app needs is in the repo (synthetic sample data where a dataset is used).

## Commands
`just setup`, `just train` where a model is trained, `just up` / `just down`, `just test`, `just demo`.

## What you see
- Run: `just model_monitoring_api-setup && just model_monitoring_api-up`, open `http://127.0.0.1:8115/`.
- Two-minute walkthrough: (1) "Fire 50 requests": tiles, histogram and a green drift table; (2) "Fire 50 drifted
  requests" twice: Tenure and TotalCharges go amber, status `drift`; (3) score one customer in the form;
  (4) open `/metrics` and find `model_prediction_score_bucket`.
- Video clip: `demo/clips/portfolio__model_monitoring_api.webm` (recorded by `just demo-video`).
- Sample inputs: the two buttons; or `curl -X POST localhost:8115/predict -H 'content-type: application/json' -d '{"Tenure": 2, "MonthlyCharges": 110, "Contract": "Month-to-month"}'` returns about 0.93.

## Try this
Try it: Fire 50 drifted requests, twice.
