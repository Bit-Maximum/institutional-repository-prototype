from __future__ import annotations

from collections import defaultdict

from django.db.models import Case, IntegerField, Q, When

from apps.publications.models import Publication
from apps.vector_store.services import VectorStoreService


class KeywordSearchService:
    def search(self, query: str, limit: int = 20):
        return list(
            Publication.objects.filter(is_draft=False)
            .filter(
                Q(title__icontains=query)
                | Q(contents__icontains=query)
                | Q(grif_text__icontains=query)
                | Q(grant_text__icontains=query)
                | Q(authors__full_name__icontains=query)
                | Q(keywords__name__icontains=query)
            )
            .distinct()[:limit]
        )


class SemanticSearchService:
    def __init__(self):
        self.vector_store = VectorStoreService()

    def search(self, query: str, limit: int = 20):
        hits = self.vector_store.search(query=query, limit=limit)
        ids = [item["publication_id"] for item in hits]
        if not ids:
            return []
        ordering = Case(*[When(pk=pk, then=position) for position, pk in enumerate(ids)], output_field=IntegerField())
        publications = Publication.objects.filter(pk__in=ids, is_draft=False).order_by(ordering)
        return list(publications)


class HybridSearchService:
    def __init__(self):
        self.keyword = KeywordSearchService()
        self.semantic = SemanticSearchService()

    def search(self, query: str, limit: int = 20):
        keyword_results = self.keyword.search(query, limit=limit)
        semantic_results = self.semantic.search(query, limit=limit)
        scores = defaultdict(float)
        by_id = {}

        for rank, publication in enumerate(keyword_results, start=1):
            by_id[publication.pk] = publication
            scores[publication.pk] += 1 / (60 + rank)

        for rank, publication in enumerate(semantic_results, start=1):
            by_id[publication.pk] = publication
            scores[publication.pk] += 1 / (60 + rank)

        ranked_ids = sorted(scores.keys(), key=lambda pk: scores[pk], reverse=True)
        return [by_id[pk] for pk in ranked_ids[:limit]]
