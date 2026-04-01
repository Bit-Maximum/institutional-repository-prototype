from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

from .models import (
    DEFAULT_PUBLIC_SITE_TAGLINE,
    DEFAULT_PUBLIC_SITE_TITLE,
    THEME_MODE_CHOICES,
    THEME_MODE_SYSTEM,
    InterfaceConfiguration,
)
from .registry import UiStyleDefinition, get_default_style, get_style, get_registered_styles

SESSION_THEME_MODE_KEY = "ui_theme_mode"
SESSION_LANGUAGE_KEY = "ui_language"


@dataclass(slots=True)
class ResolvedInterfaceState:
    config: InterfaceConfiguration
    style: UiStyleDefinition
    theme_mode: str
    language: str
    available_languages: list[tuple[str, str]]
    site_title: str
    site_tagline: str


def get_theme_mode_choices() -> list[tuple[str, str]]:
    return list(THEME_MODE_CHOICES)


def get_language_choices() -> list[tuple[str, str]]:
    return list(settings.LANGUAGES)


def normalize_theme_mode(value: str | None, fallback: str = THEME_MODE_SYSTEM) -> str:
    allowed = {key for key, _label in THEME_MODE_CHOICES}
    return value if value in allowed else fallback


def normalize_language(value: str | None, fallback: str) -> str:
    allowed = {key for key, _label in settings.LANGUAGES}
    return value if value in allowed else fallback


def resolve_interface_state(request) -> ResolvedInterfaceState:
    try:
        config = InterfaceConfiguration.get_solo()
    except Exception:
        config = SimpleNamespace(
            public_site_title=DEFAULT_PUBLIC_SITE_TITLE,
            public_site_title_translations={"en": "Institutional Repository"},
            public_site_tagline=DEFAULT_PUBLIC_SITE_TAGLINE,
            public_site_tagline_translations={
                "en": "Semantic search, collections, and intelligent recommendations"
            },
            active_style=get_default_style().identifier,
            default_theme_mode=THEME_MODE_SYSTEM,
            default_language=settings.LANGUAGE_CODE.split("-")[0],
            allow_user_theme_mode_switch=True,
            allow_user_language_switch=True,
            get_localized_site_value=lambda base_field, translations_field, language: {
                ("public_site_title", "ru"): _("Институциональный репозиторий"),
                ("public_site_title", "en"): "Institutional Repository",
                ("public_site_tagline", "ru"): _("Семантический поиск, коллекции и интеллектуальные рекомендации"),
                ("public_site_tagline", "en"): "Semantic search, collections, and intelligent recommendations",
            }.get((base_field, language), getattr(config, base_field, "")),
        )
    style = get_style(config.active_style) or get_default_style()

    theme_mode = config.default_theme_mode
    if config.allow_user_theme_mode_switch:
        if request.user.is_authenticated and getattr(request.user, "preferred_theme_mode", None):
            theme_mode = request.user.preferred_theme_mode
        else:
            theme_mode = request.session.get(SESSION_THEME_MODE_KEY, theme_mode)
    theme_mode = normalize_theme_mode(theme_mode, fallback=config.default_theme_mode)

    default_language = normalize_language(config.default_language, fallback=settings.LANGUAGE_CODE.split("-")[0])
    language = default_language
    if config.allow_user_language_switch:
        if request.user.is_authenticated and getattr(request.user, "preferred_language", None):
            language = request.user.preferred_language
        else:
            language = request.session.get(SESSION_LANGUAGE_KEY, language)
    language = normalize_language(language, fallback=default_language)

    with translation.override(language):
        site_title = config.get_localized_site_value("public_site_title", "public_site_title_translations", language)
        site_tagline = config.get_localized_site_value("public_site_tagline", "public_site_tagline_translations", language)

    return ResolvedInterfaceState(
        config=config,
        style=style,
        theme_mode=theme_mode,
        language=language,
        available_languages=get_language_choices(),
        site_title=site_title,
        site_tagline=site_tagline,
    )


def get_registered_style_payload() -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for style in get_registered_styles():
        payload.append(
            {
                "identifier": style.identifier,
                "label": str(style.label),
                "description": str(style.description),
                "preview_hint": str(style.preview_hint),
                "stylesheet_path": style.stylesheet_path,
            }
        )
    return payload
