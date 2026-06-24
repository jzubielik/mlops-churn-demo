"""FastAPI — service serving the churn model.

Endpoints:
    GET  /health   - healthcheck (liveness/readiness)
    GET  /metrics  - Prometheus metrics
    POST /predict  - churn probability for a single customer

The model (sklearn Pipeline from churnml) is loaded at startup from model.joblib
(in the project directory). The Pipeline does feature engineering + preprocessing
itself, so we accept RAW customer fields and build a single-row DataFrame from them.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, ConfigDict, Field

# model.joblib lives in the project directory (one level above serving/).
MODEL_PATH = Path(__file__).resolve().parent.parent / "model.joblib"

# --- Prometheus metrics -----------------------------------------------------
REQUEST_COUNT = Counter(
    "predict_requests_total", "Number of prediction requests", ["status"]
)
PREDICTION_COUNT = Counter(
    "predictions_by_label_total", "Predictions by label", ["label"]
)
REQUEST_LATENCY = Histogram(
    "predict_request_latency_seconds",
    "Time to handle a prediction request [s]",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Model not found: {MODEL_PATH}. Train it: make train-model (or make repro)."
        )
    STATE["model"] = joblib.load(MODEL_PATH)
    STATE["ready"] = True
    yield
    STATE.clear()


app = FastAPI(
    title="Churn — model serving",
    description="Production skeleton for serving the churn model on FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)


class ChurnInput(BaseModel):
    """Raw customer fields (matching the churn data contract)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 2,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "Fiber optic",
                "OnlineSecurity": "No",
                "OnlineBackup": "No",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "No",
                "StreamingMovies": "No",
                "Contract": "Month-to-month",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 89.5,
                "TotalCharges": 179.0,
            }
        }
    )

    gender: str
    SeniorCitizen: int = Field(..., ge=0, le=1)
    Partner: str
    Dependents: str
    tenure: int = Field(..., ge=0, le=72)
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float = Field(..., ge=0)
    TotalCharges: float = Field(..., ge=0)


class PredictionResponse(BaseModel):
    churn_probability: float
    churn_label: str  # "Yes" / "No"
    threshold: float


@app.get("/health")
def health() -> JSONResponse:
    ready = STATE.get("ready", False)
    payload = {"status": "ok" if ready else "loading", "model_loaded": ready}
    return JSONResponse(payload, status_code=200 if ready else 503)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictionResponse)
def predict(features: ChurnInput, threshold: float = 0.5) -> PredictionResponse:
    start = time.perf_counter()
    try:
        model = STATE["model"]
        row = pd.DataFrame([features.model_dump()])
        proba = float(model.predict_proba(row)[0, 1])
        label = "Yes" if proba >= threshold else "No"

        REQUEST_COUNT.labels(status="success").inc()
        PREDICTION_COUNT.labels(label=label).inc()
        return PredictionResponse(
            churn_probability=round(proba, 6),
            churn_label=label,
            threshold=threshold,
        )
    except Exception:
        REQUEST_COUNT.labels(status="error").inc()
        raise
    finally:
        REQUEST_LATENCY.observe(time.perf_counter() - start)


@app.get("/")
def root() -> dict:
    return {
        "service": "churn-serving",
        "endpoints": ["/health", "/metrics", "/predict", "/docs"],
    }
