from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .registry import get_default_style, get_style, get_registered_styles


DEFAULT_PUBLIC_SITE_TITLE = "Институциональный репозиторий"
DEFAULT_PUBLIC_SITE_TAGLINE = "Семантический поиск, коллекции и интеллектуальные рекомендации"

THEME_MODE_SYSTEM = "system"
THEME_MODE_LIGHT = "light"
THEME_MODE_DARK = "dark"

THEME_MODE_CHOICES = [
    (THEME_MODE_SYSTEM, _("Следовать настройкам устройства")),
    (THEME_MODE_LIGHT, _("Светлая")),
    (THEME_MODE_DARK, _("Тёмная")),
]


class InterfaceConfiguration(TimeStampedModel):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    public_site_title = models.CharField(
        max_length=255,
        default=DEFAULT_PUBLIC_SITE_TITLE,
        verbose_name=_("Название публичного сайта"),
    )
    public_site_title_translations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Локализованные варианты названия сайта"),
        help_text=_(
            "Расширяемый словарь вида {'en': 'Institutional Repository'}. Если для выбранного языка записи нет, используется основное поле названия."
        ),
    )
    public_site_tagline = models.CharField(
        max_length=255,
        blank=True,
        default=DEFAULT_PUBLIC_SITE_TAGLINE,
        verbose_name=_("Подзаголовок публичного сайта"),
    )
    public_site_tagline_translations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Локализованные варианты подзаголовка"),
        help_text=_(
            "Расширяемый словарь вида {'en': 'Semantic search, collections, and intelligent recommendations'}."
        ),
    )
    active_style = models.CharField(
        max_length=64,
        default="academic",
        verbose_name=_("Активный глобальный стиль"),
        help_text=_(
            "Определяет базовый визуальный стиль всего публичного сайта. Новые стили можно добавлять через реестр apps.ui.registry."
        ),
    )
    default_theme_mode = models.CharField(
        max_length=16,
        choices=THEME_MODE_CHOICES,
        default=THEME_MODE_SYSTEM,
        verbose_name=_("Тема по умолчанию"),
    )
    default_language = models.CharField(
        max_length=16,
        default="ru",
        verbose_name=_("Язык публичного интерфейса по умолчанию"),
    )
    allow_user_theme_mode_switch = models.BooleanField(
        default=True,
        verbose_name=_("Разрешить пользователям переключать светлую/тёмную тему"),
    )
    allow_user_language_switch = models.BooleanField(
        default=True,
        verbose_name=_("Разрешить пользователям переключать язык интерфейса"),
    )

    class Meta:
        verbose_name = _("Конфигурация публичного интерфейса")
        verbose_name_plural = _("Конфигурация публичного интерфейса")

    def __str__(self) -> str:
        return self.public_site_title

    def clean(self):
        super().clean()
        if get_style(self.active_style) is None:
            available = ", ".join(style.identifier for style in get_registered_styles())
            raise ValidationError({
                "active_style": _(
                    "Неизвестный стиль интерфейса. Доступные идентификаторы: %(available)s"
                )
                % {"available": available}
            })

        valid_languages = {code for code, _label in settings.LANGUAGES}
        if self.default_language not in valid_languages:
            raise ValidationError({
                "default_language": _(
                    "Язык должен входить в список LANGUAGES проекта."
                )
            })

        for field_name in ("public_site_title_translations", "public_site_tagline_translations"):
            payload = getattr(self, field_name) or {}
            if not isinstance(payload, dict):
                raise ValidationError({field_name: _("Поле должно содержать JSON-объект с языковыми кодами и строками.")})
            invalid_codes = sorted(code for code in payload.keys() if code not in valid_languages)
            if invalid_codes:
                raise ValidationError({
                    field_name: _("Недопустимые языковые коды: %(codes)s") % {"codes": ", ".join(invalid_codes)}
                })

    def save(self, *args, **kwargs):
        self.singleton_key = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def active_style_definition(self):
        return get_style(self.active_style) or get_default_style()

    def get_localized_site_value(self, base_field: str, translations_field: str, language: str) -> str:
        translations = getattr(self, translations_field, None) or {}
        localized_value = translations.get(language) or translations.get(language.split("-")[0])
        if localized_value:
            return str(localized_value)

        raw_value = getattr(self, base_field, "") or ""
        if base_field == "public_site_title" and raw_value == DEFAULT_PUBLIC_SITE_TITLE:
            return str(_("Институциональный репозиторий"))
        if base_field == "public_site_tagline" and raw_value == DEFAULT_PUBLIC_SITE_TAGLINE:
            return str(_("Семантический поиск, коллекции и интеллектуальные рекомендации"))
        return str(raw_value)

    @classmethod
    def get_solo(cls) -> "InterfaceConfiguration":
        obj, _created = cls.objects.get_or_create(
            singleton_key=1,
            defaults={
                "public_site_title": DEFAULT_PUBLIC_SITE_TITLE,
                "public_site_tagline": DEFAULT_PUBLIC_SITE_TAGLINE,
                "public_site_title_translations": {"en": "Institutional Repository"},
                "public_site_tagline_translations": {
                    "en": "Semantic search, collections, and intelligent recommendations"
                },
                "active_style": get_default_style().identifier,
                "default_theme_mode": THEME_MODE_SYSTEM,
                "default_language": settings.LANGUAGE_CODE.split("-")[0],
            },
        )
        return obj
