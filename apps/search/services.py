from __future__ import annotations

import math
import re
from typing import Any, Iterable

from django.conf import settings
from django.db.models import QuerySet

from apps.publications.models import Publication
from apps.vector_store.services import VectorStoreService


class BaseSearchService:
    select_related_fields = (
        "publication_subtype",
        "publication_subtype__publication_type",
        "language",
        "periodicity",
    )
    prefetch_related_fields = (
        "authors",
        "keywords",
        "publishers",
        "publication_places",
        "scientific_supervisors",
    )

    def get_base_queryset(self) -> QuerySet[Publication]:
        return Publication.objects.filter(is_draft=False).select_related(*self.select_related_fields).prefetch_related(
            *self.prefetch_related_fields
        )

    def apply_filters(self, queryset: QuerySet[Publication], filters: dict[str, Any] | None = None) -> QuerySet[Publication]:
        filters = filters or {}
        publication_type = filters.get("publication_type")
        publication_subtype = filters.get("publication_subtype")
        language = filters.get("language")
        periodicity = filters.get("periodicity")
        author = filters.get("author")
        keyword = filters.get("keyword")
        publisher = filters.get("publisher")
        publication_place = filters.get("publication_place")
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")

        if publication_type:
            queryset = queryset.filter(publication_subtype__publication_type=publication_type)
        if publication_subtype:
            queryset = queryset.filter(publication_subtype=publication_subtype)
        if language:
            queryset = queryset.filter(language=language)
        if periodicity:
            queryset = queryset.filter(periodicity=periodicity)
        if author:
            queryset = queryset.filter(authors=author)
        if keyword:
            queryset = queryset.filter(keywords=keyword)
        if publisher:
            queryset = queryset.filter(publishers=publisher)
        if publication_place:
            queryset = queryset.filter(publication_places=publication_place)
        if year_from is not None:
            queryset = queryset.filter(publication_year__gte=year_from)
        if year_to is not None:
            queryset = queryset.filter(publication_year__lte=year_to)

        return queryset.distinct()

    def has_active_filters(self, filters: dict[str, Any] | None = None) -> bool:
        if not filters:
            return False
        return any(value not in (None, "") for value in filters.values())

    def normalize_text(self, value: str | None) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    def tokenize_query(self, query: str) -> list[str]:
        normalized = self.normalize_text(query)
        if not normalized:
            return []
        tokens = [token for token in re.split(r"[\s,.;:!?()\[\]{}\"'«»/\\|-]+", normalized) if token]
        return list(dict.fromkeys(tokens))

    def get_publication_search_values(self, publication: Publication) -> dict[str, list[str]]:
        return {
            "title": [self.normalize_text(publication.title)],
            "authors": [self.normalize_text(item.full_name) for item in publication.authors.all()],
            "keywords": [self.normalize_text(item.name) for item in publication.keywords.all()],
            "publishers": [self.normalize_text(item.name) for item in publication.publishers.all()],
            "places": [self.normalize_text(item.name) for item in publication.publication_places.all()],
            "supervisors": [self.normalize_text(item.full_name) for item in publication.scientific_supervisors.all()],
        }

    def calculate_keyword_score(self, publication: Publication, query: str) -> int:
        normalized_query = self.normalize_text(query)
        if not normalized_query:
            return 0

        tokens = self.tokenize_query(query)
        values = self.get_publication_search_values(publication)
        title = values["title"][0] if values["title"] else ""
        score = 0

        if title == normalized_query:
            score += 220
        elif title.startswith(normalized_query):
            score += 150
        elif f" {normalized_query} " in f" {title} ":
            score += 125
        elif normalized_query in title:
            score += 100

        phrase_weights = {
            "authors": 70,
            "keywords": 60,
            "publishers": 45,
            "places": 35,
            "supervisors": 35,
        }
        token_weights = {
            "title": 22,
            "authors": 10,
            "keywords": 9,
            "publishers": 6,
            "places": 5,
            "supervisors": 5,
        }

        for field_name, weight in phrase_weights.items():
            field_values = values[field_name]
            if any(value == normalized_query for value in field_values):
                score += weight + 12
            elif any(normalized_query in value for value in field_values):
                score += weight

        for token in tokens:
            if token in title:
                score += token_weights["title"]
            for field_name, weight in token_weights.items():
                if field_name == "title":
                    continue
                if any(token in value for value in values[field_name]):
                    score += weight

        return score

    def sort_publications(self, publications: list[Publication], sort_by: str = "relevance", default_sort: str = "newest") -> list[Publication]:
        publications = list(publications)
        sort_key = sort_by or default_sort
        if sort_key == "relevance":
            sort_key = default_sort

        if sort_key == "newest":
            publications.sort(key=lambda item: (item.uploaded_at, item.pk), reverse=True)
        elif sort_key == "oldest":
            publications.sort(key=lambda item: (item.uploaded_at, item.pk))
        elif sort_key == "year_desc":
            publications.sort(key=lambda item: (item.publication_year is None, -(item.publication_year or -1), -item.pk))
        elif sort_key == "year_asc":
            publications.sort(key=lambda item: (item.publication_year is None, item.publication_year or 10**9, item.pk))
        elif sort_key == "title_asc":
            publications.sort(key=lambda item: (self.normalize_text(item.title), item.pk))
        elif sort_key == "title_desc":
            publications.sort(key=lambda item: (self.normalize_text(item.title), item.pk), reverse=True)
        else:
            publications.sort(key=lambda item: (item.uploaded_at, item.pk), reverse=True)
        return publications

    def filter_publications_by_score(self, publications: list[Publication], min_score: float | int) -> list[Publication]:
        threshold = float(min_score or 0.0)
        if threshold <= 0:
            return list(publications)
        return [publication for publication in publications if float(getattr(publication, "search_score", 0.0) or 0.0) >= threshold]

    def _collect_publications(self, queryset: QuerySet[Publication], publication_ids: Iterable[int]) -> dict[int, Publication]:
        ids = list(dict.fromkeys(int(pk) for pk in publication_ids))
        if not ids:
            return {}
        return {publication.pk: publication for publication in queryset.filter(pk__in=ids)}

    def _build_excerpt(self, text: str) -> str:
        clean = self.normalize_text(text)
        limit = int(getattr(settings, "SEARCH_EXCERPT_CHARS", 260))
        if len(clean) <= limit:
            return clean
        return f"{clean[: limit - 1].rstrip()}…"

    def _lexical_bonus(self, query: str, title: str, text: str) -> float:
        normalized_query = self.normalize_text(query)
        if not normalized_query:
            return 0.0
        tokens = self.tokenize_query(query)
        title_normalized = self.normalize_text(title)
        text_normalized = self.normalize_text(text)
        if not tokens:
            return 0.0

        bonus = 0.0
        if normalized_query in title_normalized:
            bonus += 0.12
        elif any(token in title_normalized for token in tokens):
            bonus += 0.06

        matched_tokens = sum(1 for token in tokens if token in text_normalized)
        bonus += 0.08 * (matched_tokens / len(tokens))
        return bonus

    def _build_rerank_document(self, publication: Publication, best_chunk_text: str = "") -> str:
        max_chars = int(getattr(settings, "SEARCH_RERANK_MAX_TEXT_CHARS", 2400))
        metadata_parts = [publication.title]
        authors = ", ".join(author.full_name for author in publication.authors.all())
        if authors:
            metadata_parts.append(f"Авторы: {authors}")
        if publication.publication_type:
            metadata_parts.append(f"Тип: {publication.publication_type.name}")
        if publication.publication_subtype:
            metadata_parts.append(f"Подтип: {publication.publication_subtype.name}")
        keywords = ", ".join(keyword.name for keyword in publication.keywords.all())
        if keywords:
            metadata_parts.append(f"Ключевые слова: {keywords}")
        if publication.publication_year:
            metadata_parts.append(f"Год: {publication.publication_year}")

        text_body = self.normalize_text(best_chunk_text or publication.contents or "")
        if text_body:
            metadata_parts.append(f"Фрагмент: {text_body[:max_chars]}")
        return "\n".join(part for part in metadata_parts if part).strip()[: max_chars + 600]

    def _rerank_publications(
        self,
        query: str,
        publications: list[Publication],
        vector_store: VectorStoreService,
        *,
        threshold: float,
        default_source: str,
    ) -> list[Publication]:
        if not query or not publications or not getattr(settings, "SEARCH_RERANK_ENABLED", True):
            return self.filter_publications_by_score(publications, threshold)

        rerank_top_k = max(1, int(getattr(settings, "SEARCH_RERANK_TOP_K", 40)))
        candidate_count = min(len(publications), rerank_top_k)
        candidates = list(publications[:candidate_count])
        candidate_documents = [
            self._build_rerank_document(publication, getattr(publication, "best_chunk_text", "")) for publication in candidates
        ]
        reranked = vector_store.rerank_documents(query=query, documents=candidate_documents, top_k=candidate_count)
        if not reranked:
            return self.filter_publications_by_score(candidates, threshold)

        reranked_publications: list[Publication] = []
        for rank, item in enumerate(reranked, start=1):
            publication = candidates[item["index"]]
            publication.retrieval_score = float(getattr(publication, "search_score", 0.0) or 0.0)
            publication.search_score = float(item["score"])
            publication.search_rank = rank
            publication.search_source = getattr(publication, "search_source", default_source) or default_source
            publication.search_stage = "reranked"
            reranked_publications.append(publication)

        return self.filter_publications_by_score(reranked_publications, threshold)

    def _aggregate_chunk_hits(self, queryset: QuerySet[Publication], hits: list[dict], query: str, source: str) -> list[Publication]:
        publications_by_id = self._collect_publications(queryset, [hit["publication_id"] for hit in hits])
        if not publications_by_id:
            return []

        aggregated: dict[int, dict[str, Any]] = {}
        for rank, hit in enumerate(hits, start=1):
            publication = publications_by_id.get(hit["publication_id"])
            if publication is None:
                continue
            entry = aggregated.setdefault(
                publication.pk,
                {
                    "publication": publication,
                    "best_score": float("-inf"),
                    "chunk_scores": [],
                    "best_chunk_text": "",
                    "matched_chunks": 0,
                    "best_rank": rank,
                },
            )
            entry["matched_chunks"] += 1
            entry["chunk_scores"].append(float(hit["score"]))
            if hit["score"] > entry["best_score"]:
                entry["best_score"] = float(hit["score"])
                entry["best_chunk_text"] = hit.get("chunk_text") or ""
                entry["best_rank"] = rank

        results: list[Publication] = []
        for payload in aggregated.values():
            publication = payload["publication"]
            top_scores = sorted(payload["chunk_scores"], reverse=True)[:2]
            aggregate_score = max(top_scores) if top_scores else 0.0
            if len(top_scores) > 1:
                aggregate_score += 0.15 * top_scores[1]
            aggregate_score += 0.04 * math.log1p(max(0, payload["matched_chunks"] - 1))
            aggregate_score += self._lexical_bonus(query, publication.title, payload["best_chunk_text"])
            publication.search_score = float(aggregate_score)
            publication.search_rank = payload["best_rank"]
            publication.search_source = source
            publication.search_stage = "retrieved"
            publication.best_chunk_text = payload["best_chunk_text"]
            publication.search_excerpt = self._build_excerpt(payload["best_chunk_text"])
            results.append(publication)

        results.sort(key=lambda item: (item.search_score, -item.search_rank, item.uploaded_at, item.pk), reverse=True)
        return results


class KeywordSearchService(BaseSearchService):
    def search(self, query: str = "", filters: dict[str, Any] | None = None, sort_by: str = "relevance") -> list[Publication]:
        queryset = self.apply_filters(self.get_base_queryset(), filters)
        publications = list(queryset)
        query = (query or "").strip()

        if query:
            scored_results = []
            for publication in publications:
                keyword_score = self.calculate_keyword_score(publication, query)
                if keyword_score <= 0:
                    continue
                publication.search_score = float(keyword_score)
                publication.search_source = "keyword"
                publication.search_stage = "retrieved"
                scored_results.append(publication)

            publications = self.filter_publications_by_score(
                scored_results,
                getattr(settings, "SEARCH_KEYWORD_MIN_SCORE", 20),
            )
            publications = sorted(
                publications,
                key=lambda item: (item.search_score, item.uploaded_at, item.pk),
                reverse=True,
            )
            if sort_by != "relevance":
                publications = self.sort_publications(publications, sort_by=sort_by)
            return publications

        return self.sort_publications(publications, sort_by=sort_by, default_sort="newest")


class SemanticSearchService(BaseSearchService):
    def __init__(self):
        self.vector_store = VectorStoreService()

    def search(self, query: str = "", filters: dict[str, Any] | None = None, limit: int = 200, sort_by: str = "relevance") -> list[Publication]:
        queryset = self.apply_filters(self.get_base_queryset(), filters)
        query = (query or "").strip()
        if not query:
            return self.sort_publications(list(queryset), sort_by=sort_by, default_sort="newest")

        chunk_limit = max(limit, int(getattr(settings, "MILVUS_CHUNK_CANDIDATE_POOL", 400)))
        dense_hits = self.vector_store.search_dense_chunks(query=query, limit=chunk_limit)
        publications = self._aggregate_chunk_hits(queryset, dense_hits, query=query, source="semantic")
        publications = self._rerank_publications(
            query,
            publications,
            self.vector_store,
            threshold=float(getattr(settings, "SEARCH_SEMANTIC_MIN_SCORE", 0.2)),
            default_source="semantic",
        )
        if sort_by != "relevance":
            publications = self.sort_publications(publications, sort_by=sort_by)
        return publications[:limit]


class HybridSearchService(BaseSearchService):
    def __init__(self):
        self.keyword = KeywordSearchService()
        self.vector_store = VectorStoreService()

    def search(self, query: str = "", filters: dict[str, Any] | None = None, limit: int = 200, sort_by: str = "relevance") -> list[Publication]:
        query = (query or "").strip()
        if not query:
            return self.keyword.search(query="", filters=filters, sort_by=sort_by)

        queryset = self.apply_filters(self.get_base_queryset(), filters)
        chunk_limit = max(limit, int(getattr(settings, "MILVUS_CHUNK_CANDIDATE_POOL", 400)))
        hybrid_hits = self.vector_store.search_hybrid_chunks(query=query, limit=chunk_limit)
        semantic_results = self._aggregate_chunk_hits(queryset, hybrid_hits, query=query, source="hybrid-semantic")
        semantic_results = self._rerank_publications(
            query,
            semantic_results,
            self.vector_store,
            threshold=float(getattr(settings, "SEARCH_HYBRID_MIN_SCORE", 0.2)),
            default_source="hybrid-semantic",
        )

        semantic_head_limit = min(limit, max(1, int(getattr(settings, "HYBRID_SEMANTIC_HEAD_LIMIT", 30))))
        semantic_head = semantic_results[:semantic_head_limit]
        used_ids = {publication.pk for publication in semantic_head}

        keyword_tail: list[Publication] = []
        keyword_results = self.keyword.search(query=query, filters=filters, sort_by="relevance")
        for publication in keyword_results:
            if publication.pk in used_ids:
                continue
            publication.search_source = "hybrid-keyword"
            publication.search_stage = getattr(publication, "search_stage", "retrieved")
            keyword_tail.append(publication)
            used_ids.add(publication.pk)
            if len(semantic_head) + len(keyword_tail) >= limit:
                break

        filter_tail: list[Publication] = []
        if len(semantic_head) + len(keyword_tail) < limit and self.has_active_filters(filters):
            filter_only_results = self.keyword.search(query="", filters=filters, sort_by="newest")
            for publication in filter_only_results:
                if publication.pk in used_ids:
                    continue
                publication.search_source = "hybrid-filter"
                publication.search_score = getattr(publication, "search_score", None)
                publication.search_stage = "filtered"
                filter_tail.append(publication)
                used_ids.add(publication.pk)
                if len(semantic_head) + len(keyword_tail) + len(filter_tail) >= limit:
                    break

        combined_results = semantic_head + keyword_tail + filter_tail
        if sort_by != "relevance":
            combined_results = self.sort_publications(combined_results, sort_by=sort_by)
        return combined_results[:limit]
