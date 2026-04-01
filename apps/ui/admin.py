from __future__ import annotations

from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.core.admin_mixins import LocalizedModelAdminMixin

from .models import InterfaceConfiguration
from .registry import get_registered_styles, style_choices_for_admin


class InterfaceConfigurationAdminForm(forms.ModelForm):
    active_style = forms.ChoiceField(label=_("Активный глобальный стиль"), choices=())

    class Meta:
        model = InterfaceConfiguration
        fields = "__all__"
        widgets = {
            "public_site_title_translations": forms.Textarea(attrs={"rows": 4}),
            "public_site_tagline_translations": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["active_style"].choices = style_choices_for_admin()


@admin.register(InterfaceConfiguration)
class InterfaceConfigurationAdmin(LocalizedModelAdminMixin, ModelAdmin):
    form = InterfaceConfigurationAdminForm
    fieldsets = (
        (
            _("Идентичность сайта"),
            {
                "fields": (
                    "public_site_title",
                    "public_site_title_translations",
                    "public_site_tagline",
                    "public_site_tagline_translations",
                ),
            },
        ),
        (
            _("Глобальный стиль"),
            {
                "fields": ("active_style", "available_styles_overview"),
            },
        ),
        (
            _("Пользовательские предпочтения"),
            {
                "fields": (
                    "default_theme_mode",
                    "default_language",
                    "allow_user_theme_mode_switch",
                    "allow_user_language_switch",
                ),
            },
        ),
    )
    readonly_fields = ("available_styles_overview",)
    field_labels = {
        "public_site_title": _("Название публичного сайта"),
        "public_site_title_translations": _("Локализованные варианты названия сайта"),
        "public_site_tagline": _("Подзаголовок публичного сайта"),
        "public_site_tagline_translations": _("Локализованные варианты подзаголовка"),
        "active_style": _("Активный глобальный стиль"),
        "available_styles_overview": _("Доступные стили"),
        "default_theme_mode": _("Тема по умолчанию"),
        "default_language": _("Язык публичного интерфейса по умолчанию"),
        "allow_user_theme_mode_switch": _("Разрешить переключение темы"),
        "allow_user_language_switch": _("Разрешить переключение языка"),
    }

    def has_add_permission(self, request):
        if InterfaceConfiguration.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_("Доступные стили"))
    def available_styles_overview(self, obj):
        items = []
        for style in get_registered_styles():
            items.append(
                f"<li><strong>{style.label}</strong> — {style.identifier}<br>"
                f"<small>{style.description}</small><br><small>{style.preview_hint}</small></li>"
            )
        return mark_safe("<ul style='margin:0; padding-left:1.25rem;'>" + "".join(items) + "</ul>")
