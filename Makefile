.PHONY: dev db-up

dev: db-up
	@test -x .venv/bin/python || (echo "Создайте окружение: python -m venv .venv && .venv/bin/pip install -r requirements.txt" && exit 1)
	.venv/bin/python -m src.main

db-up:
	docker compose up -d db
	@echo "Ждём PostgreSQL..."
	@until docker compose exec -T db pg_isready -U petbot -d petbot >/dev/null 2>&1; do sleep 0.5; done
