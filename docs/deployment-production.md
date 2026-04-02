# Production deployment in Docker

This project ships with a complete container stack for public deployment:

- Django + Gunicorn application container
- Nginx reverse proxy
- PostgreSQL
- Milvus + etcd + MinIO
- shared volumes for static files, media, and application data

## Files

- `Dockerfile`
- `docker-compose.prod.yml`
- `.env.production.example`
- `docker/entrypoint.sh`
- `docker/gunicorn.conf.py`
- `docker/nginx/nginx.conf`
- `docker/nginx/default.conf`

## Quick start

1. Copy the environment template:

   ```bash
   cp .env.production.example .env.production
   ```

2. Fill in at least these values:

   - `SECRET_KEY`
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
   - `POSTGRES_PASSWORD`
   - `DJANGO_SUPERUSER_EMAIL`
   - `DJANGO_SUPERUSER_PASSWORD`
   - `WAGTAILADMIN_BASE_URL`

3. Build and start the stack:

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

4. Watch the startup logs:

   ```bash
   docker compose -f docker-compose.prod.yml logs -f web nginx
   ```

5. Open the application on your server domain or public IP.

## What the entrypoint does

On container startup the Django web service can automatically:

- wait for PostgreSQL
- wait for Milvus health
- apply migrations
- collect static files
- bootstrap the Wagtail site structure
- ensure the Milvus collection exists
- optionally create the initial superuser

These behaviors are controlled by environment variables in `.env.production`.

## Public internet access

By default, the stack publishes Nginx on port `80`.

For a real public deployment, put it behind HTTPS termination:

- your own reverse proxy / load balancer
- Nginx Proxy Manager
- Traefik
- Caddy
- cloud load balancer

If HTTPS is terminated before Django, keep `USE_X_FORWARDED_HOST=True` and set `CSRF_TRUSTED_ORIGINS` to your public HTTPS origins.

## TLS / secure cookies

When the application is actually served over HTTPS, turn on:

- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`

Enable HSTS only after HTTPS is configured and working correctly:

- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`

## GPU deployment (optional)

The production stack defaults to CPU-friendly PyTorch wheels.

If you deploy to a GPU-enabled Linux server, you can switch to CUDA wheels in `.env.production`:

```env
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
MILVUS_BGE_M3_DEVICE=cuda:0
SEARCH_RERANK_DEVICE=cuda:0
MILVUS_BGE_M3_USE_FP16=True
SEARCH_RERANK_ENABLED=True
```

You may also need to add Docker GPU runtime settings depending on your server and Docker installation.

## Typical maintenance commands

Rebuild after changes:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Run migrations manually:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

Rebuild static files manually:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

Re-bootstrap Wagtail:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py bootstrap_wagtail
```

Ensure Milvus collection:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py ensure_milvus_collection
```

Force preview generation:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py generate_publication_previews --force
```

## Backups

You should back up at least:

- PostgreSQL volume
- media volume
- Milvus volumes
- `.env.production`

For named volumes, export them regularly from the server or attach them to your standard backup system.
