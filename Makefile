run:
	docker compose unpause api

stop:
	docker compose pause api

update-pkgs:
	docker compose exec -w /api api pip install -r requirements.txt

update-api:
	docker compose cp ./api api:.

start:
	docker compose up --build -d