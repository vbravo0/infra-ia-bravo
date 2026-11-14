# Makefile calcado del template unlu-ia-infra-cloud con volumen local para Ollama
TAG         ?= local
K3D_CLUSTER ?= infra-cloud
OLLAMA_DIR  ?= /home/vub/.ollama

.DEFAULT_GOAL := help
.PHONY: help build-model k3d-up k3d-images deploy rollback status clean

help: ## lista los comandos
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

build-model: ## construye la imagen model:$(TAG)
	docker build --build-arg MODEL_VERSION=$(TAG) -t model:$(TAG) ./model

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
