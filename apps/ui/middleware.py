from __future__ import annotations

from django.conf import settings
from django.utils import translation

from .services import resolve_interface_state


class InterfaceStateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.interface_state = resolve_interface_state(request)

        path = request.path or ""
        if path.startswith("/admin/") or path.startswith("/cms-admin/"):
            admin_language = settings.LANGUAGE_CODE.split("-")[0]
            translation.activate(admin_language)
            request.LANGUAGE_CODE = admin_language
        else:
            translation.activate(request.interface_state.language)
            request.LANGUAGE_CODE = request.interface_state.language

        response = self.get_response(request)
        response.headers.setdefault("Content-Language", getattr(request, "LANGUAGE_CODE", translation.get_language() or "ru"))
        return response
