FROM python:3.13-slim-bookworm

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN python - <<'PY' > /tmp/requirements.txt
from pathlib import Path
import tomllib

project = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
deps = project['project']['dependencies']
filtered = [dep for dep in deps if not dep.startswith('torch')]
filtered.append('gunicorn>=23,<24')
Path('/tmp/requirements.txt').write_text('\n'.join(filtered) + '\n', encoding='utf-8')
print('\n'.join(filtered))
PY

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /tmp/requirements.txt \
    && python -m pip install --index-url "${TORCH_INDEX_URL}" 'torch>=2.11,<2.12'

COPY . /app

RUN addgroup --system app && adduser --system --ingroup app --home /app app \
    && mkdir -p /app/staticfiles /app/media /app/var/search_benchmarks \
    && chown -R app:app /app \
    && chmod +x /app/docker/entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/docker/gunicorn.conf.py", "config.wsgi:application"]
