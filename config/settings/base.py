from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parents[2]


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and ((value[0] == value[-1]) and value[0] in {'"', "'"}):
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_env_file(BASE_DIR / ".env")


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = env(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("SECRET_KEY", "django-insecure-change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "taggit",
    "modelcluster",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "apps.core",
    "apps.users",
    "apps.publications",
    "apps.collections_app",
    "apps.ingestion",
    "apps.search",
    "apps.vector_store",
    "apps.cms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = env("DATABASE_URL", "postgresql://repository:repository@localhost:5432/repository")
parsed = urlparse(database_url)
scheme = (parsed.scheme or "").lower()

if scheme in {"postgresql", "postgres"}:
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise ImproperlyConfigured("DATABASE_URL must include a database name.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(db_name),
            "USER": unquote(parsed.username or "repository"),
            "PASSWORD": unquote(parsed.password or "repository"),
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
elif scheme == "sqlite":
    sqlite_path = parsed.path or "/db.sqlite3"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / sqlite_path.lstrip("/")),
        }
    }
else:
    raise ImproperlyConfigured(
        "Unsupported DATABASE_URL scheme. Use postgresql://... for PostgreSQL or sqlite:///... for SQLite."
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / env("STATIC_ROOT", "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / env("MEDIA_ROOT", "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
AUTH_USER_MODEL = "users.User"

WAGTAIL_SITE_NAME = "Institutional Repository"
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", "http://localhost:8000")

SEARCH_PROFILE = env("SEARCH_PROFILE", "fast").strip().lower()
_profile_defaults = {
    "fast": {
        "candidate_pool": 60,
        "head_limit": 16,
        "rerank_enabled": False,
        "rerank_top_k": 12,
    },
    "quality": {
        "candidate_pool": 140,
        "head_limit": 24,
        "rerank_enabled": True,
        "rerank_top_k": 24,
    },
}
search_profile_defaults = _profile_defaults.get(SEARCH_PROFILE, _profile_defaults["fast"])

MILVUS_URI = env("MILVUS_URI", "http://localhost:19530")
MILVUS_COLLECTION = env("MILVUS_COLLECTION", "publications_chunks_hybrid_v1")
MILVUS_BGE_M3_MODEL = env("MILVUS_BGE_M3_MODEL", "BAAI/bge-m3")
MILVUS_DENSE_DIM = int(env("MILVUS_DENSE_DIM", "1024"))
MILVUS_DROP_RATIO_BUILD = float(env("MILVUS_DROP_RATIO_BUILD", "0.2"))
MILVUS_DROP_RATIO_SEARCH = float(env("MILVUS_DROP_RATIO_SEARCH", "0.15"))
MILVUS_CHUNK_TEXT_MAX_LENGTH = int(env("MILVUS_CHUNK_TEXT_MAX_LENGTH", "8192"))
MILVUS_CHUNK_CANDIDATE_POOL = int(env("MILVUS_CHUNK_CANDIDATE_POOL", str(search_profile_defaults["candidate_pool"])))
MILVUS_RRF_K = int(env("MILVUS_RRF_K", "60"))
MILVUS_HYBRID_DENSE_WEIGHT = float(env("MILVUS_HYBRID_DENSE_WEIGHT", "0.65"))
MILVUS_HYBRID_SPARSE_WEIGHT = float(env("MILVUS_HYBRID_SPARSE_WEIGHT", "0.35"))

VECTOR_CHUNK_MAX_WORDS = int(env("VECTOR_CHUNK_MAX_WORDS", "320"))
VECTOR_CHUNK_OVERLAP_WORDS = int(env("VECTOR_CHUNK_OVERLAP_WORDS", "40"))
VECTOR_CHUNK_MAX_CHARS = int(env("VECTOR_CHUNK_MAX_CHARS", "2200"))
INGESTION_MIN_TEXT_CHARS = int(env("INGESTION_MIN_TEXT_CHARS", "120"))
INGESTION_MIN_TEXT_WORDS = int(env("INGESTION_MIN_TEXT_WORDS", "25"))
UPLOAD_PREFILL_CONTENTS_MAX_CHARS = int(env("UPLOAD_PREFILL_CONTENTS_MAX_CHARS", "700"))

SEARCH_PAGE_SIZE = int(env("SEARCH_PAGE_SIZE", "10"))
SEARCH_CANDIDATE_POOL_SIZE = int(env("SEARCH_CANDIDATE_POOL_SIZE", "120"))
SEARCH_EXCERPT_CHARS = int(env("SEARCH_EXCERPT_CHARS", "260"))
SEARCH_KEYWORD_MIN_SCORE = int(env("SEARCH_KEYWORD_MIN_SCORE", "20"))
SEARCH_SEMANTIC_MIN_SCORE = float(env("SEARCH_SEMANTIC_MIN_SCORE", "0.2"))
SEARCH_HYBRID_MIN_SCORE = float(env("SEARCH_HYBRID_MIN_SCORE", "0.2"))
SEARCH_RERANK_ENABLED = env_bool("SEARCH_RERANK_ENABLED", bool(search_profile_defaults["rerank_enabled"]))
SEARCH_RERANK_MODEL = env("SEARCH_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
SEARCH_RERANK_TOP_K = int(env("SEARCH_RERANK_TOP_K", str(search_profile_defaults["rerank_top_k"])))
SEARCH_RERANK_MAX_TEXT_CHARS = int(env("SEARCH_RERANK_MAX_TEXT_CHARS", "1200"))
SEARCH_KEYWORD_RELATIVE_CUTOFF = float(env("SEARCH_KEYWORD_RELATIVE_CUTOFF", "0.0"))
SEARCH_SEMANTIC_RELATIVE_CUTOFF = float(env("SEARCH_SEMANTIC_RELATIVE_CUTOFF", "0.35"))
SEARCH_HYBRID_RELATIVE_CUTOFF = float(env("SEARCH_HYBRID_RELATIVE_CUTOFF", "0.4"))
SEARCH_WARMUP_ON_STARTUP = env_bool("SEARCH_WARMUP_ON_STARTUP", True)
SEARCH_WARMUP_INCLUDE_RERANK = env_bool("SEARCH_WARMUP_INCLUDE_RERANK", False)
SEARCH_WARMUP_LOAD_COLLECTION = env_bool("SEARCH_WARMUP_LOAD_COLLECTION", True)
MILVUS_QUERY_CACHE_SIZE = int(env("MILVUS_QUERY_CACHE_SIZE", "64"))
SEARCH_METADATA_ONLY_SCORE_FACTOR = float(env("SEARCH_METADATA_ONLY_SCORE_FACTOR", "0.88"))
SEARCH_FULLTEXT_SCORE_BONUS = float(env("SEARCH_FULLTEXT_SCORE_BONUS", "0.03"))
HYBRID_SEMANTIC_HEAD_LIMIT = int(env("HYBRID_SEMANTIC_HEAD_LIMIT", str(search_profile_defaults["head_limit"])))
SEARCH_REFERENCE_CHUNK_SCORE_FACTOR = float(env("SEARCH_REFERENCE_CHUNK_SCORE_FACTOR", "0.08"))
SEARCH_CROSS_SCRIPT_SCORE_FACTOR = float(env("SEARCH_CROSS_SCRIPT_SCORE_FACTOR", "0.42"))
SEARCH_ZERO_OVERLAP_CROSS_SCRIPT_FACTOR = float(env("SEARCH_ZERO_OVERLAP_CROSS_SCRIPT_FACTOR", "0.30"))
SEARCH_TOKEN_COVERAGE_BOOST = float(env("SEARCH_TOKEN_COVERAGE_BOOST", "0.18"))
SEARCH_TOC_CHUNK_SCORE_FACTOR = float(env("SEARCH_TOC_CHUNK_SCORE_FACTOR", "0.04"))
SEARCH_ZERO_GROUNDING_SCORE_FACTOR = float(env("SEARCH_ZERO_GROUNDING_SCORE_FACTOR", "0.26"))
SEARCH_HYBRID_ZERO_GROUNDING_SCORE_FACTOR = float(env("SEARCH_HYBRID_ZERO_GROUNDING_SCORE_FACTOR", "0.16"))
SEARCH_PARTIAL_GROUNDING_SCORE_FACTOR = float(env("SEARCH_PARTIAL_GROUNDING_SCORE_FACTOR", "0.72"))
SEARCH_EXACT_QUERY_GROUNDING_BOOST = float(env("SEARCH_EXACT_QUERY_GROUNDING_BOOST", "0.18"))
SEARCH_HYBRID_SEMANTIC_BLEND = float(env("SEARCH_HYBRID_SEMANTIC_BLEND", "0.58"))
SEARCH_HYBRID_KEYWORD_BLEND = float(env("SEARCH_HYBRID_KEYWORD_BLEND", "0.42"))
SEARCH_HYBRID_SEMANTIC_ONLY_FACTOR = float(env("SEARCH_HYBRID_SEMANTIC_ONLY_FACTOR", "0.58"))
SEARCH_SEMANTIC_EXACT_PHRASE_BOOST = float(env("SEARCH_SEMANTIC_EXACT_PHRASE_BOOST", "0.32"))
SEARCH_HYBRID_EXACT_PHRASE_BOOST = float(env("SEARCH_HYBRID_EXACT_PHRASE_BOOST", "0.44"))
VECTOR_CHUNK_MIN_INDEX_QUALITY = float(env("VECTOR_CHUNK_MIN_INDEX_QUALITY", "0.28"))
