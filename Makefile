IMAGE   ?= argo-streak-detection:0.1.0
CLUSTER ?= day
NS      ?= argo

.PHONY: install test run-local image kind-load deploy submit watch logs ui clean

install:            ## install Python dependencies
	pip install -r requirements.txt pytest

test:               ## run unit tests
	python -m pytest -q

run-local:          ## run the whole pipeline on this machine (no Kubernetes)
	python -m pipeline --data-dir ./out run-local --n-frames 12 --seed 42

image:              ## build the container image
	docker build -t $(IMAGE) .

kind-load: image    ## copy the image into the kind cluster (no registry needed)
	kind load docker-image $(IMAGE) --name $(CLUSTER)

deploy:             ## install RBAC and the WorkflowTemplate
	kubectl apply -f k8s/rbac.yaml
	kubectl apply -f k8s/workflowtemplate.yaml

submit:             ## start one pipeline run
	kubectl create -f k8s/workflow.yaml

watch:              ## watch the step pods
	kubectl get pods -n $(NS) -w

logs:               ## print the report of the latest run (needs the argo CLI: brew install argo)
	argo logs @latest -n $(NS) | tail -25

ui:                 ## open a tunnel to the Argo UI at http://localhost:2746
	kubectl -n $(NS) port-forward svc/argo-server 2746:2746

clean:              ## delete finished runs and local output
	kubectl delete workflows -n $(NS) --all
	rm -rf ./out
