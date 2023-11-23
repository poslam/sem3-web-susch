run:
	docker compose unpause api

stop:
	docker compose pause api

update:
	docker compose up -d --no-deps --build api
	docker compose exec -w /api api poetry run python -m alembic upgrade head

start:
	docker compose up --build -d
	docker compose exec -w /api api poetry run python -m alembic upgrade head