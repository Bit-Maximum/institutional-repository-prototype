import logging

from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views import View
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from apps.cms.models import AnnouncementPage
from apps.core.health import startup_state
from apps.publications.models import Publication
from apps.publications.previews import ensure_publication_previews
from apps.collections_app.models import Collection
from apps.search.models import SearchQuery


logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_publications = list(
            Publication.objects.filter(is_draft=False)
            .select_related("publication_subtype", "publication_subtype__publication_type", "language")
            .prefetch_related("authors", "keywords", "chunks")
            .order_by("-uploaded_at")[:8]
        )
        ensure_publication_previews(latest_publications)
        context["latest_publications"] = latest_publications[:4]
        context["featured_publications"] = latest_publications
        context["latest_announcements"] = AnnouncementPage.objects.live().public().order_by("-first_published_at")[:4]
        context["home_metrics"] = [
            {"label": _("Изданий"), "value": Publication.objects.filter(is_draft=False).count()},
            {"label": _("Проиндексировано"), "value": Publication.objects.filter(is_draft=False, vector_indexed_at__isnull=False).count()},
            {"label": _("Публичных коллекций"), "value": Collection.objects.count()},
            {"label": _("Сигналов поиска"), "value": SearchQuery.objects.count()},
        ]
        context["capability_cards"] = [
            {
                "title": _("Гибридный поиск"),
                "text": _("Комбинирует традиционный поиск по метаданным и семантическое сопоставление текста, чтобы находить материалы не только по ключевым словам, но и по смыслу."),
            },
            {
                "title": _("Превью и карточки изданий"),
                "text": _("Система автоматически формирует визуальные превью: по первой странице PDF, загруженному изображению или на основе аккуратной сгенерированной обложки."),
            },
            {
                "title": _("Рекомендации для читателя"),
                "text": _("Рекомендательная лента использует историю поисковых запросов, учитывает новизну интересов и снижает вес уже просмотренных материалов."),
            },
            {
                "title": _("Гибкий интерфейс"),
                "text": _("Глобальный стиль задаётся администратором, а пользователь дополнительно переключает тему и язык интерфейса без перезагрузки логики системы."),
            },
        ]
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
