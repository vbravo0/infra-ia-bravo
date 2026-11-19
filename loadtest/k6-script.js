// Load test para comparar HPA y latencias entre TF-IDF y LLM en el modelo CVE (Clase 8)
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

// Metricas personalizadas de latencia por motor
const latencyTfidf = new Trend("latency_tfidf", true);
const latencyLlm = new Trend("latency_llm", true);

// Variables de entorno configurables
const ENGINE = __ENV.ENGINE || "tfidf"; // "tfidf" o "llm"
const SLEEP = Number(__ENV.SLEEP || (ENGINE === "llm" ? 2 : 0.05));
const PEAK_VUS = Number(__ENV.PEAK_VUS || (ENGINE === "llm" ? 3 : 40));
const MODEL_URL = __ENV.MODEL_URL || "http://model:8081";

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-vus",
      startVUs: ENGINE === "llm" ? 1 : 2,
      stages: ENGINE === "llm"
        ? [
            { duration: "30s", target: PEAK_VUS },
            { duration: "1m", target: PEAK_VUS },
            { duration: "20s", target: 0 },
          ]
        : [
            { duration: "20s", target: 15 },
            { duration: "1m", target: PEAK_VUS }, // Carga sostenida para superar el 60% CPU
            { duration: "20s", target: 0 },
          ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

const payload = JSON.stringify([
  {
    cve_id: "CVE-2024-STRESS",
    description: "Buffer overflow vulnerability in authentication handler allows remote command execution and privilege escalation.",
    engine: ENGINE
  }
]);

export default function () {
  const start = new Date();
  const res = http.post(`${MODEL_URL}/predict`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  const duration = new Date() - start;

  if (ENGINE === "llm") {
    latencyLlm.add(duration);
  } else {
    latencyTfidf.add(duration);
  }

  check(res, {
    "status 200": (r) => r.status === 200,
  });

  sleep(SLEEP);
}
