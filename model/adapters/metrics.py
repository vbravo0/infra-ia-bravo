from prometheus_client import Counter, Histogram

PREDICTIONS = Counter(
    "cve_predictions_total",
    "Predicciones servidas",
    ["engine", "severity", "version", "prompt_hash"],
)
INVALID_OUTPUT = Counter(
    "cve_invalid_output_total",
    "Salidas del LLM fuera de las 4 clases",
    ["version", "prompt_hash"],
)
PREDICT_LATENCY = Histogram(
    "cve_predict_seconds", "Latencia de prediccion en segundos", ["engine"]
)
