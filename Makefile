sync:
	uv sync

migrate:
	uv run python manage.py makemigrations
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

run:
	uv run python manage.py runserver

createsuperuser:
	uv run python manage.py createsuperuser

bootstrap:
	uv run python manage.py makemigrations
	uv run python manage.py migrate
	uv run python manage.py bootstrap_wagtail
	uv run python manage.py ensure_milvus_collection
