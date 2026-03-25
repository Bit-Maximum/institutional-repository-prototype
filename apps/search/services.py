from __future__ import annotations

import math
import re
from typing import Any, Iterable

from django.conf import settings
from django.db.models import QuerySet

from apps.ingestion.services import detect_script_kind, is_reference_heavy_text, is_table_of_contents_text
from apps.publications.models import Publication, PublicationChunk
from apps.vector_store.services import VectorStoreService


SEMANTIC_SEARCH_STOPWORDS = {
    "и", "в", "во", "на", "по", "о", "об", "обо", "для", "при", "с", "со", "к", "ко", "у", "от", "до",
    "из", "за", "над", "под", "или", "не", "как", "что", "это", "эта", "этот", "эти", "информация", "сведения",
    "about", "the", "and", "for", "with", "from", "into", "this", "that", "information",
}


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

    def get_base_queryset(self, *, include_chunks: bool = False) -> QuerySet[Publication]:
        queryset = Publication.objects.filter(is_draft=False).select_related(*self.select_related_fields).prefetch_related(
            *self.prefetch_related_fields
        )
        if include_chunks:
            queryset = queryset.prefetch_related("chunks")
        return queryset

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

    def semantic_tokens(self, query: str) -> list[str]:
        return [token for token in self.tokenize_query(query) if len(token) >= 3 and token not in SEMANTIC_SEARCH_STOPWORDS]

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

    def calculate_fulltext_keyword_support(self, publication: Publication, query: str) -> tuple[int, str, str]:
        normalized_query = self.normalize_text(query)
        if not normalized_query:
            return 0, "", ""

        tokens = self.semantic_tokens(query) or self.tokenize_query(query)
        best_score = 0
        best_text = ""
        best_label = ""

        for chunk in publication.chunks.all():
            normalized_chunk = self.normalize_text(chunk.text)
            if not normalized_chunk:
                continue
            coverage = self._query_token_coverage(query, normalized_chunk)
            score = 0
            if normalized_query in normalized_chunk:
                score += 120
            elif coverage >= 1.0 and len(tokens) >= 2:
                score += 88
            elif coverage > 0:
                score += int(68 * coverage)

            if score > 0 and chunk.source_kind == "metadata":
                score = int(score * 0.82)
            if score > best_score:
                best_score = score
                best_text = chunk.text
                best_label = getattr(chunk, "page_label", "")

        contents_text = self.normalize_text(publication.contents)
        if contents_text:
            contents_score = 0
            coverage = self._query_token_coverage(query, publication.contents)
            if normalized_query in contents_text:
                contents_score += 72
            elif coverage > 0:
                contents_score += int(42 * coverage)
            if contents_score > best_score:
                best_score = contents_score
                best_text = publication.contents
                best_label = "аннотация"

        return best_score, best_text, best_label

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

    def filter_publications_by_relative_floor(
        self,
        publications: list[Publication],
        relative_floor: float | str | None,
    ) -> list[Publication]:
        if relative_floor in (None, ""):
            return list(publications)
        ratio = float(relative_floor or 0.0)
        if ratio <= 0:
            return list(publications)
        positive_scores = [float(getattr(publication, "search_score", 0.0) or 0.0) for publication in publications if float(getattr(publication, "search_score", 0.0) or 0.0) > 0]
        if not positive_scores:
            return []
        best_score = max(positive_scores)
        threshold = best_score * ratio
        filtered = [publication for publication in publications if float(getattr(publication, "search_score", 0.0) or 0.0) >= threshold]
        for publication in filtered:
            publication.relative_score_threshold = threshold
            publication.relative_score_ratio = ratio
            publication.best_result_score = best_score
        return filtered

    def resolve_relative_floor(self, mode: str, explicit_value: float | str | None = None) -> float:
        if explicit_value not in (None, ""):
            return float(explicit_value)
        defaults = {
            "keyword": float(getattr(settings, "SEARCH_KEYWORD_RELATIVE_CUTOFF", 0.0)),
            "semantic": float(getattr(settings, "SEARCH_SEMANTIC_RELATIVE_CUTOFF", 0.0)),
            "hybrid": float(getattr(settings, "SEARCH_HYBRID_RELATIVE_CUTOFF", 0.0)),
        }
        return float(defaults.get(mode, 0.0))

    def _collect_publications(self, queryset: QuerySet[Publication], publication_ids: Iterable[int]) -> dict[int, Publication]:
        ids = list(dict.fromkeys(int(pk) for pk in publication_ids))
        if not ids:
            return {}
        return {publication.pk: publication for publication in queryset.filter(pk__in=ids)}

    def _collect_chunk_metadata(self, chunk_ids: Iterable[int]) -> dict[int, PublicationChunk]:
        ids = list(dict.fromkeys(int(pk) for pk in chunk_ids))
        if not ids:
            return {}
        return {
            chunk.pk: chunk
            for chunk in PublicationChunk.objects.filter(pk__in=ids).only(
                "id", "source_kind", "page_start", "page_end", "publication_id"
            )
        }

    def _build_excerpt(self, text: str) -> str:
        clean = self.normalize_text(text)
        limit = int(getattr(settings, "SEARCH_EXCERPT_CHARS", 260))
        if len(clean) <= limit:
            return clean
        return f"{clean[: limit - 1].rstrip()}…"

    def _query_token_coverage(self, query: str, *texts: str) -> float:
        tokens = self.semantic_tokens(query)
        if not tokens:
            return 0.0
        haystack = " ".join(self.normalize_text(text) for text in texts if text)
        matched = sum(1 for token in tokens if token in haystack)
        return matched / len(tokens)

    def _query_signals(self, query: str, *texts: str) -> dict[str, Any]:
        phrase = self.normalize_text(query)
        tokens = self.semantic_tokens(query)
        haystack = " ".join(self.normalize_text(text) for text in texts if text)
        matched_tokens = [token for token in tokens if token in haystack]
        return {
            "phrase": phrase,
            "tokens": tokens,
            "haystack": haystack,
            "coverage": (len(matched_tokens) / len(tokens)) if tokens else 0.0,
            "matched_tokens": matched_tokens,
            "exact_phrase": bool(phrase and len(phrase) >= 5 and phrase in haystack),
        }

    def _language_alignment_multiplier(self, query: str, publication: Publication, chunk_text: str) -> float:
        query_script = detect_script_kind(query)
        if query_script not in {"cyrillic", "latin"}:
            return 1.0

        text_script = detect_script_kind(chunk_text or publication.title)
        language_name = self.normalize_text(getattr(getattr(publication, "language", None), "name", ""))
        token_coverage = self._query_token_coverage(query, publication.title, chunk_text, getattr(publication, "contents", ""))

        multiplier = 1.0
        if text_script in {"cyrillic", "latin"} and text_script != query_script:
            multiplier *= float(getattr(settings, "SEARCH_CROSS_SCRIPT_SCORE_FACTOR", 0.42))
            if token_coverage <= 0:
                multiplier *= float(getattr(settings, "SEARCH_ZERO_OVERLAP_CROSS_SCRIPT_FACTOR", 0.30))
        elif query_script == "cyrillic" and language_name and "рус" in language_name:
            multiplier *= 1.03
        return multiplier

    def _semantic_grounding_multiplier(self, query: str, publication: Publication, chunk_text: str, *, source: str) -> float:
        keyword_texts = ", ".join(keyword.name for keyword in publication.keywords.all())
        title_text = publication.title or ""
        haystack_parts = [
            title_text,
            chunk_text,
            publication.contents or "",
            keyword_texts,
        ]
        signals = self._query_signals(query, *haystack_parts)
        coverage = signals["coverage"]
        token_count = len(signals["tokens"])
        multiplier = 1.0

        if signals["exact_phrase"]:
            boost_name = "SEARCH_HYBRID_EXACT_PHRASE_BOOST" if source.startswith("hybrid") else "SEARCH_SEMANTIC_EXACT_PHRASE_BOOST"
            default_boost = 0.44 if source.startswith("hybrid") else 0.32
            multiplier += float(getattr(settings, boost_name, default_boost))

        if coverage == 0 and token_count >= 2:
            setting_name = "SEARCH_HYBRID_ZERO_GROUNDING_SCORE_FACTOR" if source.startswith("hybrid") else "SEARCH_ZERO_GROUNDING_SCORE_FACTOR"
            default_value = 0.16 if source.startswith("hybrid") else 0.26
            multiplier *= float(getattr(settings, setting_name, default_value))
        elif 0 < coverage < 0.5 and token_count >= 2:
            multiplier *= float(getattr(settings, "SEARCH_PARTIAL_GROUNDING_SCORE_FACTOR", 0.72))
        elif coverage >= 0.5:
            multiplier *= 1.0 + float(getattr(settings, "SEARCH_TOKEN_COVERAGE_BOOST", 0.18)) * coverage

        return multiplier

    def _chunk_quality_multiplier(self, query: str, publication: Publication, chunk_text: str, source_kind: str, *, source: str) -> float:
        multiplier = 1.0
        if source_kind != "metadata" and is_reference_heavy_text(chunk_text):
            multiplier *= float(getattr(settings, "SEARCH_REFERENCE_CHUNK_SCORE_FACTOR", 0.08))
        if source_kind != "metadata" and is_table_of_contents_text(chunk_text):
            multiplier *= float(getattr(settings, "SEARCH_TOC_CHUNK_SCORE_FACTOR", 0.04))
        multiplier *= self._language_alignment_multiplier(query, publication, chunk_text)
        multiplier *= self._semantic_grounding_multiplier(query, publication, chunk_text, source=source)
        coverage = self._query_token_coverage(query, publication.title, chunk_text)
        if coverage > 0:
            multiplier += float(getattr(settings, "SEARCH_TOKEN_COVERAGE_BOOST", 0.18)) * coverage
        return multiplier

    def _lexical_bonus(self, query: str, title: str, text: str, metadata_text: str = "") -> float:
        signals = self._query_signals(query, title, text, metadata_text)
        if not signals["tokens"] and not signals["phrase"]:
            return 0.0

        title_normalized = self.normalize_text(title)
        text_normalized = self.normalize_text(text)
        metadata_normalized = self.normalize_text(metadata_text)
        phrase = signals["phrase"]
        coverage = signals["coverage"]
        bonus = 0.0

        if phrase and phrase in title_normalized:
            bonus += 0.32
        elif phrase and (phrase in text_normalized or phrase in metadata_normalized):
            bonus += 0.26

        if coverage > 0:
            bonus += 0.24 * coverage
            title_hits = sum(1 for token in signals["tokens"] if token in title_normalized)
            if title_hits:
                bonus += 0.08 * (title_hits / len(signals["tokens"]))
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
        if not query or not publications or not getattr(settings, "SEARCH_RERANK_ENABLED", False):
            return self.filter_publications_by_score(publications, threshold)

        rerank_top_k = max(1, int(getattr(settings, "SEARCH_RERANK_TOP_K", 24)))
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
        chunk_metadata = self._collect_chunk_metadata(hit["chunk_pk"] for hit in hits)
        if not publications_by_id:
            return []

        aggregated: dict[int, dict[str, Any]] = {}
        for rank, hit in enumerate(hits, start=1):
            publication = publications_by_id.get(hit["publication_id"])
            if publication is None:
                continue
            chunk = chunk_metadata.get(int(hit["chunk_pk"]))
            source_kind = getattr(chunk, "source_kind", "fulltext") or "fulltext"
            entry = aggregated.setdefault(
                publication.pk,
                {
                    "publication": publication,
                    "best_score": float("-inf"),
                    "best_raw_score": 0.0,
                    "chunk_scores": [],
                    "best_chunk_text": "",
                    "matched_chunks": 0,
                    "best_rank": rank,
                    "best_source_kind": source_kind,
                    "best_chunk_label": "",
                },
            )
            adjusted_score = float(hit["score"]) * self._chunk_quality_multiplier(
                query, publication, hit.get("chunk_text") or "", source_kind, source=source
            )
            entry["matched_chunks"] += 1
            entry["chunk_scores"].append(adjusted_score)
            if adjusted_score > entry["best_score"]:
                entry["best_score"] = adjusted_score
                entry["best_raw_score"] = float(hit["score"])
                entry["best_chunk_text"] = hit.get("chunk_text") or ""
                entry["best_rank"] = rank
                entry["best_source_kind"] = source_kind
                entry["best_chunk_label"] = getattr(chunk, "page_label", "") if chunk is not None else ""

        results: list[Publication] = []
        metadata_penalty = float(getattr(settings, "SEARCH_METADATA_ONLY_SCORE_FACTOR", 0.88))
        fulltext_bonus = float(getattr(settings, "SEARCH_FULLTEXT_SCORE_BONUS", 0.03))
        for payload in aggregated.values():
            publication = payload["publication"]
            top_scores = sorted(payload["chunk_scores"], reverse=True)[:2]
            aggregate_score = max(top_scores) if top_scores else 0.0
            if len(top_scores) > 1:
                aggregate_score += 0.08 * top_scores[1]
            aggregate_score += 0.02 * math.log1p(max(0, payload["matched_chunks"] - 1))
            keyword_text = ", ".join(keyword.name for keyword in publication.keywords.all())
            aggregate_score += self._lexical_bonus(query, publication.title, payload["best_chunk_text"], keyword_text)
            if payload["best_source_kind"] == "metadata":
                aggregate_score *= metadata_penalty
            else:
                aggregate_score += fulltext_bonus
            publication.search_score = float(aggregate_score)
            publication.retrieval_score = float(payload.get("best_raw_score", aggregate_score))
            publication.search_rank = payload["best_rank"]
            publication.search_source = source
            publication.search_stage = "retrieved"
            publication.best_chunk_text = payload["best_chunk_text"]
            publication.search_excerpt = self._build_excerpt(payload["best_chunk_text"])
            publication.search_match_basis = payload["best_source_kind"]
            publication.search_match_label = payload["best_chunk_label"]
            results.append(publication)

        results.sort(key=lambda item: (item.search_score, -item.search_rank, item.uploaded_at, item.pk), reverse=True)
        return results

    def _vector_limit(self, requested_limit: int, *, hybrid: bool = False) -> int:
        pool_limit = int(getattr(settings, "MILVUS_CHUNK_CANDIDATE_POOL", 60))
        page_size = int(getattr(settings, "SEARCH_PAGE_SIZE", 10))
        if hybrid:
            semantic_head = int(getattr(settings, "HYBRID_SEMANTIC_HEAD_LIMIT", 20))
            target = max(semantic_head * 3, page_size * 4, 40)
        else:
            target = max(page_size * 5, 50)
        if requested_limit:
            target = max(target, min(int(requested_limit), pool_limit))
        return min(pool_limit, target)

    def _clone_publication_for_hybrid(self, source_publication: Publication) -> Publication:
        source_publication.search_excerpt = getattr(source_publication, "search_excerpt", "")
        source_publication.search_match_basis = getattr(source_publication, "search_match_basis", "")
        source_publication.search_match_label = getattr(source_publication, "search_match_label", "")
        source_publication.best_chunk_text = getattr(source_publication, "best_chunk_text", "")
        source_publication.search_rank = getattr(source_publication, "search_rank", 0)
        source_publication.search_stage = getattr(source_publication, "search_stage", "retrieved")
        return source_publication

    def _hybrid_support_bonus(self, query: str, publication: Publication) -> float:
        keyword_text = ", ".join(keyword.name for keyword in publication.keywords.all())
        signals = self._query_signals(
            query,
            publication.title,
            getattr(publication, "best_chunk_text", "") or getattr(publication, "search_excerpt", ""),
            publication.contents or "",
            keyword_text,
        )
        bonus = 0.0
        if signals["exact_phrase"]:
            bonus += float(getattr(settings, "SEARCH_HYBRID_EXACT_PHRASE_BOOST", 0.44))
        elif signals["coverage"] > 0:
            bonus += 0.22 * signals["coverage"]
        elif len(signals["tokens"]) >= 2:
            bonus -= 0.18
        return bonus


class KeywordSearchService(BaseSearchService):
    def search(
        self,
        query: str = "",
        filters: dict[str, Any] | None = None,
        sort_by: str = "relevance",
        *,
        include_fulltext: bool = False,
        relative_floor: float | str | None = None,
    ) -> list[Publication]:
        queryset = self.apply_filters(self.get_base_queryset(include_chunks=include_fulltext), filters)
        publications = list(queryset)
        query = (query or "").strip()

        if query:
            scored_results = []
            for publication in publications:
                keyword_score = self.calculate_keyword_score(publication, query)
                fulltext_score = 0
                best_text = ""
                best_label = ""
                if include_fulltext:
                    fulltext_score, best_text, best_label = self.calculate_fulltext_keyword_support(publication, query)

                total_score = keyword_score + fulltext_score
                if total_score <= 0:
                    continue

                publication.search_score = float(total_score)
                publication.retrieval_score = None
                publication.search_source = "keyword"
                publication.search_stage = "retrieved"
                if fulltext_score > keyword_score and best_text:
                    publication.search_excerpt = self._build_excerpt(best_text)
                    publication.search_match_basis = "fulltext"
                    publication.search_match_label = best_label
                else:
                    publication.search_excerpt = ""
                    publication.search_match_basis = "metadata"
                    publication.search_match_label = "метаданные"
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
            publications = self.filter_publications_by_relative_floor(
                publications,
                self.resolve_relative_floor("keyword", relative_floor),
            )
            if sort_by != "relevance":
                publications = self.sort_publications(publications, sort_by=sort_by)
            return publications

        return self.sort_publications(publications, sort_by=sort_by, default_sort="newest")


class SemanticSearchService(BaseSearchService):
    def __init__(self):
        self.vector_store = VectorStoreService()

    def search(
        self,
        query: str = "",
        filters: dict[str, Any] | None = None,
        limit: int = 200,
        sort_by: str = "relevance",
        *,
        relative_floor: float | str | None = None,
    ) -> list[Publication]:
        queryset = self.apply_filters(self.get_base_queryset(), filters)
        query = (query or "").strip()
        if not query:
            return self.sort_publications(list(queryset), sort_by=sort_by, default_sort="newest")

        chunk_limit = self._vector_limit(limit, hybrid=False)
        dense_hits = self.vector_store.search_dense_chunks(query=query, limit=chunk_limit)
        publications = self._aggregate_chunk_hits(queryset, dense_hits, query=query, source="semantic")
        publications = self._rerank_publications(
            query,
            publications,
            self.vector_store,
            threshold=float(getattr(settings, "SEARCH_SEMANTIC_MIN_SCORE", 0.2)),
            default_source="semantic",
        )
        publications = self.filter_publications_by_relative_floor(
            publications,
            self.resolve_relative_floor("semantic", relative_floor),
        )
        if sort_by != "relevance":
            publications = self.sort_publications(publications, sort_by=sort_by)
        return publications[:limit]


class HybridSearchService(BaseSearchService):
    def __init__(self):
        self.keyword = KeywordSearchService()
        self.vector_store = VectorStoreService()

    def search(
        self,
        query: str = "",
        filters: dict[str, Any] | None = None,
        limit: int = 200,
        sort_by: str = "relevance",
        *,
        relative_floor: float | str | None = None,
    ) -> list[Publication]:
        query = (query or "").strip()
        if not query:
            return self.keyword.search(query="", filters=filters, sort_by=sort_by, relative_floor=relative_floor)

        queryset = self.apply_filters(self.get_base_queryset(), filters)
        chunk_limit = self._vector_limit(limit, hybrid=True)
        hybrid_hits = self.vector_store.search_hybrid_chunks(query=query, limit=chunk_limit)
        semantic_results = self._aggregate_chunk_hits(queryset, hybrid_hits, query=query, source="hybrid-semantic")
        semantic_results = self._rerank_publications(
            query,
            semantic_results,
            self.vector_store,
            threshold=float(getattr(settings, "SEARCH_HYBRID_MIN_SCORE", 0.2)),
            default_source="hybrid-semantic",
        )

        keyword_results = self.keyword.search(
            query=query,
            filters=filters,
            sort_by="relevance",
            include_fulltext=True,
            relative_floor=self.resolve_relative_floor("keyword", relative_floor),
        )
        semantic_head_limit = min(limit, max(1, int(getattr(settings, "HYBRID_SEMANTIC_HEAD_LIMIT", 20))))
        semantic_candidates = semantic_results[: max(semantic_head_limit * 2, 20)]
        keyword_candidates = keyword_results[: max(semantic_head_limit * 2, 20)]

        semantic_max = max((float(getattr(item, "search_score", 0.0) or 0.0) for item in semantic_candidates), default=0.0)
        keyword_max = max((float(getattr(item, "search_score", 0.0) or 0.0) for item in keyword_candidates), default=0.0)
        semantic_weight = float(getattr(settings, "SEARCH_HYBRID_SEMANTIC_BLEND", 0.58))
        keyword_weight = float(getattr(settings, "SEARCH_HYBRID_KEYWORD_BLEND", 0.42))
        semantic_only_penalty = float(getattr(settings, "SEARCH_HYBRID_SEMANTIC_ONLY_FACTOR", 0.58))

        semantic_map = {publication.pk: publication for publication in semantic_candidates}
        keyword_map = {publication.pk: publication for publication in keyword_candidates}
        candidate_ids = list(dict.fromkeys([*semantic_map.keys(), *keyword_map.keys()]))

        fused_results: list[Publication] = []
        for publication_id in candidate_ids:
            semantic_publication = semantic_map.get(publication_id)
            keyword_publication = keyword_map.get(publication_id)
            publication = self._clone_publication_for_hybrid(semantic_publication or keyword_publication)
            if keyword_publication is not None and getattr(keyword_publication, "search_excerpt", "") and not getattr(publication, "search_excerpt", ""):
                publication.search_excerpt = keyword_publication.search_excerpt
                publication.best_chunk_text = getattr(keyword_publication, "search_excerpt", "")
                publication.search_match_basis = getattr(keyword_publication, "search_match_basis", "metadata")
                publication.search_match_label = getattr(keyword_publication, "search_match_label", "")
            semantic_score = float(getattr(semantic_publication, "search_score", 0.0) or 0.0)
            keyword_score = float(getattr(keyword_publication, "search_score", 0.0) or 0.0)
            semantic_norm = (semantic_score / semantic_max) if semantic_max > 0 else 0.0
            keyword_norm = (keyword_score / keyword_max) if keyword_max > 0 else 0.0
            hybrid_bonus = self._hybrid_support_bonus(query, publication)
            fused_score = (semantic_weight * semantic_norm) + (keyword_weight * keyword_norm) + hybrid_bonus

            if semantic_norm > 0 and keyword_norm <= 0:
                fused_score *= semantic_only_penalty

            publication.retrieval_score = float(getattr(semantic_publication, "retrieval_score", semantic_score) or semantic_score or keyword_score)
            publication.search_score = float(fused_score)
            publication.search_stage = "fused"
            if semantic_norm > 0 and keyword_norm > 0:
                publication.search_source = "hybrid-combined"
            elif semantic_norm > 0:
                publication.search_source = "hybrid-semantic"
            else:
                publication.search_source = "hybrid-keyword"
            fused_results.append(publication)

        fused_results = self.filter_publications_by_score(
            sorted(fused_results, key=lambda item: (item.search_score, getattr(item, "retrieval_score", 0.0), item.uploaded_at, item.pk), reverse=True),
            float(getattr(settings, "SEARCH_HYBRID_MIN_SCORE", 0.2)),
        )
        fused_results = self.filter_publications_by_relative_floor(
            fused_results,
            self.resolve_relative_floor("hybrid", relative_floor),
        )
        semantic_head = fused_results[:semantic_head_limit]
        used_ids = {publication.pk for publication in semantic_head}

        filter_tail: list[Publication] = []
        if len(semantic_head) < limit and self.has_active_filters(filters):
            filter_only_results = self.keyword.search(query="", filters=filters, sort_by="newest", relative_floor=0)
            for publication in filter_only_results:
                if publication.pk in used_ids:
                    continue
                publication.search_source = "hybrid-filter"
                publication.search_score = getattr(publication, "search_score", None)
                publication.search_stage = "filtered"
                filter_tail.append(publication)
                used_ids.add(publication.pk)
                if len(semantic_head) + len(filter_tail) >= limit:
                    break

        combined_results = semantic_head + filter_tail
        if sort_by != "relevance":
            combined_results = self.sort_publications(combined_results, sort_by=sort_by)
        return combined_results[:limit]
