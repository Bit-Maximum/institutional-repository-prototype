from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView
from django.utils.translation import gettext as _

from apps.search.models import SearchQuery
from apps.vector_store.exceptions import VectorStoreDependencyError
from apps.publications.previews import ensure_publication_previews

from .forms import SearchForm
from .recommendations import RecommendationService
from .services import HybridSearchService, KeywordSearchService, SemanticSearchService


class SearchView(FormView):
    template_name = "search/results.html"
    form_class = SearchForm

    def get_initial(self):
        querydict = self.request.GET
        return {
            "q": querydict.get("q", ""),
            "mode": querydict.get("mode", "hybrid"),
            "sort": querydict.get("sort", "relevance"),
            "strictness": querydict.get("strictness", ""),
            "results_per_page": querydict.get("results_per_page", "10"),
            "publication_type": querydict.getlist("publication_type"),
            "publication_subtype": querydict.getlist("publication_subtype"),
            "language": querydict.getlist("language"),
            "periodicity": querydict.getlist("periodicity"),
            "author": querydict.getlist("author"),
            "keyword": querydict.getlist("keyword"),
            "publisher": querydict.getlist("publisher"),
            "publication_place": querydict.getlist("publication_place"),
            "year_from": querydict.get("year_from", ""),
            "year_to": querydict.get("year_to", ""),
            "include_fulltext_in_keyword": querydict.get("include_fulltext_in_keyword", ""),
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = self.request.GET.copy()
        data.setdefault("mode", "hybrid")
        data.setdefault("sort", "relevance")
        kwargs["data"] = data
        return kwargs

    def get_filter_payload(self, cleaned_data):
        return {
            "publication_type": list(cleaned_data.get("publication_type") or []),
            "publication_subtype": list(cleaned_data.get("publication_subtype") or []),
            "language": list(cleaned_data.get("language") or []),
            "periodicity": list(cleaned_data.get("periodicity") or []),
            "author": list(cleaned_data.get("author") or []),
            "keyword": list(cleaned_data.get("keyword") or []),
            "publisher": list(cleaned_data.get("publisher") or []),
            "publication_place": list(cleaned_data.get("publication_place") or []),
            "year_from": cleaned_data.get("year_from"),
            "year_to": cleaned_data.get("year_to"),
            "include_fulltext_in_keyword": bool(cleaned_data.get("include_fulltext_in_keyword")),
            "relative_score_floor": cleaned_data.get("strictness") or None,
        }

    def get_serialized_filters(self, cleaned_data, mode: str):
        payload = {
            "mode": mode,
            "sort": cleaned_data.get("sort") or "relevance",
            "strictness": cleaned_data.get("strictness") or None,
            "results_per_page": cleaned_data.get("results_per_page") or "10",
            "publication_type": [item.pk for item in cleaned_data.get("publication_type") or []],
            "publication_subtype": [item.pk for item in cleaned_data.get("publication_subtype") or []],
            "language": [item.pk for item in cleaned_data.get("language") or []],
            "periodicity": [item.pk for item in cleaned_data.get("periodicity") or []],
            "author": [item.pk for item in cleaned_data.get("author") or []],
            "keyword": [item.pk for item in cleaned_data.get("keyword") or []],
            "publisher": [item.pk for item in cleaned_data.get("publisher") or []],
            "publication_place": [item.pk for item in cleaned_data.get("publication_place") or []],
            "year_from": cleaned_data.get("year_from"),
            "year_to": cleaned_data.get("year_to"),
            "include_fulltext_in_keyword": bool(cleaned_data.get("include_fulltext_in_keyword")),
            "relative_score_floor": cleaned_data.get("strictness") or None,
        }
        compact_payload = {}
        for key, value in payload.items():
            if value in (None, "", []):
                continue
            compact_payload[key] = value
        return json.dumps(compact_payload, ensure_ascii=False)

    def has_active_criteria(self, cleaned_data) -> bool:
        meaningful_keys = {
            "q",
            "publication_type",
            "publication_subtype",
            "language",
            "periodicity",
            "author",
            "keyword",
            "publisher",
            "publication_place",
            "year_from",
            "year_to",
            "include_fulltext_in_keyword",
            "strictness",
        }
        for key in meaningful_keys:
            value = cleaned_data.get(key)
            if value in (None, ""):
                continue
            if hasattr(value, "exists"):
                if value.exists():
                    return True
                continue
            if isinstance(value, (list, tuple, set)):
                if value:
                    return True
                continue
            if value:
                return True
        return self.request.GET.get("mode") not in (None, "", "hybrid")

    def paginate_results(self, results, per_page: int):
        paginator = Paginator(results, per_page)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        return paginator, page_obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["results"] = []
        context["page_obj"] = None
        context["paginator"] = None
        context["is_paginated"] = False
        context["total_results"] = 0
        context["primary_results"] = []
        context["additional_results"] = []
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["querystring"] = query_params.urlencode()
        page_size_params = self.request.GET.copy()
        page_size_params.pop("page", None)
        page_size_params.pop("results_per_page", None)
        context["page_size_querystring"] = page_size_params.urlencode()
        context["page_size_choices"] = [10, 20, 50]

        if not form.is_valid():
            return context

        query = (form.cleaned_data.get("q") or "").strip()
        mode = form.cleaned_data["mode"]
        sort_by = form.cleaned_data.get("sort") or "relevance"
        filters = self.get_filter_payload(form.cleaned_data)

        created_history_entry = None
        serialized_filters = self.get_serialized_filters(form.cleaned_data, mode)

        try:
            if mode == "keyword":
                results = KeywordSearchService().search(
                    query=query,
                    filters=filters,
                    sort_by=sort_by,
                    include_fulltext=bool(form.cleaned_data.get("include_fulltext_in_keyword")),
                    relative_floor=form.cleaned_data.get("strictness") or None,
                )
            elif mode == "semantic":
                results = SemanticSearchService().search(
                    query=query,
                    filters=filters,
                    limit=settings.SEARCH_CANDIDATE_POOL_SIZE,
                    sort_by=sort_by,
                    relative_floor=form.cleaned_data.get("strictness") or None,
                )
            else:
                results = HybridSearchService().search(
                    query=query,
                    filters=filters,
                    limit=settings.SEARCH_CANDIDATE_POOL_SIZE,
                    sort_by=sort_by,
                    relative_floor=form.cleaned_data.get("strictness") or None,
                )
        except VectorStoreDependencyError as exc:
            messages.error(self.request, str(exc))
            results = KeywordSearchService().search(
                query=query,
                filters=filters,
                sort_by=sort_by,
                relative_floor=form.cleaned_data.get("strictness") or None,
            ) if mode == "hybrid" else []

        if self.request.user.is_authenticated and self.has_active_criteria(form.cleaned_data):
            created_history_entry = SearchQuery.objects.create(
                query_text=query,
                filters=serialized_filters,
                user=self.request.user,
            )
            RecommendationService().prime_from_search_entry(created_history_entry, results)

        current_page_size = int(form.cleaned_data.get("results_per_page") or settings.SEARCH_PAGE_SIZE)
        paginator, page_obj = self.paginate_results(results, per_page=current_page_size)
        page_results = list(page_obj.object_list)
        context["primary_results"] = [item for item in page_results if getattr(item, "search_source", "") != "hybrid-filter"]
        context["additional_results"] = [item for item in page_results if getattr(item, "search_source", "") == "hybrid-filter"]
        ensure_publication_previews(context["primary_results"])
        ensure_publication_previews(context["additional_results"])
        context["results"] = page_results
        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["is_paginated"] = page_obj.has_other_pages()
        context["total_results"] = paginator.count
        context["active_mode"] = mode
        context["active_sort"] = sort_by
        context["has_active_filters"] = self.has_active_criteria(form.cleaned_data)
        context["current_page_size"] = current_page_size
        return context


class SearchHistoryView(LoginRequiredMixin, TemplateView):
    template_name = "search/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = SearchQuery.objects.filter(user=self.request.user).order_by("-created_at", "-id")
        paginator = Paginator(queryset, settings.SEARCH_PAGE_SIZE)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["history_entries"] = page_obj.object_list
        context["history_count"] = paginator.count
        return context


class SearchHistoryDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk: int, *args, **kwargs):
        entry = get_object_or_404(SearchQuery, pk=pk, user=request.user)
        entry.delete()
        messages.success(request, _("Запись из истории поиска удалена."))
        return redirect("search:history")


class SearchHistoryClearView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        deleted_count, _ = SearchQuery.objects.filter(user=request.user).delete()
        if deleted_count:
            messages.success(request, _("История поиска очищена."))
        else:
            messages.info(request, _("История поиска уже была пустой."))
        return redirect("search:history")


class RecommendationListView(TemplateView):
    template_name = "search/recommendations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not user.is_authenticated:
            context.update({
                "requires_authentication": True,
                "recommendations": [],
                "source_queries": [],
                "has_history": False,
            })
            return context

        requested_page = self.request.GET.get("page") or 1
        try:
            requested_page_int = max(1, int(requested_page))
        except (TypeError, ValueError):
            requested_page_int = 1
        recommendation_context = RecommendationService().build_for_user(
            user,
            page=requested_page_int,
            page_size=settings.SEARCH_PAGE_SIZE,
        )
        paginator = Paginator(recommendation_context.results, settings.SEARCH_PAGE_SIZE)
        page_obj = paginator.get_page(requested_page_int)
        recommendations = list(page_obj.object_list)
        ensure_publication_previews(recommendations)
        context.update(
            {
                "requires_authentication": False,
                "recommendations": recommendations,
                "source_queries": recommendation_context.source_queries,
                "has_history": recommendation_context.has_history,
                "page_obj": page_obj,
                "paginator": paginator,
                "total_results": paginator.count,
            }
        )
        return context
