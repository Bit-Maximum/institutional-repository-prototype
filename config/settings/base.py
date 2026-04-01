from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


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
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
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
    "apps.ui",
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
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.ui.middleware.InterfaceStateMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.ui.context_processors.ui_context",
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

LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", _("Русский")), ("en", _("Английский"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / env("STATIC_ROOT", "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / env("MEDIA_ROOT", "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_ADAPTER = "allauth.account.adapter.DefaultAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.RepositorySocialAccountAdapter"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_STORE_TOKENS = False

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", "") or ""
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", "") or ""
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
        "EMAIL_AUTHENTICATION": True,
        "EMAIL_AUTHENTICATION_AUTO_CONNECT": True,
        "APPS": (
            [
                {
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "key": "",
                    "settings": {
                        "scope": ["profile", "email"],
                        "auth_params": {"access_type": "online"},
                    },
                }
            ]
            if GOOGLE_OAUTH_ENABLED
            else []
        ),
    }
}

WAGTAIL_SITE_NAME = "Institutional Repository"
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", "http://localhost:8000")

UNFOLD = {
    "SITE_TITLE": _("Панель администратора репозитория"),
    "SITE_HEADER": _("Институциональный репозиторий"),
    "SITE_SUBHEADER": _("Администрирование прототипа ВКР"),
    "SITE_SYMBOL": "library_books",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
    "STYLES": [lambda request: static("admin/css/unfold_custom.css")],
    "SITE_DROPDOWN": [
        {
            "icon": "language",
            "title": _("Открыть публичный сайт"),
            "link": "/",
        },
        {
            "icon": "edit_document",
            "title": _("CMS-админка"),
            "link": "/cms-admin/",
            "permission": lambda request: request.user.is_staff,
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "10px",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Навигация"),
                "separator": True,
                "items": [
                    {
                        "title": _("Администрирование"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Статистика"),
                        "icon": "monitoring",
                        "link": reverse_lazy("admin:repository_statistics"),
                    },
                    {
                        "title": _("Публикации"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:publications_publication_changelist"),
                    },
                    {
                        "title": _("Пользователи"),
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Коллекции"),
                        "icon": "collections_bookmark",
                        "link": reverse_lazy("admin:collections_app_collection_changelist"),
                    },
                    {
                        "title": _("История поиска"),
                        "icon": "history",
                        "link": reverse_lazy("admin:search_searchquery_changelist"),
                    },
                    {
                        "title": _("Интерфейс сайта"),
                        "icon": "palette",
                        "link": reverse_lazy("admin:ui_interfaceconfiguration_changelist"),
                    },
                ],
            },
            {
                "title": _("Быстрые переходы"),
                "separator": True,
                "items": [
                    {
                        "title": _("Открыть сайт"),
                        "icon": "public",
                        "link": "/",
                    },
                    {
                        "title": _("CMS-админка"),
                        "icon": "web",
                        "link": "/cms-admin/",
                        "permission": lambda request: request.user.is_staff,
                    },
                    {
                        "title": _("Поиск на сайте"),
                        "icon": "search",
                        "link": "/search/",
                    },
                ],
            },
        ],
    },
}

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
MILVUS_BGE_M3_BATCH_SIZE = int(env("MILVUS_BGE_M3_BATCH_SIZE", "64"))
MILVUS_BGE_M3_DEVICE = env("MILVUS_BGE_M3_DEVICE", "auto")
MILVUS_BGE_M3_USE_FP16 = env_bool("MILVUS_BGE_M3_USE_FP16", True)
SEARCH_RERANK_DEVICE = env("SEARCH_RERANK_DEVICE", MILVUS_BGE_M3_DEVICE)
MILVUS_DENSE_DIM = int(env("MILVUS_DENSE_DIM", "1024"))
MILVUS_DROP_RATIO_BUILD = float(env("MILVUS_DROP_RATIO_BUILD", "0.2"))
MILVUS_DROP_RATIO_SEARCH = float(env("MILVUS_DROP_RATIO_SEARCH", "0.15"))
MILVUS_CHUNK_TEXT_MAX_LENGTH = int(env("MILVUS_CHUNK_TEXT_MAX_LENGTH", "8192"))
MILVUS_CHUNK_CANDIDATE_POOL = int(env("MILVUS_CHUNK_CANDIDATE_POOL", str(search_profile_defaults["candidate_pool"])))
MILVUS_UPSERT_BATCH_SIZE = int(env("MILVUS_UPSERT_BATCH_SIZE", "512"))
MILVUS_DELETE_BATCH_SIZE = int(env("MILVUS_DELETE_BATCH_SIZE", "64"))
MILVUS_RRF_K = int(env("MILVUS_RRF_K", "60"))
MILVUS_HYBRID_DENSE_WEIGHT = float(env("MILVUS_HYBRID_DENSE_WEIGHT", "0.65"))
MILVUS_HYBRID_SPARSE_WEIGHT = float(env("MILVUS_HYBRID_SPARSE_WEIGHT", "0.35"))

VECTOR_INDEX_SCHEMA_VERSION = env("VECTOR_INDEX_SCHEMA_VERSION", "2026-03-structural-retrieval-v1")
VECTOR_CHUNK_MAX_WORDS = int(env("VECTOR_CHUNK_MAX_WORDS", "320"))
VECTOR_CHUNK_OVERLAP_WORDS = int(env("VECTOR_CHUNK_OVERLAP_WORDS", "40"))
VECTOR_CHUNK_MAX_CHARS = int(env("VECTOR_CHUNK_MAX_CHARS", "2200"))
VECTOR_HEADING_MAX_WORDS = int(env("VECTOR_HEADING_MAX_WORDS", "14"))
VECTOR_ANCHOR_MAX_CHARS = int(env("VECTOR_ANCHOR_MAX_CHARS", "520"))
VECTOR_INDEX_INCLUDE_METADATA_ANCHOR = env_bool("VECTOR_INDEX_INCLUDE_METADATA_ANCHOR", True)
VECTOR_INDEX_MAX_EMBED_TEXTS = int(env("VECTOR_INDEX_MAX_EMBED_TEXTS", "512"))
VECTOR_REINDEX_PUBLICATION_BATCH_SIZE = int(env("VECTOR_REINDEX_PUBLICATION_BATCH_SIZE", "128"))
VECTOR_REINDEX_CHUNK_BATCH_SIZE = int(env("VECTOR_REINDEX_CHUNK_BATCH_SIZE", "1024"))
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
VECTOR_CHUNK_MIN_INFORMATION_DENSITY = float(env("VECTOR_CHUNK_MIN_INFORMATION_DENSITY", "0.24"))
SEARCH_BENCHMARK_RUNS = int(env("SEARCH_BENCHMARK_RUNS", "3"))
SEARCH_BENCHMARK_TOP_K = int(env("SEARCH_BENCHMARK_TOP_K", "5"))
SEARCH_BENCHMARK_LIMIT = int(env("SEARCH_BENCHMARK_LIMIT", "20"))
SEARCH_BENCHMARK_OUTPUT_DIR = env("SEARCH_BENCHMARK_OUTPUT_DIR", "var/search_benchmarks")
RECOMMENDATION_HISTORY_LIMIT = int(env("RECOMMENDATION_HISTORY_LIMIT", "5"))
RECOMMENDATION_PER_QUERY_LIMIT = int(env("RECOMMENDATION_PER_QUERY_LIMIT", "16"))
RECOMMENDATION_MAX_RESULTS = int(env("RECOMMENDATION_MAX_RESULTS", "50"))
RECOMMENDATION_RECENCY_DECAY = float(env("RECOMMENDATION_RECENCY_DECAY", "0.78"))
RECOMMENDATION_RELATIVE_FLOOR = env("RECOMMENDATION_RELATIVE_FLOOR", "0.4")
RECOMMENDATION_VIEWED_FACTOR = float(env("RECOMMENDATION_VIEWED_FACTOR", "0.78"))
RECOMMENDATION_DOWNLOADED_FACTOR = float(env("RECOMMENDATION_DOWNLOADED_FACTOR", "0.45"))
RECOMMENDATION_KEYWORD_FALLBACK_LIMIT = int(env("RECOMMENDATION_KEYWORD_FALLBACK_LIMIT", "4"))

RECOMMENDATION_CACHE_TIMEOUT = int(env("RECOMMENDATION_CACHE_TIMEOUT", "300"))
RECOMMENDATION_PRELOAD_PAGES = int(env("RECOMMENDATION_PRELOAD_PAGES", "2"))
RECOMMENDATION_ENTRY_CACHE_SEARCH_LIMIT = int(env("RECOMMENDATION_ENTRY_CACHE_SEARCH_LIMIT", "2"))
USER_ACTIVITY_VIEW_DEBOUNCE_MINUTES = int(env("USER_ACTIVITY_VIEW_DEBOUNCE_MINUTES", "30"))


SEARCH_WARMUP_RUN_QUERY = env("SEARCH_WARMUP_RUN_QUERY", "True").lower() == "true"
HEALTHCHECK_CHECK_VECTOR_STORE = env_bool("HEALTHCHECK_CHECK_VECTOR_STORE", True)
HEALTHCHECK_REQUIRE_WARMUP = env_bool("HEALTHCHECK_REQUIRE_WARMUP", True)
SEARCH_WARMUP_SAMPLE_QUERY = env("SEARCH_WARMUP_SAMPLE_QUERY", "поиск")


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "apps.vector_store.apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.vector_store.services": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
