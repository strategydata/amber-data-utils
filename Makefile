.PHONY: build run

IMAGE := gitlabdata:test

# Docker-related
build:
	@echo "Building image..."
	@docker build -t ${IMAGE} .

run: build
	@echo "Building image and opening shell..."
	@docker run -i -t ${IMAGE} /bin/bash

# Dev-related
lint:
	@echo "Linting the repo..."
	@black .

pylint:
	@echo "Running pylint..."
	@pylint ../gitlab-data-utils/ --disable=C --disable=W1203 --disable=W1202 --reports=y

radon:
	@echo "Run Radon to compute complexity..."
	@radon cc . --total-average -nb

xenon:
	@echo "Running Xenon..."
	@xenon --max-absolute B --max-modules A --max-average A .

release:
	./release.sh
