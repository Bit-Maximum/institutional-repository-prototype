from __future__ import annotations

import logging
import os
import sys
import threading

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class VectorStoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vector_store"
    verbose_name = "Vector Store"

    _warmup_started = False

    def ready(self):
        from django.conf import settings

        if self.__class__._warmup_started:
            return
        if not getattr(settings, "SEARCH_WARMUP_ON_STARTUP", False):
            return

        command = sys.argv[1] if len(sys.argv) > 1 else ""
        if command and command not in {"runserver", "gunicorn", "uwsgi", "daphne"}:
            return
        if command == "runserver" and os.environ.get("RUN_MAIN") != "true":
            return

        self.__class__._warmup_started = True

        def _warmup() -> None:
            try:
                from apps.vector_store.services import VectorStoreService

                service = VectorStoreService()
                if getattr(settings, "SEARCH_WARMUP_LOAD_COLLECTION", True):
                    service.ensure_collection()
                service.warmup(
                    include_reranker=getattr(settings, "SEARCH_WARMUP_INCLUDE_RERANK", False),
                    run_query=getattr(settings, "SEARCH_WARMUP_RUN_QUERY", True),
                )
                logger.info("Search warmup completed: %s", service.runtime_info())
            except Exception:  # pragma: no cover - best effort warmup
                logger.exception("Search warmup failed")

        threading.Thread(target=_warmup, name="search-warmup", daemon=True).start()
