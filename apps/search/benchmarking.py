from __future__ import annotations

import csv
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.publications.models import (
    Author,
    Keyword,
    PublicationLanguage,
    PublicationPeriodicity,
    PublicationPlace,
    PublicationSubtype,
    PublicationType,
    Publisher,
)
from apps.search.services import HybridSearchService, KeywordSearchService, SemanticSearchService
from apps.vector_store.services import VectorStoreService


FILTER_MODEL_MAP = {
    "publication_type": PublicationType,
    "publication_subtype": PublicationSubtype,
    "language": PublicationLanguage,
    "periodicity": PublicationPeriodicity,
    "author": Author,
    "keyword": Keyword,
    "publisher": Publisher,
    "publication_place": PublicationPlace,
}


SERVICE_MAP = {
    "keyword": KeywordSearchService,
    "semantic": SemanticSearchService,
    "hybrid": HybridSearchService,
}


@dataclass(slots=True)
class BenchmarkCase:
    name: str
    query: str
    modes: list[str]
    filters: dict[str, Any]
    sort_by: str
    include_fulltext_in_keyword: bool
    relative_floor: float | str | None
    limit: int
    expected_publication_ids: list[int]
    expected_title_contains: list[str]
    notes: str


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    values = sorted(float(value) for value in values)
    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    fraction = index - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def load_benchmark_spec(path: str | Path) -> tuple[dict[str, Any], list[BenchmarkCase]]:
    spec_path = Path(path)
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    defaults = payload.get("defaults", {})
    default_modes = defaults.get("modes") or ["keyword", "semantic", "hybrid"]
    default_sort = defaults.get("sort", "relevance")
    default_limit = int(defaults.get("limit") or getattr(settings, "SEARCH_BENCHMARK_LIMIT", 20))
    default_include_fulltext = bool(defaults.get("include_fulltext_in_keyword", False))
    default_relative_floor = defaults.get("relative_floor")

    cases: list[BenchmarkCase] = []
    for index, raw_case in enumerate(payload.get("cases", []), start=1):
        raw_modes = [str(mode).strip().lower() for mode in (raw_case.get("modes") or default_modes)]
        modes = [mode for mode in raw_modes if mode in SERVICE_MAP]
        if not modes:
            raise ValueError(f"Case {index} does not define any supported modes.")
        case = BenchmarkCase(
            name=str(raw_case.get("name") or f"case_{index}"),
            query=str(raw_case.get("query") or "").strip(),
            modes=modes,
            filters=resolve_filter_payload(raw_case.get("filters") or {}),
            sort_by=str(raw_case.get("sort") or default_sort),
            include_fulltext_in_keyword=bool(raw_case.get("include_fulltext_in_keyword", default_include_fulltext)),
            relative_floor=raw_case.get("relative_floor", default_relative_floor),
            limit=int(raw_case.get("limit") or default_limit),
            expected_publication_ids=[int(value) for value in (raw_case.get("expected_publication_ids") or [])],
            expected_title_contains=[str(value).strip().lower() for value in (raw_case.get("expected_title_contains") or []) if str(value).strip()],
            notes=str(raw_case.get("notes") or "").strip(),
        )
        cases.append(case)
    return payload, cases


def resolve_filter_payload(raw_filters: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in raw_filters.items():
        if value in (None, ""):
            continue
        if key in FILTER_MODEL_MAP:
            resolved[key] = FILTER_MODEL_MAP[key].objects.filter(pk=value).first()
        elif key in {"year_from", "year_to"}:
            resolved[key] = int(value)
        else:
            resolved[key] = value
    return resolved




def serialize_filter_payload(filters: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in filters.items():
        if value in (None, ""):
            continue
        if hasattr(value, "pk"):
            serialized[key] = int(value.pk)
        else:
            serialized[key] = value
    return serialized

def is_expected_publication(publication, case: BenchmarkCase) -> bool:
    if publication.pk in case.expected_publication_ids:
        return True
    title = str(getattr(publication, "title", "") or "").strip().lower()
    if not title:
        return False
    return any(fragment in title for fragment in case.expected_title_contains)


def build_top_results(publications: list[Any], top_k: int) -> list[dict[str, Any]]:
    top_results: list[dict[str, Any]] = []
    for publication in publications[:top_k]:
        top_results.append(
            {
                "id": int(publication.pk),
                "title": publication.title,
                "score": float(getattr(publication, "search_score", 0.0) or 0.0),
                "retrieval_score": (
                    None
                    if getattr(publication, "retrieval_score", None) is None
                    else float(getattr(publication, "retrieval_score", 0.0) or 0.0)
                ),
                "source": getattr(publication, "search_source", ""),
                "match_basis": getattr(publication, "search_match_basis", ""),
                "match_label": getattr(publication, "search_match_label", ""),
            }
        )
    return top_results


def evaluate_expected_hits(publications: list[Any], case: BenchmarkCase, top_k: int) -> dict[str, Any]:
    if not case.expected_publication_ids and not case.expected_title_contains:
        return {
            "has_expectations": False,
            "expected_ranks": [],
            "reciprocal_rank": None,
            "hits_at_1": None,
            "hits_at_3": None,
            "hits_at_5": None,
            "precision_at_k": None,
            "recall_at_k": None,
        }

    expected_ranks: list[int] = []
    retrieved_expected = 0
    for rank, publication in enumerate(publications[:top_k], start=1):
        if is_expected_publication(publication, case):
            expected_ranks.append(rank)
            retrieved_expected += 1
    first_rank = expected_ranks[0] if expected_ranks else None
    total_expected = max(1, len(case.expected_publication_ids) + len(case.expected_title_contains))
    return {
        "has_expectations": True,
        "expected_ranks": expected_ranks,
        "reciprocal_rank": (1.0 / first_rank) if first_rank else 0.0,
        "hits_at_1": 1.0 if first_rank == 1 else 0.0,
        "hits_at_3": 1.0 if first_rank and first_rank <= 3 else 0.0,
        "hits_at_5": 1.0 if first_rank and first_rank <= 5 else 0.0,
        "precision_at_k": retrieved_expected / max(1, min(top_k, len(publications))),
        "recall_at_k": min(1.0, retrieved_expected / total_expected),
    }


def summarize_runs(mode: str, case: BenchmarkCase, runs: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(run["elapsed_ms"]) for run in runs]
    result_counts = [int(run["result_count"]) for run in runs]
    top_scores = [float(run.get("top_score") or 0.0) for run in runs]
    summary = {
        "mode": mode,
        "case": case.name,
        "query": case.query,
        "runs": len(runs),
        "mean_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "median_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "min_ms": round(min(latencies), 3) if latencies else 0.0,
        "max_ms": round(max(latencies), 3) if latencies else 0.0,
        "avg_result_count": round(statistics.fmean(result_counts), 3) if result_counts else 0.0,
        "avg_top_score": round(statistics.fmean(top_scores), 4) if top_scores else 0.0,
        "top1_titles": [run.get("top_title") for run in runs if run.get("top_title")],
    }
    if any(run.get("metrics", {}).get("has_expectations") for run in runs):
        rr_values = [float(run["metrics"].get("reciprocal_rank") or 0.0) for run in runs]
        h1 = [float(run["metrics"].get("hits_at_1") or 0.0) for run in runs]
        h3 = [float(run["metrics"].get("hits_at_3") or 0.0) for run in runs]
        h5 = [float(run["metrics"].get("hits_at_5") or 0.0) for run in runs]
        p_at_k = [float(run["metrics"].get("precision_at_k") or 0.0) for run in runs]
        r_at_k = [float(run["metrics"].get("recall_at_k") or 0.0) for run in runs]
        summary.update(
            {
                "mrr": round(statistics.fmean(rr_values), 4) if rr_values else 0.0,
                "hits_at_1": round(statistics.fmean(h1), 4) if h1 else 0.0,
                "hits_at_3": round(statistics.fmean(h3), 4) if h3 else 0.0,
                "hits_at_5": round(statistics.fmean(h5), 4) if h5 else 0.0,
                "precision_at_k": round(statistics.fmean(p_at_k), 4) if p_at_k else 0.0,
                "recall_at_k": round(statistics.fmean(r_at_k), 4) if r_at_k else 0.0,
            }
        )
    return summary


def aggregate_mode_summaries(mode_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in mode_rows:
        grouped.setdefault(row["mode"], []).append(row)

    aggregates: list[dict[str, Any]] = []
    for mode, rows in grouped.items():
        metrics = {
            "mode": mode,
            "cases": len(rows),
            "mean_ms": round(statistics.fmean(row["mean_ms"] for row in rows), 3),
            "median_ms": round(statistics.fmean(row["median_ms"] for row in rows), 3),
            "p95_ms": round(statistics.fmean(row["p95_ms"] for row in rows), 3),
            "avg_result_count": round(statistics.fmean(row["avg_result_count"] for row in rows), 3),
            "avg_top_score": round(statistics.fmean(row["avg_top_score"] for row in rows), 4),
        }
        if all("mrr" in row for row in rows):
            metrics.update(
                {
                    "mrr": round(statistics.fmean(row["mrr"] for row in rows), 4),
                    "hits_at_1": round(statistics.fmean(row["hits_at_1"] for row in rows), 4),
                    "hits_at_3": round(statistics.fmean(row["hits_at_3"] for row in rows), 4),
                    "hits_at_5": round(statistics.fmean(row["hits_at_5"] for row in rows), 4),
                    "precision_at_k": round(statistics.fmean(row["precision_at_k"] for row in rows), 4),
                    "recall_at_k": round(statistics.fmean(row["recall_at_k"] for row in rows), 4),
                }
            )
        aggregates.append(metrics)
    return sorted(aggregates, key=lambda item: item["mode"])


def run_benchmark(
    *,
    cases: list[BenchmarkCase],
    runs_per_case: int,
    top_k_eval: int,
    warmup: bool = True,
    include_reranker_in_warmup: bool = False,
) -> dict[str, Any]:
    if warmup:
        vector_store = VectorStoreService()
        vector_store.ensure_collection()
        vector_store.warmup(include_reranker=include_reranker_in_warmup)

    timestamp = timezone.now().isoformat()
    case_results: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for case in cases:
        for mode in case.modes:
            service_cls = SERVICE_MAP[mode]
            runs: list[dict[str, Any]] = []
            for run_index in range(1, runs_per_case + 1):
                service = service_cls()
                started = perf_counter()
                if mode == "keyword":
                    results = service.search(
                        query=case.query,
                        filters=case.filters,
                        sort_by=case.sort_by,
                        include_fulltext=case.include_fulltext_in_keyword,
                        relative_floor=case.relative_floor,
                    )
                else:
                    results = service.search(
                        query=case.query,
                        filters=case.filters,
                        limit=case.limit,
                        sort_by=case.sort_by,
                        relative_floor=case.relative_floor,
                    )
                elapsed_ms = (perf_counter() - started) * 1000.0
                metrics = evaluate_expected_hits(results, case, top_k_eval)
                top_results = build_top_results(results, top_k_eval)
                run_payload = {
                    "run": run_index,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "result_count": len(results),
                    "top_title": top_results[0]["title"] if top_results else None,
                    "top_score": top_results[0]["score"] if top_results else None,
                    "top_results": top_results,
                    "metrics": metrics,
                }
                runs.append(run_payload)

            summary = summarize_runs(mode, case, runs)
            case_results.append(
                {
                    "case": case.name,
                    "query": case.query,
                    "mode": mode,
                    "filters": serialize_filter_payload(case.filters),
                    "sort_by": case.sort_by,
                    "include_fulltext_in_keyword": case.include_fulltext_in_keyword,
                    "relative_floor": case.relative_floor,
                    "notes": case.notes,
                    "runs": runs,
                    "summary": summary,
                }
            )
            summary_rows.append(summary)

    return {
        "generated_at": timestamp,
        "runs_per_case": runs_per_case,
        "top_k_eval": top_k_eval,
        "summary": aggregate_mode_summaries(summary_rows),
        "cases": case_results,
    }


def write_reports(report: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    json_path = target_dir / f"search_benchmark_{timestamp}.json"
    csv_path = target_dir / f"search_benchmark_{timestamp}.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "case",
                "mode",
                "query",
                "mean_ms",
                "median_ms",
                "p95_ms",
                "avg_result_count",
                "avg_top_score",
                "mrr",
                "hits_at_1",
                "hits_at_3",
                "hits_at_5",
                "precision_at_k",
                "recall_at_k",
            ]
        )
        for case_item in report["cases"]:
            summary = case_item["summary"]
            writer.writerow(
                [
                    case_item["case"],
                    case_item["mode"],
                    case_item["query"],
                    summary.get("mean_ms"),
                    summary.get("median_ms"),
                    summary.get("p95_ms"),
                    summary.get("avg_result_count"),
                    summary.get("avg_top_score"),
                    summary.get("mrr"),
                    summary.get("hits_at_1"),
                    summary.get("hits_at_3"),
                    summary.get("hits_at_5"),
                    summary.get("precision_at_k"),
                    summary.get("recall_at_k"),
                ]
            )

    return {"json": str(json_path), "csv": str(csv_path)}
