dev:
	docker compose -f infra/docker/docker-compose.yml up --build
test:
	docker compose exec api pytest
format:
	docker compose exec api poetry run black .
lint:
	docker compose exec api poetry run flake8 .
scale:
	docker compose -f infra/docker/docker-compose.yml up --scale worker=$(N)
audit:
	poetry run python scripts/audit_completeness.py
