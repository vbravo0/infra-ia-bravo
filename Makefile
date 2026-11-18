# Makefile calcado del template unlu-ia-infra-cloud con volumen local para Ollama
TAG         ?= local
K3D_CLUSTER ?= infra-cloud
OLLAMA_DIR  ?= /home/vub/.ollama

.DEFAULT_GOAL := help
.PHONY: help train eval-tfidf test test-unit test-eval test-integration build-model k3d-up k3d-images deploy rollback status clean

help: ## lista los comandos
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

train: ## entrena el modelo TF-IDF con data/sample_1000.csv -> model.joblib
	python model/train.py

eval-tfidf: ## corre el Quality Gate de CI/CD para TF-IDF (frena si Macro F1 < 0.60)
	PYTHONPATH=model:. python model/eval/evaluate_tfidf.py

test-unit: ## corre las pruebas unitarias aisladas en memoria (0.2s)
	docker compose -f docker-compose.unit.yml up --build --abort-on-container-exit --exit-code-from test-runner
	docker compose -f docker-compose.unit.yml down -v

test-eval: ## corre la suite de evaluacion de modelo y significancia estadistica (REQ-08, REQ-09)
	docker compose -f docker-compose.unit.yml run --rm test-runner pytest model/tests/evaluation -v --disable-warnings

test-integration: ## corre las pruebas de integracion reales contra Ollama y Qwen2.5
	docker compose -f docker-compose.integration.yml up --build --attach integration-runner --abort-on-container-exit --exit-code-from integration-runner
	docker compose -f docker-compose.integration.yml down -v

test: test-unit test-eval test-integration ## corre todas las suites (unitarias + evaluacion + integracion)

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
