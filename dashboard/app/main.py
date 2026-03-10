from fastapi import FastAPI
from .core import MetricPayload, add_metric, get_fleet_status, get_fleet_summary

app = FastAPI(title="Fleet Dashboard")

@app.get("/health")
def health():
    return {"status": "dashboard running"}

@app.post("/metrics")
def receive_metrics(metric: MetricPayload):
    add_metric(metric.to_payload())
    return {"status": "metric stored"}

@app.get("/fleet")
def fleet():
    return get_fleet_status()


@app.get("/fleet/summary")
def fleet_summary():
    return get_fleet_summary()
