from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from .models import THEME_MODE_SYSTEM, InterfaceConfiguration
from .services import (
    SESSION_LANGUAGE_KEY,
    SESSION_THEME_MODE_KEY,
    get_language_choices,
    normalize_language,
    normalize_theme_mode,
)


class PreferenceRedirectMixin:
    fallback_redirect_name = "home"

    def get_next_url(self, request) -> str:
        candidate = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER", "")
        if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return candidate
        return self.fallback_redirect_name

    def redirect_back(self, request):
        target = self.get_next_url(request)
        if target == self.fallback_redirect_name:
            return redirect(self.fallback_redirect_name)
        return redirect(target)


class SetThemeModeView(PreferenceRedirectMixin, View):
    def post(self, request, *args, **kwargs):
        config = InterfaceConfiguration.get_solo()
        if not config.allow_user_theme_mode_switch:
            messages.warning(request, _("Переключение темы сейчас отключено администратором."))
            return self.redirect_back(request)

        value = normalize_theme_mode(request.POST.get("theme_mode"), fallback=THEME_MODE_SYSTEM)
        request.session[SESSION_THEME_MODE_KEY] = value
        if request.user.is_authenticated:
            request.user.preferred_theme_mode = value
            request.user.save(update_fields=["preferred_theme_mode"])
        messages.success(request, _("Настройка темы интерфейса обновлена."))
        return self.redirect_back(request)


class SetLanguageView(PreferenceRedirectMixin, View):
    def post(self, request, *args, **kwargs):
        config = InterfaceConfiguration.get_solo()
        if not config.allow_user_language_switch:
            messages.warning(request, _("Переключение языка сейчас отключено администратором."))
            return self.redirect_back(request)

        default_language = settings.LANGUAGE_CODE.split("-")[0]
        allowed = {code for code, _label in get_language_choices()}
        value = request.POST.get("language")
        value = normalize_language(value if value in allowed else None, fallback=default_language)
        request.session[SESSION_LANGUAGE_KEY] = value
        request.session["django_language"] = value
        if request.user.is_authenticated:
            request.user.preferred_language = value
            request.user.save(update_fields=["preferred_language"])
        messages.success(request, _("Язык интерфейса обновлён."))
        return self.redirect_back(request)
