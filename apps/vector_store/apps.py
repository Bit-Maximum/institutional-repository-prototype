from __future__ import annotations

import logging
import os
import sys
import threading

from django.apps import AppConfig

from apps.core.health import startup_state


logger = logging.getLogger(__name__)


class VectorStoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vector_store"
    verbose_name = "Векторное хранилище"

    _warmup_started = False

    def ready(self):
        from django.conf import settings

        warmup_enabled = bool(getattr(settings, "SEARCH_WARMUP_ON_STARTUP", False))
        startup_state.configure(warmup_enabled=warmup_enabled)

        if self.__class__._warmup_started:
            return
        if not warmup_enabled:
            if not startup_state.mark_ready_logged():
                logger.info("Application startup completed. Prototype is ready to use. Search warmup is disabled.")
            return

        command = sys.argv[1] if len(sys.argv) > 1 else ""
        if command and command not in {"runserver", "gunicorn", "uwsgi", "daphne"}:
            return
        if command == "runserver" and os.environ.get("RUN_MAIN") != "true":
            return

        self.__class__._warmup_started = True

        def _warmup() -> None:
            startup_state.mark_warmup_started()
            try:
                from apps.vector_store.services import VectorStoreService

                service = VectorStoreService()
                if getattr(settings, "SEARCH_WARMUP_LOAD_COLLECTION", True):
                    service.ensure_collection()
                service.warmup(
                    include_reranker=getattr(settings, "SEARCH_WARMUP_INCLUDE_RERANK", False),
                    run_query=getattr(settings, "SEARCH_WARMUP_RUN_QUERY", True),
                )
                startup_state.mark_warmup_completed()
                logger.info("Search warmup completed: %s", service.runtime_info())
                if not startup_state.mark_ready_logged():
                    logger.info("Application startup completed. Prototype is ready to use.")
            except Exception as exc:  # pragma: no cover - best effort warmup
                startup_state.mark_warmup_failed(str(exc))
                logger.exception("Search warmup failed")

        threading.Thread(target=_warmup, name="search-warmup", daemon=True).start()
