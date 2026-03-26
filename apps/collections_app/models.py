from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.publications.models import Publication


COLLECTION_REACTION_CHOICES = [
    (1, "Лайк"),
    (-1, "Дизлайк"),
]


class CollectionQuerySet(models.QuerySet):
    def with_stats(self):
        return self.annotate(
            like_count=Count("reactions", filter=Q(reactions__value=1), distinct=True),
            dislike_count=Count("reactions", filter=Q(reactions__value=-1), distinct=True),
            publication_count=Count("publications", distinct=True),
        )


class Collection(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="collection_id")
    name = models.TextField()
    description = models.TextField(blank=True)
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collections",
        db_column="author_user_id",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    publications = models.ManyToManyField(
        Publication,
        through="CollectionPublication",
        related_name="collections",
        blank=True,
    )

    objects = CollectionQuerySet.as_manager()

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

    @property
    def rating_score(self) -> int:
        likes = getattr(self, "like_count", None)
        dislikes = getattr(self, "dislike_count", None)
        if likes is None or dislikes is None:
            likes = self.reactions.filter(value=1).count()
            dislikes = self.reactions.filter(value=-1).count()
        return int(likes) - int(dislikes)


class CollectionPublication(models.Model):
    pk = models.CompositePrimaryKey("collection", "publication")
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    added_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "collection_publications"
        verbose_name = "Связь коллекции и издания"
        verbose_name_plural = "Связи коллекций и изданий"
        indexes = [models.Index(fields=["publication"], name="idx_col_pubs_pub_id")]
        ordering = ["-added_at"]


class CollectionReaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collection_reactions")
    value = models.SmallIntegerField(choices=COLLECTION_REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "collection_reactions"
        verbose_name = "Оценка коллекции"
        verbose_name_plural = "Оценки коллекций"
        constraints = [
            models.UniqueConstraint(fields=["collection", "user"], name="uq_collection_reactions_user"),
            models.CheckConstraint(condition=Q(value__in=[-1, 1]), name="chk_collection_reaction_value"),
        ]
        indexes = [
            models.Index(fields=["collection", "value"], name="idx_col_react_value"),
            models.Index(fields=["user"], name="idx_col_react_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.collection} ({self.value})"
