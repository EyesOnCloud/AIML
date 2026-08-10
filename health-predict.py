import joblib
import numpy as np

MODEL_PATH = "model/health_model.joblib"
_model = None
FEATURES = ["cpu_pct", "mem_pct", "latency_ms", "error_rate_pct"]

def load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def predict(metrics: dict) -> dict:
    model = load_model()
    X = np.array([[metrics[f] for f in FEATURES]])
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    classes = model.classes_.tolist()
    return {
        "predicted_state": pred,
        "confidence": round(float(max(proba)), 4),
        "probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
    }
