LOCAL_IMAGE ?= argo-streak-detection:dev
CLUSTER     ?= day
NS          ?= argo

.PHONY: help install test run-local \
        argo-install argocd-install argocd-app argocd-password argocd-ui argo-ui \
        submit submit-local image kind-load watch logs status clean

help:               ## list the targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

# ---------- Python, no Kubernetes ----------
install:            ## install Python dependencies
	pip install -r requirements.txt pytest

test:               ## run unit tests
	python -m pytest -q

run-local:          ## run the whole pipeline on this machine
	python -m pipeline --data-dir ./out run-local --n-frames 12 --seed 42

# ---------- one-time cluster setup ----------
argo-install:       ## install Argo Workflows into the cluster
	kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argo --server-side --force-conflicts -f https://github.com/argoproj/argo-workflows/releases/latest/download/install.yaml
	kubectl patch deployment argo-server -n argo --type=json -p='[{"op":"replace","path":"/spec/template/spec/containers/0/args","value":["server","--auth-mode=server","--secure=false"]},{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/scheme","value":"HTTP"}]'
	kubectl rollout status deployment/argo-server -n argo

argocd-install:     ## install Argo CD into the cluster
	kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	kubectl rollout status deployment/argocd-server -n argocd --timeout=300s

argocd-app:         ## connect Argo CD to this repo (starts GitOps)
	kubectl apply -f argocd/application.yaml

argocd-password:    ## print the Argo CD admin password
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

argocd-ui:          ## Argo CD UI at https://localhost:8080 (user: admin)
	kubectl -n argocd port-forward svc/argocd-server 8080:443

argo-ui:            ## Argo Workflows UI at http://localhost:2746
	kubectl -n $(NS) port-forward svc/argo-server 2746:2746

# ---------- running the pipeline ----------
submit:             ## run the pipeline with the image CI deployed
	kubectl create -f examples/workflow.yaml

image:              ## build a local image to try changes before pushing
	docker build --provenance=false -t $(LOCAL_IMAGE) .

kind-load: image    ## load the local image into kind
	kind load docker-image $(LOCAL_IMAGE) --name $(CLUSTER)

submit-local: kind-load  ## run the pipeline with your local image
	kubectl create -f examples/workflow-local.yaml

watch:              ## watch the step pods
	kubectl get pods -n $(NS) -w

logs:               ## report of the latest run (needs: brew install argo)
	argo logs @latest -n $(NS) | tail -25

status:             ## what Argo CD has deployed and the latest runs
	kubectl get application streak-pipeline -n argocd
	kubectl get workflowtemplate streak-pipeline -n $(NS) -o jsonpath='{"image: "}{.spec.arguments.parameters[2].value}{"\n"}'
	kubectl get workflows -n $(NS) --sort-by=.metadata.creationTimestamp | tail -5

clean:              ## delete finished runs and local output
	kubectl delete workflows -n $(NS) --all
	rm -rf ./out
