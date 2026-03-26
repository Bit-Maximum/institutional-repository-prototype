from django.contrib import admin

from .models import Collection, CollectionPublication, CollectionReaction


class CollectionPublicationInline(admin.TabularInline):
    model = CollectionPublication
    extra = 0
    autocomplete_fields = ("publication",)


class CollectionReactionInline(admin.TabularInline):
    model = CollectionReaction
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "author_user", "created_at", "updated_at")
    search_fields = ("name", "description", "author_user__username")
    autocomplete_fields = ("author_user",)
    inlines = (CollectionPublicationInline, CollectionReactionInline)


@admin.register(CollectionReaction)
class CollectionReactionAdmin(admin.ModelAdmin):
    list_display = ("collection", "user", "value", "updated_at")
    list_filter = ("value",)
    search_fields = ("collection__name", "user__username")
    autocomplete_fields = ("collection", "user")
