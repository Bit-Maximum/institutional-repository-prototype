from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Max

from apps.publications.models import (
    Author,
    Keyword,
    PublicationLanguage,
    PublicationPeriodicity,
    PublicationPlace,
    PublicationSubtype,
    PublicationType,
    PublicationUserEngagement,
    Publisher,
)
from apps.search.models import SearchQuery
from apps.search.services import HybridSearchService, KeywordSearchService


@dataclass
class RecommendationContext:
    has_history: bool
    source_queries: list[SearchQuery]
    results: list[Any]


class RecommendationService:
    def __init__(self) -> None:
        self.history_limit = int(getattr(settings, "RECOMMENDATION_HISTORY_LIMIT", 5))
        self.per_query_limit = int(getattr(settings, "RECOMMENDATION_PER_QUERY_LIMIT", 16))
        self.weight_decay = float(getattr(settings, "RECOMMENDATION_RECENCY_DECAY", 0.78))
        self.viewed_factor = float(getattr(settings, "RECOMMENDATION_VIEWED_FACTOR", 0.78))
        self.downloaded_factor = float(getattr(settings, "RECOMMENDATION_DOWNLOADED_FACTOR", 0.45))
        self.keyword_fallback_limit = int(getattr(settings, "RECOMMENDATION_KEYWORD_FALLBACK_LIMIT", 4))
        self.max_results = int(getattr(settings, "RECOMMENDATION_MAX_RESULTS", 50))
        self.cache_timeout = int(getattr(settings, "RECOMMENDATION_CACHE_TIMEOUT", 300))
        self.preload_pages = max(1, int(getattr(settings, "RECOMMENDATION_PRELOAD_PAGES", 2)))
        self.entry_cache_search_limit = int(getattr(settings, "RECOMMENDATION_ENTRY_CACHE_SEARCH_LIMIT", 2))

    def build_for_user(self, user, *, page: int = 1, page_size: int | None = None) -> RecommendationContext:
        if not getattr(user, "is_authenticated", False):
            return RecommendationContext(has_history=False, source_queries=[], results=[])

        entries = self._get_recent_queries(user)
        if not entries:
            return RecommendationContext(has_history=False, source_queries=[], results=[])

        resolved_page_size = max(1, int(page_size or getattr(settings, "SEARCH_PAGE_SIZE", 10)))
        requested_page = max(1, int(page or 1))
        target_results = self._resolve_target_results(
            entries=entries,
            requested_page=requested_page,
            page_size=resolved_page_size,
        )
        self._annotate_source_queries(entries)
        cache_key = self._build_cache_key(user, entries, target_results)
        cached_payloads = cache.get(cache_key)
        if cached_payloads is not None:
            publications = self._hydrate_cached_results(cached_payloads)
            return RecommendationContext(has_history=True, source_queries=entries, results=publications)

        aggregated: dict[int, dict[str, Any]] = {}
        total_query_count = len(entries)
        per_query_limit = self._resolve_per_query_limit(total_query_count, target_results)
        unresolved_entries: list[tuple[int, SearchQuery, str, dict[str, Any], bool]] = []

        for idx, entry in enumerate(entries):
            query = (entry.query_text or "").strip()
            filters = self._deserialize_filters(entry.filters)
            if not (query or any(value not in (None, "", False) for value in filters.values())):
                continue
            cached_results, partial_cache = self._get_cached_entry_results(entry=entry, limit=per_query_limit)
            if cached_results is None:
                unresolved_entries.append((idx, entry, query, filters, False))
                continue
            self._accumulate_entry_results(
                aggregated=aggregated,
                entry=entry,
                results=cached_results,
                query=query,
                filters=filters,
                query_index=idx,
            )
            if partial_cache:
                unresolved_entries.append((idx, entry, query, filters, True))

        search_budget = self.entry_cache_search_limit
        for idx, entry, query, filters, partial_cache in unresolved_entries:
            if aggregated and len(aggregated) >= target_results and (search_budget <= 0 or partial_cache):
                break
            results = self._search_and_cache_entry_results(entry=entry, query=query, filters=filters, limit=per_query_limit)
            if not results:
                continue
            self._accumulate_entry_results(
                aggregated=aggregated,
                entry=entry,
                results=results,
                query=query,
                filters=filters,
                query_index=idx,
            )
            search_budget -= 1

        if not aggregated:
            return RecommendationContext(has_history=True, source_queries=entries, results=[])

        interactions = {
            item.publication_id: item
            for item in PublicationUserEngagement.objects.filter(user=user, publication_id__in=aggregated.keys())
        }

        ordered: list[Any] = []
        for publication_id, state in aggregated.items():
            publication = state["publication"]
            score = float(state["score"])
            engagement = interactions.get(publication_id)
            if engagement and engagement.has_been_downloaded:
                score *= self.downloaded_factor
            elif engagement and engagement.has_been_viewed:
                score *= self.viewed_factor
            publication.recommendation_score = score
            publication.recommendation_queries = state["support_queries"]
            publication.recommendation_rank_hint = state["best_rank"]
            publication.recommendation_from_recent_query = state["best_query_position"]
            publication.user_has_viewed = bool(engagement and engagement.has_been_viewed)
            publication.user_has_downloaded = bool(engagement and engagement.has_been_downloaded)
            publication.user_view_count = int(getattr(engagement, "view_count", 0) or 0)
            publication.user_download_count = int(getattr(engagement, "download_count", 0) or 0)
            ordered.append(publication)

        ordered.sort(
            key=lambda item: (
                -(float(getattr(item, "recommendation_score", 0.0) or 0.0)),
                int(getattr(item, "user_has_downloaded", False)),
                int(getattr(item, "user_has_viewed", False)),
                getattr(item, "publication_year", 0) or 0,
                item.pk,
            )
        )
        ordered = ordered[:target_results]
        cache.set(cache_key, self._serialize_results(ordered), self.cache_timeout)
        return RecommendationContext(has_history=True, source_queries=entries, results=ordered)


    def prime_from_search_entry(self, entry: SearchQuery, results: list[Any]) -> None:
        if not entry or not getattr(entry, "pk", None):
            return
        limit = self._resolve_prime_limit()
        trimmed = list(results[:limit])
        if not trimmed:
            return
        cache.set(self._build_entry_cache_key(entry, limit), self._serialize_entry_results(trimmed), self.cache_timeout)

    def _resolve_per_query_limit(self, total_query_count: int, target_results: int | None = None) -> int:
        effective_target = int(target_results or self.max_results)
        dynamic_floor = max(6, math.ceil(effective_target / max(total_query_count, 1)) + 4)
        return min(effective_target, max(self.per_query_limit, dynamic_floor))

    def _resolve_prime_limit(self) -> int:
        return min(self.max_results, max(self.per_query_limit * 2, math.ceil(self.max_results / 2) + 4))
    def _resolve_target_results(self, *, entries: list[SearchQuery], requested_page: int, page_size: int) -> int:
        base_window = page_size * max(self.preload_pages + requested_page, requested_page * 2)
        cache_rich_window = self._resolve_prime_limit() * max(len(entries), 1)
        return max(self.max_results, base_window, cache_rich_window)

    def _annotate_source_queries(self, entries: list[SearchQuery]) -> None:
        for entry in entries:
            filters = self._deserialize_filters(entry.filters)
            mode = self._extract_mode_label(filters)
            entry.recommendation_query_label = (entry.query_text or "").strip() or "Поиск только по фильтрам"
            entry.recommendation_mode_label = mode
            entry.recommendation_filter_label = self._build_filter_label(filters)

    def _build_entry_cache_key(self, entry: SearchQuery, limit: int) -> str:
        raw_key = f"recommendation-entry:{entry.pk}:{limit}:{int(entry.created_at.timestamp()) if entry.created_at else 0}"
        digest = hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"recommendation-entry:{digest}"

    def _serialize_entry_results(self, publications: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "publication_id": publication.pk,
                "search_score": float(getattr(publication, "search_score", 0.0) or 0.0),
                "search_source": str(getattr(publication, "search_source", "") or ""),
            }
            for publication in publications
        ]

    def _hydrate_entry_results(self, payloads: list[dict[str, Any]]) -> list[Any]:
        publication_ids = [int(item["publication_id"]) for item in payloads if item.get("publication_id")]
        if not publication_ids:
            return []
        queryset = KeywordSearchService().get_base_queryset(include_chunks=False)
        publication_map = {publication.pk: publication for publication in queryset.filter(pk__in=publication_ids)}
        ordered: list[Any] = []
        for payload in payloads:
            publication = publication_map.get(int(payload["publication_id"]))
            if publication is None:
                continue
            publication.search_score = float(payload.get("search_score", 0.0) or 0.0)
            publication.search_source = str(payload.get("search_source", "") or "")
            ordered.append(publication)
        return ordered

    def _get_cached_entry_results(self, *, entry: SearchQuery, limit: int) -> tuple[list[Any] | None, bool]:
        cache_key = self._build_entry_cache_key(entry, limit)
        cached_payloads = cache.get(cache_key)
        if cached_payloads is not None:
            hydrated = self._hydrate_entry_results(cached_payloads)
            return (hydrated if hydrated else []), False

        fallback_limits = []
        for candidate in (self._resolve_prime_limit(), self.per_query_limit, 16, 14, 8, 6):
            candidate = min(limit, max(1, int(candidate)))
            if candidate == limit or candidate in fallback_limits:
                continue
            fallback_limits.append(candidate)
        for candidate in fallback_limits:
            cached_payloads = cache.get(self._build_entry_cache_key(entry, candidate))
            if cached_payloads is None:
                continue
            hydrated = self._hydrate_entry_results(cached_payloads)
            return (hydrated if hydrated else []), True
        return None, False

    def _search_and_cache_entry_results(self, *, entry: SearchQuery, query: str, filters: dict[str, Any], limit: int) -> list[Any]:
        results = self._search_for_entry(query=query, filters=filters, limit=limit)
        if results:
            cache.set(self._build_entry_cache_key(entry, limit), self._serialize_entry_results(results), self.cache_timeout)
        return results


    def _accumulate_entry_results(
        self,
        *,
        aggregated: dict[int, dict[str, Any]],
        entry: SearchQuery,
        results: list[Any],
        query: str,
        filters: dict[str, Any],
        query_index: int,
    ) -> None:
        if not results:
            return
        positive_scores = [float(getattr(item, "search_score", 0.0) or 0.0) for item in results if float(getattr(item, "search_score", 0.0) or 0.0) > 0]
        best_score = max(positive_scores) if positive_scores else 1.0
        query_weight = self.weight_decay ** query_index
        query_label = self._build_support_query_label(entry=entry, filters=filters, query_index=query_index)

        for rank, publication in enumerate(results, start=1):
            normalized_score = (float(getattr(publication, "search_score", 0.0) or 0.0) / best_score) if best_score > 0 else 0.0
            rank_bonus = 1.0 / rank
            contribution = query_weight * ((0.72 * normalized_score) + (0.28 * rank_bonus))

            entry_state = aggregated.setdefault(
                publication.pk,
                {
                    "publication": publication,
                    "score": 0.0,
                    "support_queries": [],
                    "best_rank": rank,
                    "best_query_position": query_index + 1,
                },
            )
            entry_state["score"] += contribution
            entry_state["best_rank"] = min(entry_state["best_rank"], rank)
            entry_state["best_query_position"] = min(entry_state["best_query_position"], query_index + 1)
            if query_label not in entry_state["support_queries"]:
                entry_state["support_queries"].append(query_label)

    def _build_support_query_label(self, *, entry: SearchQuery, filters: dict[str, Any], query_index: int) -> str:
        base_label = getattr(entry, "recommendation_query_label", None) or (entry.query_text or "").strip() or "Поиск только по фильтрам"
        mode_label = getattr(entry, "recommendation_mode_label", None) or self._extract_mode_label(filters)
        filter_label = getattr(entry, "recommendation_filter_label", None) or self._build_filter_label(filters)
        if base_label == "Поиск только по фильтрам" and filter_label:
            return f"{base_label} · {mode_label} · {filter_label}"
        if base_label:
            return f"{base_label} · {mode_label}"
        if filter_label:
            return f"{filter_label} · {mode_label}"
        return f"Запрос #{query_index + 1} · {mode_label}"

    def _build_cache_key(self, user, entries: list[SearchQuery], target_results: int) -> str:
        query_signature = "|".join(
            f"{entry.pk}:{int(entry.created_at.timestamp())}:{self._normalize_query(entry.query_text)}:{(entry.filters or '').strip()}"
            for entry in entries
        )
        engagement_meta = PublicationUserEngagement.objects.filter(user=user).aggregate(
            updated_at=Max("updated_at"),
            count=Count("id"),
        )
        updated_at = engagement_meta.get("updated_at")
        engagement_signature = f"{engagement_meta.get('count', 0)}:{int(updated_at.timestamp()) if updated_at else 0}"
        raw_key = f"recommendations:{user.pk}:{target_results}:{query_signature}:{engagement_signature}"
        digest = hashlib.md5(raw_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"user-recommendations:{digest}"

    def _serialize_results(self, publications: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "publication_id": publication.pk,
                "recommendation_score": float(getattr(publication, "recommendation_score", 0.0) or 0.0),
                "recommendation_queries": list(getattr(publication, "recommendation_queries", []) or []),
                "recommendation_rank_hint": int(getattr(publication, "recommendation_rank_hint", 0) or 0),
                "recommendation_from_recent_query": int(getattr(publication, "recommendation_from_recent_query", 0) or 0),
                "user_has_viewed": bool(getattr(publication, "user_has_viewed", False)),
                "user_has_downloaded": bool(getattr(publication, "user_has_downloaded", False)),
                "user_view_count": int(getattr(publication, "user_view_count", 0) or 0),
                "user_download_count": int(getattr(publication, "user_download_count", 0) or 0),
            }
            for publication in publications
        ]

    def _hydrate_cached_results(self, payloads: list[dict[str, Any]]) -> list[Any]:
        publication_ids = [int(item["publication_id"]) for item in payloads if item.get("publication_id")]
        if not publication_ids:
            return []
        queryset = KeywordSearchService().get_base_queryset()
        publication_map = {publication.pk: publication for publication in queryset.filter(pk__in=publication_ids)}
        ordered: list[Any] = []
        for payload in payloads:
            publication = publication_map.get(int(payload["publication_id"]))
            if publication is None:
                continue
            publication.recommendation_score = float(payload.get("recommendation_score", 0.0) or 0.0)
            publication.recommendation_queries = list(payload.get("recommendation_queries", []) or [])
            publication.recommendation_rank_hint = int(payload.get("recommendation_rank_hint", 0) or 0)
            publication.recommendation_from_recent_query = int(payload.get("recommendation_from_recent_query", 0) or 0)
            publication.user_has_viewed = bool(payload.get("user_has_viewed", False))
            publication.user_has_downloaded = bool(payload.get("user_has_downloaded", False))
            publication.user_view_count = int(payload.get("user_view_count", 0) or 0)
            publication.user_download_count = int(payload.get("user_download_count", 0) or 0)
            ordered.append(publication)
        return ordered

    def _get_recent_queries(self, user) -> list[SearchQuery]:
        queryset = SearchQuery.objects.filter(user=user).order_by("-created_at", "-id")
        deduplicated: list[SearchQuery] = []
        seen: set[tuple[str, str]] = set()
        for entry in queryset:
            normalized_query = self._normalize_query(entry.query_text)
            filters_blob = (entry.filters or "").strip()
            key = (normalized_query, filters_blob)
            if key in seen:
                continue
            if not normalized_query and not filters_blob:
                continue
            seen.add(key)
            deduplicated.append(entry)
            if len(deduplicated) >= self.history_limit:
                break
        return deduplicated

    def _search_for_entry(self, *, query: str, filters: dict[str, Any], limit: int) -> list[Any]:
        results = HybridSearchService().search(
            query=query,
            filters=filters,
            limit=limit,
            sort_by="relevance",
            relative_floor=getattr(settings, "RECOMMENDATION_RELATIVE_FLOOR", None),
        )
        if results:
            return results[:limit]
        if not query:
            return []
        fallback_limit = min(self.keyword_fallback_limit, max(1, limit))
        fallback = KeywordSearchService().search(
            query=query,
            filters=filters,
            sort_by="relevance",
            relative_floor=None,
            include_fulltext=False,
        )
        return fallback[:fallback_limit]

    def _extract_mode_label(self, filters: dict[str, Any]) -> str:
        mode = (filters.get("mode") or "hybrid").strip().lower()
        mapping = {
            "keyword": "Традиционный поиск",
            "semantic": "Семантический поиск",
            "hybrid": "Гибридный поиск",
        }
        return mapping.get(mode, "Гибридный поиск")

    def _deserialize_filters(self, filters_blob: str | None) -> dict[str, Any]:
        if not filters_blob:
            return {}
        try:
            payload = json.loads(filters_blob)
        except json.JSONDecodeError:
            return {}

        model_map = {
            "publication_type": PublicationType,
            "publication_subtype": PublicationSubtype,
            "language": PublicationLanguage,
            "periodicity": PublicationPeriodicity,
            "author": Author,
            "keyword": Keyword,
            "publisher": Publisher,
            "publication_place": PublicationPlace,
        }
        result: dict[str, Any] = {}
        mode = payload.get("mode")
        if mode not in (None, ""):
            result["mode"] = str(mode)
        for key, model in model_map.items():
            value = payload.get(key)
            if value not in (None, ""):
                try:
                    result[key] = model.objects.filter(pk=int(value)).first()
                except (TypeError, ValueError):
                    result[key] = None
        for key in ("year_from", "year_to"):
            value = payload.get(key)
            if value not in (None, ""):
                try:
                    result[key] = int(value)
                except (TypeError, ValueError):
                    result[key] = None
        result["include_fulltext_in_keyword"] = bool(payload.get("include_fulltext_in_keyword"))
        strictness = payload.get("relative_score_floor") or payload.get("strictness")
        if strictness not in (None, ""):
            result["relative_score_floor"] = strictness
        return result

    def _build_filter_label(self, filters: dict[str, Any]) -> str:
        labels: list[str] = []
        for key in ("publication_type", "publication_subtype", "language", "keyword", "author", "publisher", "publication_place"):
            value = filters.get(key)
            name = getattr(value, "name", None) or getattr(value, "full_name", None)
            if name:
                labels.append(str(name))
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")
        if year_from or year_to:
            labels.append(f"годы {year_from or '…'}–{year_to or '…'}")
        return ", ".join(labels[:4])

    def _normalize_query(self, value: str | None) -> str:
        return " ".join((value or "").strip().lower().split())
