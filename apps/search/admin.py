from django.contrib import admin

from .models import SearchQuery


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("query_text", "user", "filters")
    search_fields = ("query_text", "filters", "user__email", "user__full_name")
