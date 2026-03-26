import logging

from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from apps.cms.models import AnnouncementPage
from apps.core.health import startup_state
from apps.publications.models import Publication


logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_publications"] = Publication.objects.filter(is_draft=False).order_by("-uploaded_at")[:5]
        context["latest_announcements"] = AnnouncementPage.objects.live().public().order_by("-first_published_at")[:5]
        return context


class HealthLiveView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "alive"})


class HealthReadyView(View):
    def get(self, request, *args, **kwargs):
        payload = {
            "status": "ready",
            "database": {"ok": False},
            "vector_store": {"ok": False},
            "startup": startup_state.snapshot(),
        }
        ready = True

        try:
            connection = connections["default"]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            payload["database"] = {
                "ok": True,
                "engine": connection.settings_dict.get("ENGINE", ""),
                "name": connection.settings_dict.get("NAME", ""),
            }
        except Exception as exc:
            ready = False
            payload["database"] = {"ok": False, "error": str(exc)}

        vector_check_enabled = bool(getattr(settings, "HEALTHCHECK_CHECK_VECTOR_STORE", True))
        if vector_check_enabled:
            try:
                from apps.vector_store.services import VectorStoreService

                service = VectorStoreService()
                collection_exists = bool(service.client.has_collection(service.collection_name))
                payload["vector_store"] = {
                    "ok": True,
                    "uri": service.uri,
                    "collection": service.collection_name,
                    "collection_exists": collection_exists,
                    "runtime": service.runtime_info(),
                }
            except Exception as exc:
                ready = False
                payload["vector_store"] = {"ok": False, "error": str(exc)}
        else:
            payload["vector_store"] = {"ok": True, "skipped": True}

        require_warmup = bool(getattr(settings, "HEALTHCHECK_REQUIRE_WARMUP", True))
        startup_snapshot = payload["startup"]
        if require_warmup and startup_snapshot.get("warmup_enabled"):
            if startup_snapshot.get("warmup_failed") or not startup_snapshot.get("warmup_completed"):
                ready = False

        if ready:
            payload["status"] = "ready"
            status_code = 200
        else:
            payload["status"] = "not_ready"
            status_code = 503
        return JsonResponse(payload, status=status_code)
