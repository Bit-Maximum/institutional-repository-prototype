from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_mixins import LocalizedModelAdminMixin

from .models import SearchQuery


@admin.register(SearchQuery)
class SearchQueryAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("query_text_display", "user_display", "filters_display", "created_at_display")
    search_fields = ("query_text", "filters", "user__email", "user__full_name")
    field_labels = {
        "query_text": _("Текст запроса"),
        "query_topic": _("Тема запроса"),
        "filters": _("Фильтры поиска"),
        "user": _("Пользователь"),
    }

    @display(description=_("Поисковый запрос"), ordering="query_text")
    def query_text_display(self, obj):
        return obj.query_text

    @display(description=_("Пользователь"), ordering="user__full_name")
    def user_display(self, obj):
        return obj.user

    @display(description=_("Фильтры"))
    def filters_display(self, obj):
        return obj.filters or "—"

    @display(description=_("Дата и время"), ordering="created_at")
    def created_at_display(self, obj):
        return obj.created_at or "—"
