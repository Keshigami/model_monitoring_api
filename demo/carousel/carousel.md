# Model monitoring API · carousel

Spec: film/specs/portfolio__model_monitoring_api.json · 8 slides, 1080x1350.

## 1/8 Hook

- This report is from the running model.

## 2/8 The question

- The inputs moved. The model kept answering.
- Who notices before a customer does?
- mean tenure, random traffic 32.3 mo → mean tenure, shifted traffic 58.0 mo

## 3/8 What it does

- Model monitoring API
- Portfolio · ML Engineer
- Every request counted, timed and checked for drift
- max@baluyot ~ $ curl -s -XPOST ':8115/simulate?n=100&shifted=true&seed=2' >/dev/null && curl -s :8115/drift

## 4/8 How it is built

- 1. Training statistics stored in the bundle; traffi — pandas
- 2. Features — fastapi
- 3. The churn champion pipeline from ../churn_predic — fastapi · prometheus_client · /metrics
- 4. FastAPI + one HTML status page on common — FastAPI
- 5. Dashboard — HTML + ui.css
- Standard error of the mean, so sample size counts

## 5/8 The result

- GET /drift after 100 shifted requests
- Tenure · 35.34 · 58.04 · 13.3 · drift (highlighted)
- MonthlyCharges · 70.10 · 109.05 · 16.5 · drift
- TotalCharges · 2,483 · 6,891 · 28.4 · drift
- SeniorCitizen · 0.53 · 0.46 · -1.7 · ok

## 6/8 The proof

- Fifty requests: served, p50, p99, drift status
- screen: portfolio/model_monitoring_api/demo/poster.png

## 7/8 The answer and the limit

- z 13.3
- Tenure drift · 100 shifted requests · flagged above 3
- Traffic is simulated. The window resets on restart.
- Real model, real metrics. And it ships.

## 8/8 Try it

- Try it: Fire 50 drifted requests, twice.
- max@baluyot ~ $ git clone https://github.com/Keshigami/model_monitoring_api.git
- max@baluyot ~ $ just model_monitoring_api-setup
- max@baluyot ~ $ just model_monitoring_api-up
- github.com/Keshigami/model_monitoring_api
- Maximus Friedrich Baluyot
- AI & ML Specialist · Applied AI · ML Engineering · Automation

_Maximus Friedrich Baluyot · Caltech CTME · PGC AIML_
