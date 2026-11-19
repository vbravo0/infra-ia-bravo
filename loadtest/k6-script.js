// Load test para probar el autoescalado del HPA en el modelo CVE (Clase 8)
import http from "k6/http";
import { check, sleep } from "k6";

const SLEEP = Number(__ENV.SLEEP || 0.05);
const PEAK_VUS = Number(__ENV.PEAK_VUS || 40);
const MODEL_URL = __ENV.MODEL_URL || "http://model:8081";

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-vus",
      startVUs: 2,
      stages: [
        { duration: "20s", target: 15 },
        { duration: "1m", target: PEAK_VUS }, // Carga sostenida para superar el 60% CPU
        { duration: "20s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

const payload = JSON.stringify([
  {
    cve_id: "CVE-2024-STRESS",
    description: "Buffer overflow vulnerability in authentication handler allows remote command execution and privilege escalation.",
    engine: "tfidf"
  }
]);

export default function () {
  const res = http.post(`${MODEL_URL}/predict`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "predict 200": (r) => r.status === 200 });
  sleep(SLEEP);
}
