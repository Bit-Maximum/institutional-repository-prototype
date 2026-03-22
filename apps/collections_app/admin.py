from django.contrib import admin

from .models import Collection, CollectionItem


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 1


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_public")
    search_fields = ("name", "description")
    inlines = [CollectionItemInline]
