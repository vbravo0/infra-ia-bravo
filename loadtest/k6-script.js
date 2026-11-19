// Load test comparativo riguroso: mismo escenario, diferentes engines (Clase 8)
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

// Metricas personalizadas de latencia por motor
const latencyTfidf = new Trend("latency_tfidf", true);
const latencyLlm = new Trend("latency_llm", true);

// Variable de entorno para seleccionar el motor
const ENGINE = __ENV.ENGINE || "tfidf"; // "tfidf" o "llm"
const MODEL_URL = __ENV.MODEL_URL || "http://model:8081";

// MISMA PRUEBA PARA AMBOS:
// Escenario controlado de concurrencia fija para evaluacion comparativa:
// 10 VUs constantes durante 1 minuto con pausas de 1 segundo entre iteraciones.
export const options = {
  scenarios: {
    comparative_benchmark: {
      executor: "constant-vus",
      vus: 10,
      duration: "1m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.10"],
  },
};

const payload = JSON.stringify([
  {
    cve_id: "CVE-2024-BENCH",
    description: "Buffer overflow vulnerability in authentication handler allows remote command execution and privilege escalation.",
    engine: ENGINE
  }
]);

export default function () {
  const start = new Date();
  const res = http.post(`${MODEL_URL}/predict`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: "60s",
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

  sleep(1);
}
