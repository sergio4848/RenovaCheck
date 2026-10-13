# Convenience targets; each one is a thin wrapper around docker compose (see README.md).
# Layout adapted from careos/Makefile — Copyright (c) 2026 Sergen Şahin.
.PHONY: help env up down reset logs ps seed migrate data-dir synth test test-web test-extract test-synth lint lint-web lint-extract lint-synth

COMPOSE ?= docker compose
TEST_DB_ENV = -e DB_DATABASE=renova_test -e DB_USERNAME=renova_owner -e DB_PASSWORD=$${RENOVA_OWNER_PASSWORD}

help:          ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

env: .env      ## Create .env from .env.example with a fresh APP_KEY

.env:
	@cp .env.example .env
	@key="base64:$$(openssl rand -base64 32)"; sed -i.bak "s|^APP_KEY=.*|APP_KEY=$$key|" .env && rm -f .env.bak
	@echo "Created .env (development defaults)."

up: .env       ## Build and start the stack, wait until healthy
	$(COMPOSE) up -d --build --wait

down:          ## Stop the stack (data volumes are kept)
	$(COMPOSE) down

reset:         ## Stop the stack and DELETE database, redis and object-storage volumes
	@echo "This deletes all local RenovaCheck data (volumes pgdata, redisdata, miniodata)."
	@read -p "Type 'yes' to continue: " answer && [ "$$answer" = "yes" ]
	$(COMPOSE) down --volumes

logs:          ## Follow application logs
	$(COMPOSE) logs -f web queue extract worker

ps:            ## Show service status
	$(COMPOSE) ps

migrate:       ## Apply database migrations
	$(COMPOSE) run --rm migrate php artisan migrate --database=migrator --force

seed:          ## Re-run the idempotent demo seed
	$(COMPOSE) run --rm migrate php artisan db:seed --database=migrator --force

# Created by the invoking user before any bind mount, so containers running as that user can write.
data-dir:
	@mkdir -p data

synth: data-dir  ## Generate 20 synthetic cases into data/synth and validate them
	HOST_UID=$$(id -u) HOST_GID=$$(id -g) $(COMPOSE) run --rm --build synth

test: test-web test-extract test-synth  ## Run all test suites inside the containers

test-web:      ## Laravel tests against PostgreSQL (renova_test) with RLS active
	set -a; . ./.env; set +a; $(COMPOSE) run --rm --no-deps $(TEST_DB_ENV) web php artisan test

test-extract:  ## Python unit tests
	$(COMPOSE) run --rm --no-deps extract pytest -q -p no:cacheprovider

test-synth: data-dir  ## Synthetic generator tests (determinism, schema, bbox provenance)
	HOST_UID=$$(id -u) HOST_GID=$$(id -g) $(COMPOSE) run --rm --build --workdir /src --entrypoint pytest synth -q -p no:cacheprovider

lint: lint-web lint-extract lint-synth  ## Static checks

lint-web:
	$(COMPOSE) run --rm --no-deps web vendor/bin/pint --test

lint-extract:
	$(COMPOSE) run --rm --no-deps extract sh -c "ruff check --no-cache . && ruff format --check --no-cache . && mypy --cache-dir=/tmp/mypy"

lint-synth: data-dir
	$(COMPOSE) run --rm --build --workdir /src --entrypoint sh synth -c "ruff check --no-cache . && ruff format --check --no-cache . && mypy --cache-dir=/tmp/mypy"
