from django.contrib import admin

from .models import Collection, CollectionPublication


class CollectionPublicationInline(admin.TabularInline):
    model = CollectionPublication
    extra = 1


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "author_user")
    search_fields = ("name", "author_user__email", "author_user__full_name")
    inlines = [CollectionPublicationInline]
