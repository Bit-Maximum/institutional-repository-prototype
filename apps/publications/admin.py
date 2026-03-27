from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.core.admin_mixins import LocalizedInlineMixin, LocalizedModelAdminMixin

from .models import (
    TEXT_EXTRACTION_STATUS_CHOICES,
    AcademicDegree,
    Author,
    AuthorPublication,
    Bibliography,
    BibliographyPublication,
    Copyright,
    CopyrightAuthor,
    CopyrightPublication,
    CopyrightPublisher,
    GraphicEdition,
    GraphicEditionPublication,
    Keyword,
    KeywordPublication,
    Publication,
    PublicationChunk,
    PublicationLanguage,
    PublicationUserEngagement,
    PublicationPeriodicity,
    PublicationPlace,
    PublicationPlacePublication,
    PublicationSubtype,
    PublicationType,
    Publisher,
    PublisherPublication,
    ScientificSupervisor,
    ScientificSupervisorPublication,
)


TEXT_EXTRACTION_STATUS_VARIANTS = {
    "Ожидает анализа": "warning",
    "Извлечён основной текст": "success",
    "Только метаданные: формат не поддерживается": "info",
    "Только метаданные: нетекстовая структура": "info",
    "Только метаданные: файл отсутствует": "danger",
    "Только метаданные: ошибка извлечения": "danger",
}


class PublicationDraftFilter(admin.SimpleListFilter):
    title = _("Статус публикации")
    parameter_name = "is_draft"

    def lookups(self, request, model_admin):
        return (("1", _("Черновики")), ("0", _("Опубликованные")))

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_draft=True)
        if self.value() == "0":
            return queryset.filter(is_draft=False)
        return queryset


class PublicationSubtypeFilter(admin.SimpleListFilter):
    title = _("Подтип издания")
    parameter_name = "publication_subtype"

    def lookups(self, request, model_admin):
        return [(str(item.pk), str(item)) for item in PublicationSubtype.objects.select_related("publication_type").order_by("publication_type__name", "name")]

    def queryset(self, request, queryset):
        return queryset.filter(publication_subtype_id=self.value()) if self.value() else queryset


class PublicationLanguageFilter(admin.SimpleListFilter):
    title = _("Язык")
    parameter_name = "language"

    def lookups(self, request, model_admin):
        return [(str(item.pk), item.name) for item in PublicationLanguage.objects.order_by("name")]

    def queryset(self, request, queryset):
        return queryset.filter(language_id=self.value()) if self.value() else queryset


class PublicationPeriodicityFilter(admin.SimpleListFilter):
    title = _("Периодичность")
    parameter_name = "periodicity"

    def lookups(self, request, model_admin):
        return [(str(item.pk), item.name) for item in PublicationPeriodicity.objects.order_by("name")]

    def queryset(self, request, queryset):
        return queryset.filter(periodicity_id=self.value()) if self.value() else queryset


class TextExtractionStatusFilter(admin.SimpleListFilter):
    title = _("Статус извлечения текста")
    parameter_name = "text_extraction_status"

    def lookups(self, request, model_admin):
        return list(TEXT_EXTRACTION_STATUS_CHOICES)

    def queryset(self, request, queryset):
        return queryset.filter(text_extraction_status=self.value()) if self.value() else queryset


class AcademicDegreeFilter(admin.SimpleListFilter):
    title = _("Учёная степень")
    parameter_name = "academic_degree"

    def lookups(self, request, model_admin):
        return [(str(item.pk), item.name) for item in AcademicDegree.objects.order_by("name")]

    def queryset(self, request, queryset):
        return queryset.filter(academic_degree_id=self.value()) if self.value() else queryset


class PublicationTypeFilter(admin.SimpleListFilter):
    title = _("Тип издания")
    parameter_name = "publication_type"

    def lookups(self, request, model_admin):
        return [(str(item.pk), item.name) for item in PublicationType.objects.order_by("name")]

    def queryset(self, request, queryset):
        return queryset.filter(publication_type_id=self.value()) if self.value() else queryset


class PublicationRelationInline(LocalizedInlineMixin, TabularInline):
    extra = 1
    classes = ("tab",)
    show_count = True
    show_change_link = True


class AuthorPublicationInline(PublicationRelationInline):
    model = AuthorPublication
    verbose_name_plural = _("Авторы издания")
    autocomplete_fields = ("author",)
    field_labels = {"author": _("Автор")}


class BibliographyPublicationInline(PublicationRelationInline):
    model = BibliographyPublication
    extra = 0
    verbose_name_plural = _("Библиографические описания")
    autocomplete_fields = ("bibliography",)
    field_labels = {"bibliography": _("Библиографическое описание")}


class PublicationPlacePublicationInline(PublicationRelationInline):
    model = PublicationPlacePublication
    extra = 0
    verbose_name_plural = _("Места публикации")
    autocomplete_fields = ("place",)
    field_labels = {"place": _("Место публикации")}


class PublisherPublicationInline(PublicationRelationInline):
    model = PublisherPublication
    extra = 0
    verbose_name_plural = _("Издатели")
    autocomplete_fields = ("publisher",)
    field_labels = {"publisher": _("Издатель")}


class CopyrightPublicationInline(PublicationRelationInline):
    model = CopyrightPublication
    extra = 0
    verbose_name_plural = _("Копирайты")
    autocomplete_fields = ("copyright",)
    field_labels = {"copyright": _("Копирайт")}


class GraphicEditionPublicationInline(PublicationRelationInline):
    model = GraphicEditionPublication
    extra = 0
    verbose_name_plural = _("Графические издания")
    autocomplete_fields = ("graphic_edition",)
    field_labels = {"graphic_edition": _("Графическое издание")}


class KeywordPublicationInline(PublicationRelationInline):
    model = KeywordPublication
    extra = 0
    verbose_name_plural = _("Ключевые слова")
    autocomplete_fields = ("keyword",)
    field_labels = {"keyword": _("Ключевое слово")}


class ScientificSupervisorPublicationInline(PublicationRelationInline):
    model = ScientificSupervisorPublication
    extra = 0
    verbose_name_plural = _("Научные руководители")
    autocomplete_fields = ("scientific_supervisor",)
    field_labels = {"scientific_supervisor": _("Научный руководитель")}


class RelatedPublicationInline(PublicationRelationInline):
    extra = 0
    verbose_name_plural = _("Связанные издания")
    autocomplete_fields = ("publication",)
    field_labels = {"publication": _("Издание")}


class PublicationForAuthorInline(RelatedPublicationInline):
    model = AuthorPublication
    verbose_name_plural = _("Издания автора")


class PublicationForBibliographyInline(RelatedPublicationInline):
    model = BibliographyPublication
    verbose_name_plural = _("Издания с этим библиографическим описанием")


class PublicationForPlaceInline(RelatedPublicationInline):
    model = PublicationPlacePublication
    verbose_name_plural = _("Издания по месту публикации")


class PublicationForPublisherInline(RelatedPublicationInline):
    model = PublisherPublication
    verbose_name_plural = _("Издания издателя")


class PublicationForCopyrightInline(RelatedPublicationInline):
    model = CopyrightPublication
    verbose_name_plural = _("Издания с этим копирайтом")


class PublicationForGraphicEditionInline(RelatedPublicationInline):
    model = GraphicEditionPublication
    verbose_name_plural = _("Издания с графическим приложением")


class PublicationForKeywordInline(RelatedPublicationInline):
    model = KeywordPublication
    verbose_name_plural = _("Издания по ключевому слову")


class PublicationForScientificSupervisorInline(RelatedPublicationInline):
    model = ScientificSupervisorPublication
    verbose_name_plural = _("Издания научного руководителя")


class CopyrightAuthorInline(LocalizedInlineMixin, TabularInline):
    model = CopyrightAuthor
    extra = 1
    show_count = True
    verbose_name_plural = _("Авторы копирайта")
    autocomplete_fields = ("author",)
    field_labels = {"author": _("Автор")}


class CopyrightPublisherInline(LocalizedInlineMixin, TabularInline):
    model = CopyrightPublisher
    extra = 1
    show_count = True
    verbose_name_plural = _("Издатели копирайта")
    autocomplete_fields = ("publisher",)
    field_labels = {"publisher": _("Издатель")}


@admin.register(PublicationType)
class PublicationTypeAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    field_labels = {"name": _("Название")}

    @display(description=_("Название"))
    def name_display(self, obj):
        return obj.name


@admin.register(PublicationSubtype)
class PublicationSubtypeAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "publication_type_display")
    list_filter = (PublicationTypeFilter,)
    search_fields = ("name", "publication_type__name")
    field_labels = {
        "name": _("Название подтипа"),
        "publication_type": _("Тип издания"),
    }

    @display(description=_("Подтип издания"))
    def name_display(self, obj):
        return obj.name

    @display(description=_("Тип издания"), ordering="publication_type__name")
    def publication_type_display(self, obj):
        return obj.publication_type


@admin.register(PublicationLanguage)
class PublicationLanguageAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    field_labels = {"name": _("Название языка")}

    @display(description=_("Язык издания"))
    def name_display(self, obj):
        return obj.name


@admin.register(PublicationPeriodicity)
class PublicationPeriodicityAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    field_labels = {"name": _("Название периодичности")}

    @display(description=_("Периодичность издания"))
    def name_display(self, obj):
        return obj.name


@admin.register(AcademicDegree)
class AcademicDegreeAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    field_labels = {"name": _("Название степени")}

    @display(description=_("Учёная степень"))
    def name_display(self, obj):
        return obj.name


@admin.register(Author)
class AuthorAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("full_name_display", "academic_degree_display", "position_display")
    search_fields = ("full_name", "position", "author_mark")
    list_filter = (AcademicDegreeFilter,)
    autocomplete_fields = ("academic_degree",)
    inlines = (PublicationForAuthorInline,)
    field_labels = {
        "full_name": _("ФИО автора"),
        "academic_degree": _("Учёная степень"),
        "position": _("Должность"),
        "author_mark": _("Авторский знак"),
    }

    @display(description=_("ФИО"), ordering="full_name")
    def full_name_display(self, obj):
        return obj.full_name

    @display(description=_("Учёная степень"), ordering="academic_degree__name")
    def academic_degree_display(self, obj):
        return obj.academic_degree or "—"

    @display(description=_("Должность"), ordering="position")
    def position_display(self, obj):
        return obj.position or "—"


@admin.register(ScientificSupervisor)
class ScientificSupervisorAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("full_name_display", "academic_degree_display", "position_display")
    search_fields = ("full_name", "position")
    list_filter = (AcademicDegreeFilter,)
    autocomplete_fields = ("academic_degree",)
    inlines = (PublicationForScientificSupervisorInline,)
    field_labels = {
        "full_name": _("ФИО научного руководителя"),
        "academic_degree": _("Учёная степень"),
        "position": _("Должность"),
    }

    @display(description=_("ФИО"), ordering="full_name")
    def full_name_display(self, obj):
        return obj.full_name

    @display(description=_("Учёная степень"), ordering="academic_degree__name")
    def academic_degree_display(self, obj):
        return obj.academic_degree or "—"

    @display(description=_("Должность"), ordering="position")
    def position_display(self, obj):
        return obj.position or "—"


@admin.register(Keyword)
class KeywordAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display",)
    search_fields = ("name",)
    inlines = (PublicationForKeywordInline,)
    field_labels = {"name": _("Ключевое слово")}

    @display(description=_("Ключевое слово"))
    def name_display(self, obj):
        return obj.name


@admin.register(PublicationPlace)
class PublicationPlaceAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "address_display")
    search_fields = ("name", "address")
    inlines = (PublicationForPlaceInline,)
    field_labels = {
        "name": _("Название места публикации"),
        "address": _("Адрес"),
    }

    @display(description=_("Место публикации"), ordering="name")
    def name_display(self, obj):
        return obj.name

    @display(description=_("Адрес"), ordering="address")
    def address_display(self, obj):
        return obj.address or "—"


@admin.register(Publisher)
class PublisherAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "address_display")
    search_fields = ("name", "address")
    inlines = (PublicationForPublisherInline,)
    field_labels = {
        "name": _("Название издателя"),
        "address": _("Адрес"),
    }

    @display(description=_("Издатель"), ordering="name")
    def name_display(self, obj):
        return obj.name

    @display(description=_("Адрес"), ordering="address")
    def address_display(self, obj):
        return obj.address or "—"


@admin.register(Copyright)
class CopyrightAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "address_display")
    search_fields = ("name", "address")
    inlines = (CopyrightAuthorInline, CopyrightPublisherInline, PublicationForCopyrightInline)
    field_labels = {
        "name": _("Наименование копирайта"),
        "address": _("Адрес"),
    }

    @display(description=_("Копирайт"), ordering="name")
    def name_display(self, obj):
        return obj.name

    @display(description=_("Адрес"), ordering="address")
    def address_display(self, obj):
        return obj.address or "—"


@admin.register(Bibliography)
class BibliographyAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("description_display",)
    search_fields = ("bibliographic_description",)
    inlines = (PublicationForBibliographyInline,)
    field_labels = {"bibliographic_description": _("Библиографическое описание")}

    @display(description=_("Библиографическое описание"))
    def description_display(self, obj):
        return obj.bibliographic_description


@admin.register(GraphicEdition)
class GraphicEditionAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("name_display", "document_link_display")
    search_fields = ("name", "document_link")
    inlines = (PublicationForGraphicEditionInline,)
    field_labels = {
        "name": _("Название графического издания"),
        "document_link": _("Ссылка на документ"),
    }

    @display(description=_("Графическое издание"), ordering="name")
    def name_display(self, obj):
        return obj.name

    @display(description=_("Ссылка на документ"), ordering="document_link")
    def document_link_display(self, obj):
        return obj.document_link or "—"


@admin.register(Publication)
class PublicationAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = (
        "title_display",
        "publication_type_display",
        "publication_year_display",
        "language_display",
        "text_extraction_status_display",
        "workflow_status_display",
    )
    list_filter = (
        PublicationDraftFilter,
        PublicationSubtypeFilter,
        PublicationLanguageFilter,
        PublicationPeriodicityFilter,
        TextExtractionStatusFilter,
    )
    search_fields = ("title", "contents", "grif_text", "grant_text", "text_extraction_notes")
    autocomplete_fields = ("uploaded_by", "last_saved_by", "published_by", "publication_subtype", "periodicity", "language")
    fieldsets = (
        (_("Основная информация"), {
            "fields": (
                "title",
                "publication_subtype",
                "language",
                "publication_year",
                "periodicity",
                "subject_code",
                "start_page",
                "end_page",
                "volume_number",
                "issue_number",
            )
        }),
        (_("Файлы и содержимое"), {
            "fields": (
                "file",
                "file_extension_admin",
                "publication_format_link",
                "contents",
                "grif_text",
                "grant_text",
                "derived_characteristics",
            )
        }),
        (_("Индексация и извлечение текста"), {
            "classes": ("tab",),
            "fields": (
                "text_extraction_status_admin",
                "text_extraction_notes_admin",
                "has_extracted_text_admin",
                "vector_index_signature",
                "vector_indexed_at_admin",
            )
        }),
        (_("Workflow и служебные поля"), {
            "classes": ("tab",),
            "fields": (
                "workflow_status_admin",
                "is_draft",
                "draft_revision",
                "uploaded_by",
                "last_saved_by",
                "published_by",
                "uploaded_at_admin",
                "updated_at_admin",
                "published_at_admin",
            )
        }),
    )
    readonly_fields = (
        "file_extension_admin",
        "text_extraction_status_admin",
        "text_extraction_notes_admin",
        "has_extracted_text_admin",
        "uploaded_at_admin",
        "updated_at_admin",
        "published_at_admin",
        "vector_indexed_at_admin",
        "workflow_status_admin",
    )
    inlines = (
        AuthorPublicationInline,
        ScientificSupervisorPublicationInline,
        KeywordPublicationInline,
        BibliographyPublicationInline,
        PublicationPlacePublicationInline,
        PublisherPublicationInline,
        CopyrightPublicationInline,
        GraphicEditionPublicationInline,
    )
    field_labels = {
        "title": _("Название издания"),
        "publication_subtype": _("Подтип издания"),
        "language": _("Язык издания"),
        "publication_year": _("Год издания"),
        "periodicity": _("Периодичность"),
        "subject_code": _("Код специальности"),
        "start_page": _("Начальная страница"),
        "end_page": _("Конечная страница"),
        "volume_number": _("Номер тома"),
        "issue_number": _("Номер выпуска"),
        "file": _("Файл издания"),
        "publication_format_link": _("Ссылка на публикацию"),
        "contents": _("Аннотация / содержание"),
        "grif_text": _("Гриф"),
        "grant_text": _("Сведения о гранте"),
        "derived_characteristics": _("Производные характеристики"),
        "vector_index_signature": _("Сигнатура индекса"),
        "is_draft": _("Черновик"),
        "draft_revision": _("Номер редакции черновика"),
        "uploaded_by": _("Кто загрузил"),
        "last_saved_by": _("Кто сохранил последним"),
        "published_by": _("Кто опубликовал"),
    }
    field_help_texts = {
        "publication_format_link": _("Укажите внешний URL, если издание доступно по ссылке."),
        "derived_characteristics": _("JSON-массив автоматически выделенных характеристик документа."),
        "vector_index_signature": _("Техническая сигнатура индексации для контроля актуальности векторного индекса."),
    }

    @display(description=_("Издание"), ordering="title")
    def title_display(self, obj):
        return obj.title

    @display(description=_("Тип издания"), ordering="publication_subtype__publication_type__name")
    def publication_type_display(self, obj):
        return obj.publication_type or "—"

    @display(description=_("Год"), ordering="publication_year")
    def publication_year_display(self, obj):
        return obj.publication_year or "—"

    @display(description=_("Язык"), ordering="language__name")
    def language_display(self, obj):
        return obj.language or "—"

    @display(description=_("Статус извлечения"), label=TEXT_EXTRACTION_STATUS_VARIANTS)
    def text_extraction_status_display(self, obj):
        return obj.get_text_extraction_status_display()

    @display(description=_("Статус публикации"), label={"Черновик": "warning", "Опубликовано": "success"})
    def workflow_status_display(self, obj):
        return obj.get_status_display()

    @display(description=_("Расширение файла"))
    def file_extension_admin(self, obj):
        return obj.file_extension or "—"

    @display(description=_("Статус извлечения"), label=TEXT_EXTRACTION_STATUS_VARIANTS)
    def text_extraction_status_admin(self, obj):
        return obj.get_text_extraction_status_display()

    @display(description=_("Примечания по извлечению текста"))
    def text_extraction_notes_admin(self, obj):
        return obj.text_extraction_notes or "—"

    @display(description=_("Основной текст извлечён"), label={"Да": "success", "Нет": "warning"})
    def has_extracted_text_admin(self, obj):
        return _("Да") if obj.has_extracted_text else _("Нет")

    @display(description=_("Статус workflow"), label={"Черновик": "warning", "Опубликовано": "success"})
    def workflow_status_admin(self, obj):
        return obj.get_status_display()

    @display(description=_("Дата загрузки"))
    def uploaded_at_admin(self, obj):
        return obj.uploaded_at or "—"

    @display(description=_("Дата последнего обновления"))
    def updated_at_admin(self, obj):
        return obj.updated_at or "—"

    @display(description=_("Дата публикации"))
    def published_at_admin(self, obj):
        return obj.published_at or "—"

    @display(description=_("Дата индексации"))
    def vector_indexed_at_admin(self, obj):
        return obj.vector_indexed_at or "—"


@admin.register(PublicationChunk)
class PublicationChunkAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = (
        "publication_display",
        "chunk_index_display",
        "source_kind_display",
        "pages_display",
        "word_count_display",
    )
    list_filter = ("publication", "source_kind")
    search_fields = ("publication__title", "text", "section_title")
    autocomplete_fields = ("publication",)
    readonly_fields = ("created_at_admin",)
    field_labels = {
        "publication": _("Издание"),
        "chunk_index": _("Номер фрагмента"),
        "text": _("Текст фрагмента"),
        "source_kind": _("Источник текста"),
        "page_start": _("Начальная страница"),
        "page_end": _("Конечная страница"),
        "section_title": _("Название раздела"),
        "char_count": _("Количество символов"),
        "word_count": _("Количество слов"),
        "index_quality": _("Качество индексации"),
    }

    @display(description=_("Издание"), ordering="publication__title")
    def publication_display(self, obj):
        return obj.publication

    @display(description=_("Фрагмент"), ordering="chunk_index")
    def chunk_index_display(self, obj):
        return obj.chunk_index

    @display(description=_("Источник текста"), ordering="source_kind")
    def source_kind_display(self, obj):
        return obj.get_source_kind_display()

    @display(description=_("Страницы"))
    def pages_display(self, obj):
        return obj.page_label or "—"

    @display(description=_("Количество слов"), ordering="word_count")
    def word_count_display(self, obj):
        return obj.word_count

    @display(description=_("Дата создания"))
    def created_at_admin(self, obj):
        return obj.created_at or "—"


@admin.register(PublicationUserEngagement)
class PublicationUserEngagementAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = (
        "publication_display",
        "user_display",
        "view_count_display",
        "download_count_display",
        "last_viewed_at_display",
        "last_downloaded_at_display",
    )
    list_filter = ("last_viewed_at", "last_downloaded_at")
    search_fields = ("publication__title", "user__email", "user__username")
    autocomplete_fields = ("publication", "user")
    readonly_fields = (
        "created_at_admin",
        "updated_at_admin",
        "first_viewed_at_admin",
        "last_viewed_at_admin",
        "first_downloaded_at_admin",
        "last_downloaded_at_admin",
    )
    field_labels = {
        "publication": _("Издание"),
        "user": _("Пользователь"),
        "view_count": _("Количество просмотров"),
        "download_count": _("Количество скачиваний"),
    }

    @display(description=_("Издание"), ordering="publication__title")
    def publication_display(self, obj):
        return obj.publication

    @display(description=_("Пользователь"), ordering="user__email")
    def user_display(self, obj):
        return obj.user

    @display(description=_("Просмотры"), ordering="view_count")
    def view_count_display(self, obj):
        return obj.view_count

    @display(description=_("Скачивания"), ordering="download_count")
    def download_count_display(self, obj):
        return obj.download_count

    @display(description=_("Первый просмотр"))
    def first_viewed_at_admin(self, obj):
        return obj.first_viewed_at or "—"

    @display(description=_("Последний просмотр"), ordering="last_viewed_at")
    def last_viewed_at_display(self, obj):
        return obj.last_viewed_at or "—"

    @display(description=_("Последний просмотр"))
    def last_viewed_at_admin(self, obj):
        return obj.last_viewed_at or "—"

    @display(description=_("Первое скачивание"))
    def first_downloaded_at_admin(self, obj):
        return obj.first_downloaded_at or "—"

    @display(description=_("Последнее скачивание"), ordering="last_downloaded_at")
    def last_downloaded_at_display(self, obj):
        return obj.last_downloaded_at or "—"

    @display(description=_("Последнее скачивание"))
    def last_downloaded_at_admin(self, obj):
        return obj.last_downloaded_at or "—"

    @display(description=_("Дата создания"))
    def created_at_admin(self, obj):
        return obj.created_at or "—"

    @display(description=_("Дата обновления"))
    def updated_at_admin(self, obj):
        return obj.updated_at or "—"
