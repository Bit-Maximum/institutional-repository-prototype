from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class PublicationType(models.Model):
    name = models.CharField(max_length=255)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Тип издания"
        verbose_name_plural = "Типы изданий"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Author(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    affiliation = models.CharField(max_length=255, blank=True)
    academic_degree = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name


class Publication(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    class VectorState(models.TextChoices):
        PENDING = "pending", "Ожидает индексации"
        INDEXED = "indexed", "Индексировано"
        FAILED = "failed", "Ошибка"

    title = models.CharField(max_length=500)
    slug = models.SlugField(unique=True)
    abstract = models.TextField(blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=64, default="ru")
    isbn_or_identifier = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    vector_state = models.CharField(max_length=16, choices=VectorState.choices, default=VectorState.PENDING)
    is_public = models.BooleanField(default=True)
    publication_type = models.ForeignKey(PublicationType, on_delete=models.PROTECT, related_name="publications")
    authors = models.ManyToManyField(Author, related_name="publications", blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to="publications/")
    cover = models.ImageField(upload_to="covers/", blank=True)
    copyright_note = models.CharField(max_length=255, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    extracted_text = models.TextField(blank=True)
    search_document = models.TextField(blank=True)

    class Meta:
        verbose_name = "Издание"
        verbose_name_plural = "Издания"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse("publications:detail", kwargs={"slug": self.slug})
