.PHONY: run get_key


run:
	docker compose up -d --build

get_key:
	poetry run python ./src/bot/core/utils/secret_key_generator.py
