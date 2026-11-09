# Model Monitoring API

The churn model served by FastAPI with Prometheus request, latency and score histograms, plus a z-score drift check on the last 200 inputs. Portfolio, ML Engineer, by Maximus Friedrich Baluyot.

**Watch first:** [the 90-second film](https://github.com/Keshigami/model_monitoring_api/blob/main/demo/film.mp4).

## Pages
- [Getting started](Getting-Started.md): run it in three commands, what you see, the API.
- [How it was built](How-It-Was-Built.md): from the brief to a running service, step by step.
- [Results](Results.md): the numbers and what they mean.
- [Limits and next steps](Limits-and-Next-Steps.md): what it cannot do yet.
- [The film](The-Film.md): what the four chapters show.

## The brief
A model that is accurate on the day it ships can quietly degrade: slower responses, inputs that no longer look like
the training set, a score distribution that piles up at one end. This service wraps a real prediction model so every
request is counted and timed for Prometheus and the input stream can be checked for drift on demand. "Solved" means an
operator sees a problem on the status page or in `/metrics` before a customer does.

## The one-line answer
z 13.3 · Tenure drift · 100 shifted requests · flagged above 3

## One honest limit
Traffic is simulated. The window resets on restart.
