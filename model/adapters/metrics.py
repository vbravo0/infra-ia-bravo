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
FEEDBACK_TOTAL = Counter(
    "cve_feedback_total",
    "Feedbacks de severidad real recibidos",
    ["actual_severity"],
)
FEEDBACK_DISCREPANCY = Counter(
    "cve_feedback_discrepancy_total",
    "Discrepancia entre la prediccion original y la severidad real",
    ["engine", "pred_severity", "actual_severity"],
)
LOW_CONFIDENCE = Counter(
    "cve_low_confidence_total",
    "Predicciones con score de confianza inferior al umbral",
    ["engine", "version"],
)
