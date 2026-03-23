from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


TEXT_EXTRACTION_STATUS_CHOICES = [
    ("pending", "Ожидает анализа"),
    ("fulltext", "Извлечён основной текст"),
    ("metadata_only_unsupported", "Только метаданные: формат не поддерживается"),
    ("metadata_only_nontext", "Только метаданные: нетекстовая структура"),
    ("metadata_only_missing", "Только метаданные: файл отсутствует"),
    ("metadata_only_error", "Только метаданные: ошибка извлечения"),
]

CHUNK_SOURCE_KIND_CHOICES = [
    ("fulltext", "Основной текст"),
    ("metadata", "Только метаданные"),
]


class NamedDictionaryModel(models.Model):
    name = models.TextField(unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PublicationPeriodicity(NamedDictionaryModel):
    id = models.BigAutoField(primary_key=True, db_column="periodicity_id")

    class Meta(NamedDictionaryModel.Meta):
        db_table = "publication_periodicities"
        verbose_name = "Периодичность издания"
        verbose_name_plural = "Периодичности изданий"


class PublicationLanguage(NamedDictionaryModel):
    id = models.BigAutoField(primary_key=True, db_column="language_id")

    class Meta(NamedDictionaryModel.Meta):
        db_table = "publication_languages"
        verbose_name = "Язык издания"
        verbose_name_plural = "Языки изданий"


class PublicationType(NamedDictionaryModel):
    id = models.BigAutoField(primary_key=True, db_column="publication_type_id")

    class Meta(NamedDictionaryModel.Meta):
        db_table = "publication_types"
        verbose_name = "Тип издания"
        verbose_name_plural = "Типы изданий"


class PublicationSubtype(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="publication_subtype_id")
    name = models.TextField()
    publication_type = models.ForeignKey(
        PublicationType,
        on_delete=models.PROTECT,
        related_name="subtypes",
        db_column="publication_type_id",
    )

    class Meta:
        db_table = "publication_subtypes"
        verbose_name = "Подтип издания"
        verbose_name_plural = "Подтипы изданий"
        ordering = ["publication_type__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "publication_type"],
                name="uq_pub_subtypes_name_type",
            )
        ]
        indexes = [models.Index(fields=["publication_type"], name="idx_pub_subtypes_type_id")]

    def __str__(self) -> str:
        return f"{self.publication_type.name} / {self.name}"


class Keyword(NamedDictionaryModel):
    id = models.BigAutoField(primary_key=True, db_column="keyword_id")

    class Meta(NamedDictionaryModel.Meta):
        db_table = "keywords"
        verbose_name = "Ключевое слово"
        verbose_name_plural = "Ключевые слова"


class GraphicEdition(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="graphic_edition_id")
    name = models.TextField()
    document_link = models.TextField(blank=True)

    class Meta:
        db_table = "graphic_editions"
        verbose_name = "Графическое издание"
        verbose_name_plural = "Графические издания"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Bibliography(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="bibliography_id")
    bibliographic_description = models.TextField()

    class Meta:
        db_table = "bibliographies"
        verbose_name = "Библиографическое описание"
        verbose_name_plural = "Библиографические описания"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.bibliographic_description[:120]


class PublicationPlace(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="place_id")
    name = models.TextField()
    address = models.TextField(blank=True)

    class Meta:
        db_table = "publication_places"
        verbose_name = "Место публикации"
        verbose_name_plural = "Места публикации"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Publisher(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="publisher_id")
    name = models.TextField()
    address = models.TextField(blank=True)

    class Meta:
        db_table = "publishers"
        verbose_name = "Издатель"
        verbose_name_plural = "Издатели"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AcademicDegree(NamedDictionaryModel):
    id = models.BigAutoField(primary_key=True, db_column="academic_degree_id")

    class Meta(NamedDictionaryModel.Meta):
        db_table = "academic_degrees"
        verbose_name = "Учёная степень"
        verbose_name_plural = "Учёные степени"


class Author(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="author_id")
    full_name = models.TextField()
    academic_degree = models.ForeignKey(
        AcademicDegree,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authors",
        db_column="academic_degree_id",
    )
    position = models.TextField(blank=True)
    author_mark = models.TextField(blank=True)

    class Meta:
        db_table = "authors"
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["full_name"]
        indexes = [models.Index(fields=["academic_degree"], name="idx_authors_academic_degree_id")]

    def __str__(self) -> str:
        return self.full_name


class ScientificSupervisor(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="scientific_supervisor_id")
    full_name = models.TextField()
    academic_degree = models.ForeignKey(
        AcademicDegree,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scientific_supervisors",
        db_column="academic_degree_id",
    )
    position = models.TextField(blank=True)

    class Meta:
        db_table = "scientific_supervisors"
        verbose_name = "Научный руководитель"
        verbose_name_plural = "Научные руководители"
        ordering = ["full_name"]
        indexes = [models.Index(fields=["academic_degree"], name="idx_sci_sup_degree_id")]

    def __str__(self) -> str:
        return self.full_name


class Copyright(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="copyright_id")
    name = models.TextField()
    address = models.TextField(blank=True)
    authors = models.ManyToManyField(
        Author,
        through="CopyrightAuthor",
        related_name="copyrights",
        blank=True,
    )
    publishers = models.ManyToManyField(
        Publisher,
        through="CopyrightPublisher",
        related_name="copyrights",
        blank=True,
    )

    class Meta:
        db_table = "copyrights"
        verbose_name = "Копирайт"
        verbose_name_plural = "Копирайты"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Publication(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="publication_id")
    title = models.TextField()
    subject_code = models.IntegerField(null=True, blank=True)
    start_page = models.IntegerField(null=True, blank=True)
    end_page = models.IntegerField(null=True, blank=True)
    file = models.FileField(upload_to="publications/", db_column="main_text_link", null=True, blank=True)
    file_extension = models.CharField(max_length=32, blank=True)
    publication_format_link = models.TextField(blank=True)
    contents = models.TextField(blank=True)
    text_extraction_status = models.CharField(
        max_length=32,
        choices=TEXT_EXTRACTION_STATUS_CHOICES,
        default="pending",
    )
    text_extraction_notes = models.TextField(blank=True)
    has_extracted_text = models.BooleanField(default=False)
    vector_index_signature = models.CharField(max_length=64, blank=True, default="")
    vector_indexed_at = models.DateTimeField(null=True, blank=True)
    grant_text = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_publications",
        db_column="uploaded_by_user_id",
    )
    publication_year = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now, editable=False)
    volume_number = models.PositiveIntegerField(null=True, blank=True)
    issue_number = models.PositiveIntegerField(null=True, blank=True)
    publication_subtype = models.ForeignKey(
        PublicationSubtype,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications",
        db_column="publication_subtype_id",
    )
    periodicity = models.ForeignKey(
        PublicationPeriodicity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications",
        db_column="periodicity_id",
    )
    grif_text = models.TextField(blank=True)
    language = models.ForeignKey(
        PublicationLanguage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications",
        db_column="language_id",
    )
    is_draft = models.BooleanField(default=False)
    authors = models.ManyToManyField(Author, through="AuthorPublication", related_name="publications", blank=True)
    bibliographies = models.ManyToManyField(
        Bibliography,
        through="BibliographyPublication",
        related_name="publications",
        blank=True,
    )
    publication_places = models.ManyToManyField(
        PublicationPlace,
        through="PublicationPlacePublication",
        related_name="publications",
        blank=True,
    )
    publishers = models.ManyToManyField(
        Publisher,
        through="PublisherPublication",
        related_name="publications",
        blank=True,
    )
    copyrights = models.ManyToManyField(
        Copyright,
        through="CopyrightPublication",
        related_name="publications",
        blank=True,
    )
    graphic_editions = models.ManyToManyField(
        GraphicEdition,
        through="GraphicEditionPublication",
        related_name="publications",
        blank=True,
    )
    keywords = models.ManyToManyField(
        Keyword,
        through="KeywordPublication",
        related_name="publications",
        blank=True,
    )
    scientific_supervisors = models.ManyToManyField(
        ScientificSupervisor,
        through="ScientificSupervisorPublication",
        related_name="publications",
        blank=True,
    )

    class Meta:
        db_table = "publications"
        verbose_name = "Издание"
        verbose_name_plural = "Издания"
        ordering = ["-uploaded_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_page__isnull=True) | Q(end_page__isnull=True) | Q(start_page__lte=models.F("end_page")),
                name="chk_publications_pages",
            ),
            models.CheckConstraint(
                condition=Q(publication_year__isnull=True) | Q(publication_year__gte=0, publication_year__lte=9999),
                name="chk_publications_year",
            ),
            models.CheckConstraint(
                condition=Q(volume_number__isnull=True) | Q(volume_number__gte=0),
                name="chk_publications_volume",
            ),
            models.CheckConstraint(
                condition=Q(issue_number__isnull=True) | Q(issue_number__gte=0),
                name="chk_publications_issue",
            ),
        ]
        indexes = [
            models.Index(fields=["uploaded_by"], name="idx_pubs_uploaded_by_id"),
            models.Index(fields=["publication_subtype"], name="idx_pubs_subtype_id"),
            models.Index(fields=["periodicity"], name="idx_pubs_period_id"),
            models.Index(fields=["language"], name="idx_publications_language_id"),
            models.Index(fields=["text_extraction_status"], name="idx_pubs_extract_status"),
            models.Index(fields=["vector_index_signature"], name="idx_pubs_vector_sig"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse("publications:detail", kwargs={"pk": self.pk})

    @property
    def abstract(self) -> str:
        return self.contents

    @property
    def publication_type(self):
        return self.publication_subtype.publication_type if self.publication_subtype else None

    @property
    def is_public(self) -> bool:
        return not self.is_draft

    @property
    def status(self) -> str:
        return "draft" if self.is_draft else "published"

    def get_status_display(self) -> str:
        return "Черновик" if self.is_draft else "Опубликовано"

    @property
    def language_name(self) -> str:
        return self.language.name if self.language else ""

    @property
    def uses_metadata_only_index(self) -> bool:
        return not self.has_extracted_text

    @property
    def search_document(self) -> str:
        keyword_text = ", ".join(keyword.name for keyword in self.keywords.all())
        author_text = ", ".join(author.full_name for author in self.authors.all())
        supervisor_text = ", ".join(supervisor.full_name for supervisor in self.scientific_supervisors.all())
        parts = [
            self.title,
            author_text,
            supervisor_text,
            self.contents,
            keyword_text,
            self.grif_text,
            self.grant_text,
        ]
        return "\n\n".join(part for part in parts if part).strip()


class PublicationChunk(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="publication_chunk_id")
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_column="publication_id",
    )
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    source_kind = models.CharField(max_length=16, choices=CHUNK_SOURCE_KIND_CHOICES, default="fulltext")
    page_start = models.PositiveIntegerField(null=True, blank=True)
    page_end = models.PositiveIntegerField(null=True, blank=True)
    char_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "publication_chunks"
        verbose_name = "Фрагмент издания"
        verbose_name_plural = "Фрагменты изданий"
        ordering = ["publication_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(fields=["publication", "chunk_index"], name="uq_pub_chunks_pub_idx"),
            models.CheckConstraint(
                condition=Q(page_start__isnull=True) | Q(page_end__isnull=True) | Q(page_start__lte=models.F("page_end")),
                name="chk_pub_chunks_pages",
            ),
        ]
        indexes = [
            models.Index(fields=["publication"], name="idx_pub_chunks_pub_id"),
        ]

    def __str__(self) -> str:
        label = f"#{self.chunk_index}"
        if self.page_start:
            if self.page_end and self.page_end != self.page_start:
                label += f" стр. {self.page_start}-{self.page_end}"
            else:
                label += f" стр. {self.page_start}"
        return f"{self.publication.title} / {label}"

    @property
    def page_label(self) -> str:
        if self.page_start and self.page_end and self.page_end != self.page_start:
            return f"стр. {self.page_start}–{self.page_end}"
        if self.page_start:
            return f"стр. {self.page_start}"
        return ""

    @property
    def vector_document(self) -> str:
        metadata_parts = [self.publication.title]
        authors = ", ".join(author.full_name for author in self.publication.authors.all())
        if authors:
            metadata_parts.append(f"Авторы: {authors}")
        if self.publication.publication_type:
            metadata_parts.append(f"Тип: {self.publication.publication_type.name}")
        if self.publication.publication_subtype:
            metadata_parts.append(f"Подтип: {self.publication.publication_subtype.name}")
        if self.publication.language:
            metadata_parts.append(f"Язык: {self.publication.language.name}")
        keywords = ", ".join(keyword.name for keyword in self.publication.keywords.all())
        if keywords:
            metadata_parts.append(f"Ключевые слова: {keywords}")
        if self.publication.publication_year:
            metadata_parts.append(f"Год: {self.publication.publication_year}")
        header = "\n".join(metadata_parts)
        return f"{header}\n\nФрагмент документа: {self.text}".strip()


class Recommendation(models.Model):
    pk = models.CompositePrimaryKey("user", "publication")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="recommended_to")

    class Meta:
        db_table = "recommendations"
        verbose_name = "Рекомендация"
        verbose_name_plural = "Рекомендации"
        indexes = [models.Index(fields=["publication"], name="idx_recom_pub_id")]


class PublicationPlacePublication(models.Model):
    pk = models.CompositePrimaryKey("place", "publication")
    place = models.ForeignKey(PublicationPlace, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "publication_place_publications"
        verbose_name = "Связь места публикации и издания"
        verbose_name_plural = "Связи мест публикации и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_place_pubs_pub_id")]


class PublisherPublication(models.Model):
    pk = models.CompositePrimaryKey("publisher", "publication")
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "publisher_publications"
        verbose_name = "Связь издателя и издания"
        verbose_name_plural = "Связи издателей и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_publisher_pubs_pub_id")]


class CopyrightPublication(models.Model):
    pk = models.CompositePrimaryKey("copyright", "publication")
    copyright = models.ForeignKey(Copyright, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "copyright_publications"
        verbose_name = "Связь копирайта и издания"
        verbose_name_plural = "Связи копирайтов и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_cpr_pubs_pub_id")]


class CopyrightPublisher(models.Model):
    pk = models.CompositePrimaryKey("copyright", "publisher")
    copyright = models.ForeignKey(Copyright, on_delete=models.CASCADE)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)

    class Meta:
        db_table = "copyright_publishers"
        verbose_name = "Связь копирайта и издателя"
        verbose_name_plural = "Связи копирайтов и издателей"
        indexes = [models.Index(fields=["publisher"], name="idx_cpr_pubs_publisher_id")]


class AuthorPublication(models.Model):
    pk = models.CompositePrimaryKey("author", "publication")
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "author_publications"
        verbose_name = "Связь автора и издания"
        verbose_name_plural = "Связи авторов и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_author_pubs_pub_id")]


class CopyrightAuthor(models.Model):
    pk = models.CompositePrimaryKey("copyright", "author")
    copyright = models.ForeignKey(Copyright, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        db_table = "copyright_authors"
        verbose_name = "Связь копирайта и автора"
        verbose_name_plural = "Связи копирайтов и авторов"
        indexes = [models.Index(fields=["author"], name="idx_cpr_auth_author_id")]


class BibliographyPublication(models.Model):
    pk = models.CompositePrimaryKey("bibliography", "publication")
    bibliography = models.ForeignKey(Bibliography, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "bibliography_publications"
        verbose_name = "Связь библиографии и издания"
        verbose_name_plural = "Связи библиографий и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_biblio_pubs_pub_id")]


class GraphicEditionPublication(models.Model):
    pk = models.CompositePrimaryKey("graphic_edition", "publication")
    graphic_edition = models.ForeignKey(GraphicEdition, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "graphic_edition_publications"
        verbose_name = "Связь графического издания и публикации"
        verbose_name_plural = "Связи графических изданий и публикаций"
        indexes = [models.Index(fields=["publication"], name="idx_graph_pubs_pub_id")]


class KeywordPublication(models.Model):
    pk = models.CompositePrimaryKey("keyword", "publication")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "keyword_publications"
        verbose_name = "Связь ключевого слова и издания"
        verbose_name_plural = "Связи ключевых слов и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_kw_pubs_pub_id")]


class ScientificSupervisorPublication(models.Model):
    pk = models.CompositePrimaryKey("scientific_supervisor", "publication")
    scientific_supervisor = models.ForeignKey(ScientificSupervisor, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "scientific_supervisor_publications"
        verbose_name = "Связь научного руководителя и издания"
        verbose_name_plural = "Связи научных руководителей и изданий"
        indexes = [
            models.Index(
                fields=["publication"],
                name="idx_sup_pubs_pub_id",
            )
        ]
