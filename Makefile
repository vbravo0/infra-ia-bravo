# Makefile calcado del template unlu-ia-infra-cloud con volumen local para Ollama
TAG         ?= local
K3D_CLUSTER ?= infra-cloud
OLLAMA_DIR  ?= /home/vub/.ollama

.DEFAULT_GOAL := help
.PHONY: help train predict-tfidf predict-llm eval-tfidf eval-llm compare test test-unit test-eval test-integration build-model k3d-up k3d-images deploy rollback status clean loadtest-tfidf loadtest-llm

help: ## lista los comandos
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

train: ## entrena el modelo TF-IDF en Docker -> model.joblib
	docker compose -f docker-compose.unit.yml run --rm test-runner python train.py

predict-tfidf: ## genera las predicciones batch del modelo TF-IDF en Docker -> data/predictions_tfidf.csv
	docker compose -f docker-compose.unit.yml run --rm test-runner python -m eval.predict --model tfidf --data data/sample_1000.csv --output data/predictions_tfidf.csv

predict-llm: ## genera las predicciones batch del LLM en Docker (con checkpoints en data/)
	docker compose -f docker-compose.integration.yml run --rm integration-runner python -m eval.predict --model llm --data data/sample_1000.csv --output data/predictions_llm.csv --prompt prompts/system_prompt.txt

eval-tfidf: ## corre el Quality Gate de CI/CD para TF-IDF en Docker (frena si Macro F1 < 0.60)
	docker compose -f docker-compose.unit.yml run --rm test-runner python eval/evaluate.py --pred data/predictions_tfidf.csv

eval-llm: ## corre la evaluacion del LLM calculando F1 sobre sus predicciones en Docker
	docker compose -f docker-compose.unit.yml run --rm test-runner python eval/evaluate.py --pred data/predictions_llm.csv --no-gate

compare: ## compara dos modelos con McNemar y Bootstrap pareado en Docker (ej: make compare PREDA=... PREDB=...)
	docker compose -f docker-compose.unit.yml run --rm test-runner python eval/compare.py --pred-a $(PREDA) --pred-b $(PREDB)

test-unit: ## corre las pruebas unitarias y de evaluacion estadistica en Docker
	docker compose -f docker-compose.unit.yml up --build --abort-on-container-exit --exit-code-from test-runner
	docker compose -f docker-compose.unit.yml down -v

test-eval: ## corre la suite de evaluacion de modelo y significancia estadistica (REQ-08, REQ-09)
	docker compose -f docker-compose.unit.yml run --rm test-runner pytest model/tests/evaluation -v --disable-warnings

test-integration: ## corre las pruebas de integracion reales contra Ollama y Qwen2.5
	docker compose -f docker-compose.integration.yml up --build --attach integration-runner --abort-on-container-exit --exit-code-from integration-runner
	docker compose -f docker-compose.integration.yml down -v

test: ## corre toda la suite automatizada (unitarios + evaluacion estadistica)
	docker compose -f docker-compose.unit.yml up --build --abort-on-container-exit --exit-code-from test-runner
	docker compose -f docker-compose.unit.yml down -v

build-model: ## construye la imagen model:$(TAG)
	docker build --build-arg MODEL_VERSION=$(TAG) -f model/Dockerfile -t model:$(TAG) .

k3d-up: ## crea el cluster k3s montando tus modelos locales de Ollama en /root/.ollama
	@if ! k3d cluster list $(K3D_CLUSTER) >/dev/null 2>&1; then \
	  k3d cluster create $(K3D_CLUSTER) --agents 1 \
	    -v "$(OLLAMA_DIR):/var/lib/ollama-models@server:0" \
	    -v "$(OLLAMA_DIR):/var/lib/ollama-models@agent:0" \
	    --wait; \
	fi

k3d-images: build-model ## importa model:$(TAG) al cluster k3d
	k3d image import model:$(TAG) -c $(K3D_CLUSTER)

deploy: ## despliega el pod de la API + el pod de Ollama montando tus modelos
	helm upgrade --install model helm/charts/model \
	  -f helm/charts/model/values-k3s.yaml \
	  --set image.tag=$(TAG) \
	  --set autoscaling.minReplicas=1 \
	  --set autoscaling.maxReplicas=3 \
	  --wait
	kubectl rollout status deploy/model

rollback: ## vuelve a la version anterior en 5 segundos
	kubectl rollout undo deploy/model
	kubectl rollout status deploy/model

status: ## muestra pods, hpa e historial
	kubectl get pods,svc,hpa
	helm history model

loadtest-tfidf: ## ejecuta prueba de estres con k6 para TF-IDF en el cluster (hace escalar el HPA)
	kubectl create configmap k6-script --from-file=loadtest/k6-script.js --dry-run=client -o yaml | kubectl apply -f -
	kubectl delete job k6 --ignore-not-found
	sed 's/value: "llm"/value: "tfidf"/' loadtest/k6-job.yaml | kubectl apply -f -
	@echo "Esperando que inicie el Job k6..."
	@sleep 3
	kubectl logs -f job/k6

loadtest-llm: ## ejecuta prueba de latencia con k6 para LLM (Qwen2.5) en el cluster
	kubectl create configmap k6-script --from-file=loadtest/k6-script.js --dry-run=client -o yaml | kubectl apply -f -
	kubectl delete job k6 --ignore-not-found
	sed 's/value: "tfidf"/value: "llm"/' loadtest/k6-job.yaml | kubectl apply -f -
	@echo "Esperando que inicie el Job k6..."
	@sleep 3
	kubectl logs -f job/k6
