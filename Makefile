# Makefile for Quantum Werewolf Project
.PHONY: help install test lint format clean docker-build docker-run docker-stop docker-compose-up docker-compose-down

# Variables
PYTHON := python3
PIP := pip3
VENV := venv
DOCKER_IMAGE := quantum-werewolf
DOCKER_TAG := latest

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Quantum Werewolf - Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Installation & Setup
install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -e .
	$(PIP) install -r web/server/requirements.txt

install-dev: install ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install pytest pytest-cov pytest-asyncio pytest-xdist
	$(PIP) install flake8 pylint black mypy
	$(PIP) install sphinx sphinx-rtd-theme

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Virtual environment created. Activate with: source $(VENV)/bin/activate$(NC)"

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTHON) -m pytest tests/ web/server/tests/ -v --cov=quantumwerewolf --cov=web/server --cov-report=html

test-backend: ## Run backend tests only
	@echo "$(BLUE)Running backend tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=quantumwerewolf --cov-report=html

test-web: ## Run web server tests only
	@echo "$(BLUE)Running web server tests...$(NC)"
	$(PYTHON) -m pytest web/server/tests/ -v --cov=web/server --cov-report=html

test-coverage: ## Generate coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	$(PYTHON) -m pytest --cov=quantumwerewolf --cov=web/server --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated. Open htmlcov/index.html to view.$(NC)"

# Code Quality
lint: ## Run linters (flake8, pylint)
	@echo "$(BLUE)Running linters...$(NC)"
	flake8 quantumwerewolf/ web/server/ tests/ --max-line-length=120 --ignore=E501,W503
	pylint quantumwerewolf/ web/server/ --disable=R,C

format: ## Format code with black
	@echo "$(BLUE)Formatting code with black...$(NC)"
	black quantumwerewolf/ web/server/ tests/

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy quantumwerewolf/ web/server/ || true

# CLI Game
cli: ## Run CLI game
	@echo "$(BLUE)Starting Quantum Werewolf CLI...$(NC)"
	quantumwerewolf

# Web Server
web-run: ## Run web server (development)
	@echo "$(BLUE)Starting web server...$(NC)"
	cd web/server && $(PYTHON) -m uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000

web-run-prod: ## Run web server (production)
	@echo "$(BLUE)Starting web server (production)...$(NC)"
	cd web/server && $(PYTHON) -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --workers 4

# Docker Commands
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image: $(DOCKER_IMAGE):$(DOCKER_TAG)...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -t $(DOCKER_IMAGE):latest .
	@echo "$(GREEN)Docker image built successfully.$(NC)"

docker-run: docker-build ## Build and run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -d \
		--name $(DOCKER_IMAGE) \
		-p 8000:8000 \
		-e DEBUG=true \
		$(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)Container running. Access at http://localhost:8000$(NC)"

docker-stop: ## Stop Docker container
	@echo "$(BLUE)Stopping Docker container...$(NC)"
	docker stop $(DOCKER_IMAGE) || true
	docker rm $(DOCKER_IMAGE) || true
	@echo "$(GREEN)Container stopped and removed.$(NC)"

docker-logs: ## Show Docker container logs
	@echo "$(BLUE)Showing Docker logs...$(NC)"
	docker logs -f $(DOCKER_IMAGE)

docker-shell: ## Access Docker container shell
	@echo "$(BLUE)Accessing Docker container shell...$(NC)"
	docker exec -it $(DOCKER_IMAGE) /bin/bash

docker-push: ## Push Docker image to registry
	@echo "$(BLUE)Pushing Docker image to registry...$(NC)"
	@echo "$(YELLOW)Make sure you're logged in: docker login$(NC)"
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE):latest

# Docker Compose Commands
docker-compose-up: ## Start all services with docker-compose
	@echo "$(BLUE)Starting services with docker-compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started. Access web at http://localhost:8000$(NC)"
	docker-compose ps

docker-compose-down: ## Stop all services with docker-compose
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped.$(NC)"

docker-compose-logs: ## Show docker-compose logs
	@echo "$(BLUE)Showing logs...$(NC)"
	docker-compose logs -f

docker-compose-build: ## Build services with docker-compose
	@echo "$(BLUE)Building services...$(NC)"
	docker-compose build

# Cleaning
clean: ## Clean up generated files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete.$(NC)"

clean-docker: ## Clean up Docker images and containers
	@echo "$(BLUE)Cleaning up Docker...$(NC)"
	docker stop $(DOCKER_IMAGE) || true
	docker rm $(DOCKER_IMAGE) || true
	docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) || true
	docker rmi $(DOCKER_IMAGE):latest || true
	@echo "$(GREEN)Docker cleanup complete.$(NC)"

distclean: clean clean-docker ## Full cleanup
	@echo "$(GREEN)Full cleanup complete.$(NC)"

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd docs && make html || echo "Docs directory not found"
	@echo "$(GREEN)Documentation generated.$(NC)"

# Development Setup
setup-dev: venv install-dev ## Setup development environment
	@echo "$(GREEN)Development environment setup complete!$(NC)"
	@echo "$(YELLOW)Activate virtual environment with: source $(VENV)/bin/activate$(NC)"

# Quick checks
check: lint test ## Run linter and tests
	@echo "$(GREEN)All checks passed!$(NC)"

# Default target
.DEFAULT_GOAL := help

