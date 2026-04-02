#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[entrypoint] %s\n' "$*"
}

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local name="$3"
  local timeout="${4:-180}"
  local started_at
  started_at="$(date +%s)"

  while ! python - "$host" "$port" <<'PY'
import socket, sys
host = sys.argv[1]
port = int(sys.argv[2])
with socket.create_connection((host, port), timeout=2):
    pass
PY
  do
    local now elapsed
    now="$(date +%s)"
    elapsed=$((now - started_at))
    if [ "$elapsed" -ge "$timeout" ]; then
      log "Timed out while waiting for ${name}."
      exit 1
    fi
    sleep 2
  done

  log "${name} is reachable."
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local timeout="${3:-240}"
  local started_at
  started_at="$(date +%s)"

  until curl --silent --show-error --fail "$url" >/dev/null 2>&1; do
    local now elapsed
    now="$(date +%s)"
    elapsed=$((now - started_at))
    if [ "$elapsed" -ge "$timeout" ]; then
      log "Timed out while waiting for ${name}."
      exit 1
    fi
    sleep 3
  done

  log "${name} is healthy."
}

parse_database_target() {
  python - <<'PY'
from urllib.parse import urlparse
import os
url = os.environ.get('DATABASE_URL', '')
parsed = urlparse(url)
print(parsed.hostname or 'db')
print(parsed.port or 5432)
PY
}

if [ -n "${DATABASE_URL:-}" ]; then
  readarray -t _db_target < <(parse_database_target)
  wait_for_tcp "${_db_target[0]}" "${_db_target[1]}" "PostgreSQL"
fi

if [ -n "${MILVUS_HEALTHCHECK_URL:-}" ]; then
  wait_for_url "$MILVUS_HEALTHCHECK_URL" "Milvus"
fi

mkdir -p "${STATIC_ROOT:-/app/staticfiles}" "${MEDIA_ROOT:-/app/media}" /app/var/search_benchmarks

if [ "${AUTO_MIGRATE:-1}" = "1" ]; then
  log "Applying database migrations..."
  python manage.py migrate --noinput
fi

if [ "${AUTO_COLLECTSTATIC:-1}" = "1" ]; then
  log "Collecting static files..."
  python manage.py collectstatic --noinput
fi

if [ "${AUTO_BOOTSTRAP_WAGTAIL:-1}" = "1" ]; then
  log "Bootstrapping Wagtail structure..."
  python manage.py bootstrap_wagtail
fi

if [ "${AUTO_ENSURE_MILVUS_COLLECTION:-1}" = "1" ]; then
  log "Ensuring Milvus collection exists..."
  python manage.py ensure_milvus_collection
fi

if [ "${AUTO_CREATE_SUPERUSER:-0}" = "1" ] || { [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; }; then
  log "Ensuring Django superuser exists..."
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
full_name = os.environ.get('DJANGO_SUPERUSER_FULL_NAME', 'Administrator')

if email and password:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'full_name': full_name,
            'is_staff': True,
            'is_superuser': True,
            'is_admin': True,
        },
    )
    changed = False
    if created:
        user.set_password(password)
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    if hasattr(user, 'is_admin') and not user.is_admin:
        user.is_admin = True
        changed = True
    if changed:
        user.save()
PY
fi

if [ "${RUN_DEPLOY_CHECK:-0}" = "1" ]; then
  log "Running Django deployment checks..."
  python manage.py check --deploy --fail-level WARNING
fi

log "Starting application process: $*"
exec "$@"
