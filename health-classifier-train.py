import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

np.random.seed(42)

def generate_synthetic_metrics(n=6000):
    rows = []
    for _ in range(n):
        state = np.random.choice(["healthy", "degraded", "critical"], p=[0.6, 0.25, 0.15])
        if state == "healthy":
            cpu = np.random.normal(35, 10); mem = np.random.normal(40, 10)
            latency_ms = np.random.normal(80, 20); error_rate = np.random.normal(0.5, 0.3)
        elif state == "degraded":
            cpu = np.random.normal(65, 12); mem = np.random.normal(68, 12)
            latency_ms = np.random.normal(300, 60); error_rate = np.random.normal(3, 1.5)
        else:
            cpu = np.random.normal(90, 8); mem = np.random.normal(92, 6)
            latency_ms = np.random.normal(900, 200); error_rate = np.random.normal(12, 4)
        rows.append({
            "cpu_pct": np.clip(cpu, 0, 100),
            "mem_pct": np.clip(mem, 0, 100),
            "latency_ms": max(latency_ms, 0),
            "error_rate_pct": max(error_rate, 0),
            "state": state,
        })
    return pd.DataFrame(rows)

df = generate_synthetic_metrics()
df.to_csv("data/metrics.csv", index=False)

X = df[["cpu_pct", "mem_pct", "latency_ms", "error_rate_pct"]]
y = df["state"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

model = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42)
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))

joblib.dump(model, "model/health_model.joblib")
print("Model saved to model/health_model.joblib")
