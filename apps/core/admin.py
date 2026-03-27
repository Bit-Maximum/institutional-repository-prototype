from __future__ import annotations

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _

from apps.core.dashboard import build_dashboard_context


def repository_statistics_view(request):
    context = {
        **admin.site.each_context(request),
        "title": _("Статистика репозитория"),
        "subtitle": _("Сводка использования и состояния системы"),
    }
    context.update(build_dashboard_context())
    request.current_app = admin.site.name
    return TemplateResponse(request, "admin/statistics_dashboard.html", context)


_original_get_urls = admin.site.get_urls


def _get_urls():
    return [
        path(
            "statistics/",
            admin.site.admin_view(repository_statistics_view),
            name="repository_statistics",
        ),
        *_original_get_urls(),
    ]


admin.site.get_urls = _get_urls
