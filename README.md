# CVE Severity Classifier (PoC MLOps / LLMOps)

PoC de arquitectura cloud-native para clasificacion de severidad de vulnerabilidades (CVEs) bajo el estandar CVSS v3.1 (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), comparando inferencia estadistica supervisada (TF-IDF + SGDClassifier) vs modelo generativo local (Ollama Qwen 2.5:1.5b).

---

## Arquitectura de Entornos

| Entorno | Runtime / Orquestador | Persistencia | Inferencia LLM | Proposito |
|---|---|---|---|---|
| **Test** | Docker Compose (`tmpfs`) | PostgreSQL 16 en RAM | `FakePredictor` / in-memory | Pruebas de contrato e integracion aisladas (`make test`) en < 2s |
| **Local Dev** | k3d / k3s | PostgreSQL pod (PVC local) | Ollama pod (`host.k3d.internal`) | Validacion de Helm, autoscaling (HPA) y metricas Prometheus |
| **Produccion** | GKE (Google Cloud) | Cloud SQL (PostgreSQL) | GPU node pool o modelo servido | Despliegue productivo inmutable via Terraform y CI/CD |

---

## Componentes del Repositorio

- [`model/`](file:///media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/test-llm-cve/model/README.md): Servidor FastAPI con arquitectura hexagonal (`domain` / `adapters`), traits desacoplados y suite de pruebas pytest.
- [`db/`](file:///media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/test-llm-cve/db/schema.sql): Esquema DDL unico (`schema.sql`) para tablas `history` y `feedback_events` (append-only).
- [`helm/`](file:///media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/test-llm-cve/helm/README.md): Charts de Helm para orquestacion en Kubernetes, ConfigMaps de prompt y HPA.
- [`terraform/`](file:///media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/test-llm-cve/terraform/README.md): Aprovisionamiento de infraestructura en GCP (GKE, Artifact Registry, Cloud SQL).

---

## Comandos Principales

### 1. Ejecutar Suite de Tests Aislada (Docker Compose)
Levanta un PostgreSQL efimero en RAM (`tmpfs`), ejecuta las pruebas de contrato y destruye los contenedores:
```bash
make test
```

### 2. Despliegue Local en Kubernetes (k3d)
```bash
# Levantar cluster y dependencias
make cluster-up
make deploy

# Verificar estado de pods y endpoints
kubectl get pods
curl http://localhost:8081/healthz
```

### 3. Calidad y Formato
Formatear todo el codigo Python con Black:
```bash
make format
```
