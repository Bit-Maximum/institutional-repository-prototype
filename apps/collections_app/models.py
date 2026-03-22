from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel
from apps.publications.models import Publication


class Collection(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="collections")
    is_public = models.BooleanField(default=True)
    publications = models.ManyToManyField(Publication, through="CollectionItem", related_name="collections")

    class Meta:
        verbose_name = "Коллекция"
        verbose_name_plural = "Коллекции"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("collections:detail", kwargs={"slug": self.slug})


class CollectionItem(TimeStampedModel):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Элемент коллекции"
        verbose_name_plural = "Элементы коллекции"
        unique_together = ("collection", "publication")
        ordering = ["position", "created_at"]
