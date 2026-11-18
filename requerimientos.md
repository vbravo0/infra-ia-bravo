# Matriz de Requerimientos y Cobertura de Tests

Mapeo directo entre los compromisos tecnicos respondidos en la devolucion del foro (`respuesta-foro.md`) y su estado real de implementacion y pruebas en `test-llm-cve`.

**Escala de testeabilidad:**
- **Alta:** Test unitario o de contrato directo en `pytest` (rapido, en memoria).
- **Media:** Requiere script offline, dataset real o levantar un servicio/BD real (`evaluate.py`, Postgres, Ollama).
- **Baja (Infra):** Configuracion declarativa de K8s/CI (`kubectl`, HPA, GitHub Actions); no se testea en `pytest`.

---

## 1. Prompt, Versionado y Seguridad (Puntos 1 y 10)

| ID | Requerimiento | Pregunta | Implementado | Testeabilidad | Estado de Test | Comentarios |
|---|---|---|---|---|---|---|
| **REQ-01** | Prompt guardado en archivo versionado `system_prompt.txt` con hash SHA256 | 1.1, 1.3 | ✅ Si | **Alta** | ✅ Unitario (`test_healthz`) | `test_healthz` valida que retorne `prompt_hash`. Falta test unitario dedicado que verifique que un cambio de texto cambie el hash (trivial). |
| **REQ-02** | Rollback rapido de modelo/prompt (`kubectl rollout undo deploy/model`) | 1.4 | ✅ Si (`Makefile`) | **Baja (Infra)** | ❌ Sin test | Operacion de Kubernetes/Helm; se valida manualmente en k3d. |
| **REQ-03** | Defensa contra Prompt Injection encapsulando input como JSON pasivo | 10.1 | ✅ Si | **Alta** (Unit) / **Media** (LLM real) | ✅ Unitario + ✅ Integracion | Unit (`test_build_messages_isolates_json_payload`) valida el escape JSON. Integracion (`test_real_llm_prompt_injection_override`, `test_real_llm_prompt_injection_json_breakout`) prueba contra Qwen2.5 real en CPU. |
| **REQ-04** | Salida invalida del LLM retorna `UNKNOWN` y marca error de parseo | 10.2 | ✅ Si | **Alta** | ✅ Unitario | `test_parse_output_rejects_invalid_llm_output`, `test_predict_records_parse_error_in_repo` y `test_invalid_llm_output_increments_prometheus_metrics`. |

---

## 2. Datos, Entrenamiento y Evaluacion (Puntos 3, 4 y 6)

| ID | Requerimiento | Pregunta | Implementado | Testeabilidad | Estado de Test | Comentarios |
|---|---|---|---|---|---|---|
| **REQ-05** | Descartar nulos (`dropna`) y descripciones duplicadas (`drop_duplicates`) | 3.3, 3.5 | ✅ Si (`train.py`) | **Alta** | ✅ Unitario (`test_dataset_cleaning.py`) | Funcion pura `clean_cve_dataset` en `train.py`, testeada en `test_clean_cve_dataset_removes_nulls_in_description_and_severity` y `test_clean_cve_dataset_removes_duplicate_descriptions`. |
| **REQ-06** | Modelo base propio: `TF-IDF + LogisticRegression` (`class_weight="balanced"`) | 4.1 | ✅ Si (`train.py`) | **Alta** | ✅ Unitario (`test_predict_tfidf`) | `Dockerfile.test` entrena en build time y `test_predict_tfidf` valida inferencia y `confidence` float. |
| **REQ-07** | Muestra de evaluacion de **1.000 casos estratificados** (2do sem 2024) | 6.1, 6.2, 6.3, 6.6 | ✅ Si (`data/sample_1000.csv`) | **Alta** | ✅ Generado | Muestra estratificada real extraida con `build_sample_1000.py` sobre `all_cves.zip` (2do sem 2024): 450 MEDIUM (45%), 370 HIGH (37%), 164 CRITICAL (16.4%) y 16 LOW (1.6%). |
| **REQ-08** | Quality Gate automatico en CI/CD (Macro F1, frena deploy si cae) | 1.2, 6.4 | ⚠️ Parcial (`evaluate.py`) | **Alta** (`evaluate.py`) / **Baja** (CI YAML) | ❌ Sin test | Se puede testear unitariamente que la funcion de corte retorne error si `macro_f1 < MIN_F1_THRESHOLD`, y enganchar `evaluate.py` en `.github/workflows/deploy.yml`. |
| **REQ-09** | Comparacion estadistica entre versiones (Test de McNemar + Bootstrap pareado en Macro F1) | 4.2, 6.2 | ❌ No | **Alta** | ❌ Sin test | Una vez implementadas las funciones matematicas de McNemar y bootstrap en `evaluate.py`, son 100% testeables con vectores sinteticos en `pytest`. |

---

## 3. Contrato de Servicio, Carga e Infraestructura (Puntos 7 y 8)

| ID | Requerimiento | Pregunta | Implementado | Testeabilidad | Estado de Test | Comentarios |
|---|---|---|---|---|---|---|
| **REQ-10** | Contrato `/predict`: recibe `cve_id`, `description`, `engine`; devuelve `severity`, `model_hash` (Git SHA) y `confidence` (`float` para TF-IDF, `null` para LLM) | 7.2 | ✅ Si | **Alta** | ✅ Unitario + ✅ Integracion | Cubierto por `test_predict_tfidf`, `test_predict_llm_with_fake` y `test_real_llm_cve_classification`. |
| **REQ-11** | Limite de lote (Batch): maximo **50 CVEs por request** (endpoint unificado `POST /predict`) | 7.3 | ✅ Si | **Alta** | ✅ Unitario | `test_predict_batch_list_success`, `test_predict_batch_empty_list_returns_empty_list` y `test_predict_batch_rejects_more_than_50_items`. |
| **REQ-12** | Auditoria inmutable en BD (`history` con `model_version`, `prompt_hash`, `latency_ms`) | 1.3 | ✅ Si | **Alta** (Fake) / **Media** (Postgres) | ✅ Unitario (`FakeCveRepository`) | Logica de dominio cubierta en memoria. Un smoke test contra Postgres real seria opcional (Media). |
| **REQ-13** | Autoscaling HPA por uso de CPU (70%) | 8.4 | ✅ Si (`helm/`) | **Baja (Infra)** | ❌ Sin test | Configuracion declarativa de Kubernetes (`hpa.yaml`); no aplica testearlo en Docker Compose. |

---

## 4. Observabilidad, Drift y Feedback (Punto 9)

| ID | Requerimiento | Pregunta | Implementado | Testeabilidad | Estado de Test | Comentarios |
|---|---|---|---|---|---|---|
| **REQ-14** | Endpoint `POST /feedback` append-only para severidad real (NVD o analista) | 9.2 | ✅ Si | **Alta** | ✅ Unitario | `test_feedback_append_only_with_fake_repo` y `test_feedback_invalid_class`. |
| **REQ-15** | Metricas Prometheus de discrepancia (`cve_feedback_discrepancy_total`) para Prediction Drift | 9.1, 9.2 | ✅ Si | **Alta** | ✅ Unitario | Cubierto por `test_feedback_discrepancy_records_prometheus_metrics`. |
| **REQ-16** | Metrica/alerta por baja confianza (`confidence`) en TF-IDF | 9.1 | ✅ Si | **Alta** | ✅ Unitario | Counter `cve_low_confidence_total` en `metrics.py` cuando `confidence < 0.50`, testeado en `test_low_confidence_metric_increments_for_uncertain_predictions`. |

---

## Prioridad para completar (ordenado por facilidad / impacto)

1. **Testear `/metrics` (REQ-04, REQ-15)** — Testeabilidad **Alta** (el codigo ya existe, es solo agregar 2 tests en `test_api.py`).
2. **Metrica de baja confianza TF-IDF (REQ-16)** — Testeabilidad **Alta** (15 min entre codigo y test).
3. **Batch de hasta 50 CVEs (REQ-11)** — Testeabilidad **Alta** (muy util y limpio con Pydantic `max_length=50`).
4. **Muestra `sample_1000.csv` + McNemar/Bootstrap (REQ-07, REQ-09)** — Testeabilidad **Media/Alta** (ideal para el lunes con calma).
