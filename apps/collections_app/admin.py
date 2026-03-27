from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.core.admin_mixins import LocalizedInlineMixin, LocalizedModelAdminMixin

from .models import COLLECTION_REACTION_CHOICES, Collection, CollectionPublication, CollectionReaction


class ReactionValueFilter(admin.SimpleListFilter):
    title = _("Оценка")
    parameter_name = "value"

    def lookups(self, request, model_admin):
        return list(COLLECTION_REACTION_CHOICES)

    def queryset(self, request, queryset):
        return queryset.filter(value=self.value()) if self.value() else queryset


class CollectionPublicationInline(LocalizedInlineMixin, TabularInline):
    model = CollectionPublication
    extra = 0
    show_count = True
    verbose_name_plural = _("Издания в коллекции")
    autocomplete_fields = ("publication",)
    field_labels = {"publication": _("Издание")}


class CollectionReactionInline(LocalizedInlineMixin, TabularInline):
    model = CollectionReaction
    extra = 0
    show_count = True
    verbose_name_plural = _("Реакции пользователей")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at_admin", "updated_at_admin")
    field_labels = {
        "user": _("Пользователь"),
        "value": _("Оценка"),
    }

    @display(description=_("Дата создания"))
    def created_at_admin(self, obj):
        return obj.created_at or "—"

    @display(description=_("Дата обновления"))
    def updated_at_admin(self, obj):
        return obj.updated_at or "—"


@admin.register(Collection)
class CollectionAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "author_display", "created_at_display", "updated_at_display")
    search_fields = ("name", "description", "author_user__full_name", "author_user__email")
    autocomplete_fields = ("author_user",)
    inlines = (CollectionPublicationInline, CollectionReactionInline)
    field_labels = {
        "name": _("Название коллекции"),
        "description": _("Описание"),
        "author_user": _("Автор коллекции"),
    }

    @display(description=_("Коллекция"), ordering="name")
    def name_display(self, obj):
        return obj.name

    @display(description=_("Автор коллекции"), ordering="author_user__full_name")
    def author_display(self, obj):
        return obj.author_user

    @display(description=_("Дата создания"), ordering="created_at")
    def created_at_display(self, obj):
        return obj.created_at or "—"

    @display(description=_("Дата обновления"), ordering="updated_at")
    def updated_at_display(self, obj):
        return obj.updated_at or "—"


@admin.register(CollectionReaction)
class CollectionReactionAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("collection_display", "user_display", "value_display", "updated_at_display")
    list_filter = (ReactionValueFilter,)
    search_fields = ("collection__name", "user__full_name", "user__email")
    autocomplete_fields = ("collection", "user")
    field_labels = {
        "collection": _("Коллекция"),
        "user": _("Пользователь"),
        "value": _("Оценка"),
    }

    @display(description=_("Коллекция"), ordering="collection__name")
    def collection_display(self, obj):
        return obj.collection

    @display(description=_("Пользователь"), ordering="user__full_name")
    def user_display(self, obj):
        return obj.user

    @display(description=_("Оценка"), label={"Лайк": "success", "Дизлайк": "danger"})
    def value_display(self, obj):
        return obj.get_value_display()

    @display(description=_("Дата обновления"), ordering="updated_at")
    def updated_at_display(self, obj):
        return obj.updated_at or "—"
