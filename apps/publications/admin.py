from django.contrib import admin

from .models import Author, Publication, PublicationType


@admin.register(PublicationType)
class PublicationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "affiliation")
    search_fields = ("full_name", "email", "affiliation")


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "publication_type", "status", "vector_state", "is_public")
    list_filter = ("status", "vector_state", "is_public", "publication_type")
    search_fields = ("title", "abstract")
    filter_horizontal = ("authors",)
