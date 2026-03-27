from django.conf import settings
from django.db import models
from django.utils import timezone


class SearchQuery(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="search_query_id")
    query_text = models.TextField()
    query_topic = models.IntegerField(null=True, blank=True)
    filters = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_queries",
        db_column="user_id",
    )

    class Meta:
        db_table = "search_queries"
        verbose_name = "Поисковый запрос"
        verbose_name_plural = "Поисковые запросы"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user"], name="idx_search_queries_user_id")]

    def __str__(self) -> str:
        return self.query_text[:120]
