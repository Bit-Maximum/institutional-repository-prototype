from __future__ import annotations

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.publications.models import Publication


class Collection(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="collection_id")
    name = models.TextField()
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collections",
        db_column="author_user_id",
    )
    publications = models.ManyToManyField(
        Publication,
        through="CollectionPublication",
        related_name="collections",
        blank=True,
    )

    class Meta:
        db_table = "publication_collections"
        verbose_name = "Коллекция изданий"
        verbose_name_plural = "Коллекции изданий"
        ordering = ["name"]
        indexes = [models.Index(fields=["author_user"], name="idx_pub_cols_author_id")]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("collections:detail", kwargs={"pk": self.pk})


class CollectionPublication(models.Model):
    pk = models.CompositePrimaryKey("collection", "publication")
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        db_table = "collection_publications"
        verbose_name = "Связь коллекции и издания"
        verbose_name_plural = "Связи коллекций и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_col_pubs_pub_id")]
