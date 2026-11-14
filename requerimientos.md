# Matriz de Requerimientos y Cobertura de Tests

Mapeo directo entre los compromisos tecnicos respondidos en la devolucion del foro (`respuesta-foro.md`) y su estado real de implementacion y pruebas en `test-llm-cve`.

---

## 1. Prompt, Versionado y Seguridad (Puntos 1 y 10)

| ID | Requerimiento | Pregunta | Implementado | Estado de Test | Comentarios |
|---|---|---|---|---|---|
| **REQ-01** | Prompt guardado en archivo versionado `system_prompt.txt` con hash SHA256 | 1.1, 1.3 | ✅ Si | ✅ Unitario (`test_healthz`) | `test_healthz` valida que retorne `prompt_hash`. Falta test unitario dedicado que verifique que un cambio de texto cambie el hash (trivial). |
| **REQ-02** | Rollback rapido de modelo/prompt (`kubectl rollout undo deploy/model`) | 1.4 | ✅ Si (`Makefile`) | ❌ Sin test | Es operacion de Kubernetes/Helm; no aplica en unit/integration Docker Compose, se valida manualmente en k3d. |
| **REQ-03** | Defensa contra Prompt Injection encapsulando input como JSON pasivo | 10.1 | ✅ Si | ✅ Unitario + ✅ Integracion | Unit (`test_build_messages_isolates_json_payload`) valida el escape JSON. Integracion (`test_real_llm_prompt_injection_override`, `test_real_llm_prompt_injection_json_breakout`) prueba contra Qwen2.5 real en CPU. |
| **REQ-04** | Salida invalida del LLM retorna `UNKNOWN` y marca error de parseo | 10.2 | ✅ Si | ✅ Unitario | `test_parse_output_rejects_invalid_llm_output` y `test_predict_records_parse_error_in_repo`. Falta verificar incremento de `cve_invalid_output_total` en `/metrics`. |

---

## 2. Datos, Entrenamiento y Evaluacion (Puntos 3, 4 y 6)

| ID | Requerimiento | Pregunta | Implementado | Estado de Test | Comentarios |
|---|---|---|---|---|---|
| **REQ-05** | Descartar nulos (`dropna`) y descripciones duplicadas (`drop_duplicates`) | 3.3, 3.5 | ✅ Si (`train.py`) | ❌ Sin test | Esta en `model/train.py`, pero no tiene test unitario de pipeline de datos. |
| **REQ-06** | Modelo base propio: `TF-IDF + LogisticRegression` (`class_weight="balanced"`) | 4.1 | ✅ Si (`train.py`) | ✅ Unitario (`test_predict_tfidf`) | `Dockerfile.test` entrena en build time y `test_predict_tfidf` valida inferencia y `confidence` float. |
| **REQ-07** | Muestra de evaluacion de **1.000 casos estratificados** (2do sem 2024) | 6.1, 6.2, 6.3, 6.6 | ⚠️ Parcial (`sample_500.csv`) | ❌ Sin test | `evaluate.py` y `train.py` siguen apuntando a `sample_500.csv`. Falta generar `sample_1000.csv` estratificado con particion temporal estricta. |
| **REQ-08** | Quality Gate automatico en CI/CD (Macro F1 y F2-CRITICAL, frena deploy si cae) | 1.2, 6.4 | ⚠️ Parcial (`evaluate.py`) | ❌ Sin test | `evaluate.py` existe en la raiz, falta verificar que corra como paso obligatorio en `.github/workflows/deploy.yml` y testearlo. |
| **REQ-09** | Comparacion estadistica entre versiones (Test de McNemar + Bootstrap pareado en Macro F1) | 4.2, 6.2 | ❌ No | ❌ Sin test | Prometido en 6.2 (umbral +20% / McNemar / Bootstrap), no implementado aun en `evaluate.py`. |

---

## 3. Contrato de Servicio, Carga e Infraestructura (Puntos 7 y 8)

| ID | Requerimiento | Pregunta | Implementado | Estado de Test | Comentarios |
|---|---|---|---|---|---|
| **REQ-10** | Contrato `/predict`: recibe `cve_id`, `description`, `engine`; devuelve `severity`, `model_hash` (Git SHA) y `confidence` (`float` para TF-IDF, `null` para LLM) | 7.2 | ✅ Si | ✅ Unitario + ✅ Integracion | Cubierto por `test_predict_tfidf`, `test_predict_llm_with_fake` y `test_real_llm_cve_classification`. |
| **REQ-11** | Limite de lote (Batch): maximo **50 CVEs por request** | 7.3 | ❌ No | ❌ Sin test | Hoy `/predict` solo acepta 1 CVE. Falta implementar endpoint batch (o lista en payload) con validacion HTTP 400/422 si `len > 50` + su test unitario. |
| **REQ-12** | Auditoria inmutable en BD (`history` con `model_version`, `prompt_hash`, `latency_ms`) | 1.3 | ✅ Si | ✅ Unitario (`FakeCveRepository`) | Falta test de humo opcional contra Postgres real (`PostgresCveRepository`) si se quiere validar SQL/DDL de `db/schema.sql`. |
| **REQ-13** | Autoscaling HPA por uso de CPU (70%) | 8.4 | ✅ Si (`helm/`) | ❌ Sin test | Configuracion declarativa de Kubernetes (`hpa.yaml`); no aplica testearlo en Docker Compose. |

---

## 4. Observabilidad, Drift y Feedback (Punto 9)

| ID | Requerimiento | Pregunta | Implementado | Estado de Test | Comentarios |
|---|---|---|---|---|---|
| **REQ-14** | Endpoint `POST /feedback` append-only para severidad real (NVD o analista) | 9.2 | ✅ Si | ✅ Unitario | `test_feedback_append_only_with_fake_repo` y `test_feedback_invalid_class`. |
| **REQ-15** | Metricas Prometheus de discrepancia (`cve_feedback_discrepancy_total`) para Prediction Drift | 9.1, 9.2 | ✅ Si | ❌ Sin test | El codigo incrementa `FEEDBACK_DISCREPANCY`, pero ningun test consulta `/metrics` para verificar que el contador suba tras un feedback discrepante. |
| **REQ-16** | Metrica/alerta por baja confianza (`confidence`) en TF-IDF | 9.1 | ❌ No | ❌ Sin test | `metrics.py` tiene latencia, predicciones, invalid_output y feedback, pero no registra histograma/counter de `low_confidence` para TF-IDF. |

---

## Resumen de lo que SI vale la pena agregar / testear antes de cerrar

1. **Batch de hasta 50 CVEs (REQ-11):** implementar soporte batch + test unitario validando limite `<= 50` y rechazo `> 50` (muy facil de testear).
2. **Test de `/metrics` para discrepancias y `parse_error` (REQ-04, REQ-15):** verificar en `test_api.py` que `/metrics` exponga `cve_feedback_discrepancy_total` y `cve_invalid_output_total` cuando ocurren.
3. **Metrica de baja confianza TF-IDF (REQ-16):** sumar counter/gauge en `metrics.py` cuando `confidence < umbral` + test unitario.
4. **Muestra `sample_1000.csv` + McNemar/Bootstrap en `evaluate.py` (REQ-07, REQ-09):** alinear el dataset de evaluacion a 1.000 casos reales y sumar la comparacion estadistica.
