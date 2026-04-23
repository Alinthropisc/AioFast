.PHONY: dev test lint bench loadtest migrate seed

dev:
	uv run python main.py

test:
	uv run pytest tests/ -v

lint:
	uvx ruff check . --fix
	uvx ruff format .

bench:
	uv run pytest benchmarks/ --benchmark-sort=mean -v

loadtest:
	uv run locust -f loadtests/locustfile.py

migrate:
	python -m aiocraft migrate:run

seed:
	python -m aiocraft db:seed

fresh:
	python -m aiocraft migrate:fresh --seed

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app