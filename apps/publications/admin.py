from django.contrib import admin

from .models import (
    AcademicDegree,
    Author,
    Bibliography,
    Copyright,
    CopyrightAuthor,
    CopyrightPublisher,
    GraphicEdition,
    Keyword,
    Publication,
    PublicationChunk,
    PublicationLanguage,
    PublicationPeriodicity,
    PublicationPlace,
    PublicationSubtype,
    PublicationType,
    Publisher,
    ScientificSupervisor,
)


class CopyrightAuthorInline(admin.TabularInline):
    model = CopyrightAuthor
    extra = 1
    autocomplete_fields = ("author",)


class CopyrightPublisherInline(admin.TabularInline):
    model = CopyrightPublisher
    extra = 1
    autocomplete_fields = ("publisher",)


@admin.register(PublicationType)
class PublicationTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(PublicationSubtype)
class PublicationSubtypeAdmin(admin.ModelAdmin):
    list_display = ("name", "publication_type")
    list_filter = ("publication_type",)
    search_fields = ("name", "publication_type__name")


@admin.register(PublicationLanguage)
class PublicationLanguageAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(PublicationPeriodicity)
class PublicationPeriodicityAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(AcademicDegree)
class AcademicDegreeAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "academic_degree", "position")
    search_fields = ("full_name", "position", "author_mark")
    list_filter = ("academic_degree",)


@admin.register(ScientificSupervisor)
class ScientificSupervisorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "academic_degree", "position")
    search_fields = ("full_name", "position")
    list_filter = ("academic_degree",)


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(PublicationPlace)
class PublicationPlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
    search_fields = ("name", "address")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
    search_fields = ("name", "address")


@admin.register(Copyright)
class CopyrightAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
    search_fields = ("name", "address")
    inlines = (CopyrightAuthorInline, CopyrightPublisherInline)


@admin.register(Bibliography)
class BibliographyAdmin(admin.ModelAdmin):
    search_fields = ("bibliographic_description",)


@admin.register(GraphicEdition)
class GraphicEditionAdmin(admin.ModelAdmin):
    list_display = ("name", "document_link")
    search_fields = ("name", "document_link")


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "publication_type_display", "publication_year", "language", "text_extraction_status", "is_draft")
    list_filter = ("is_draft", "publication_subtype", "language", "periodicity", "text_extraction_status")
    search_fields = ("title", "contents", "grif_text", "grant_text", "text_extraction_notes")
    readonly_fields = ("file_extension", "text_extraction_status", "text_extraction_notes", "has_extracted_text")

    @admin.display(description="Тип издания")
    def publication_type_display(self, obj):
        return obj.publication_type


@admin.register(PublicationChunk)
class PublicationChunkAdmin(admin.ModelAdmin):
    list_display = ("publication", "chunk_index", "source_kind", "page_start", "page_end", "word_count")
    list_filter = ("publication", "source_kind")
    search_fields = ("publication__title", "text")
    readonly_fields = ("created_at",)
