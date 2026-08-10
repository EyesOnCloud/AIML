from flask import Flask, request, jsonify
from predict import predict, FEATURES
import os
import logging

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("health-classifier")

app = Flask(__name__)
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "model_version": MODEL_VERSION})

@app.route("/predict", methods=["POST"])
def predict_route():
    data = request.get_json(silent=True) or {}
    missing = [f for f in FEATURES if f not in data]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400
    result = predict(data)
    result["model_version"] = MODEL_VERSION
    logger.info(f"prediction={result['predicted_state']} input={data}")
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
