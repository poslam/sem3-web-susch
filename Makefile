run:
	docker compose unpause api

stop:
	docker compose pause api

update:
	docker compose up -d --no-deps --build api

start:
	docker compose up --build -d