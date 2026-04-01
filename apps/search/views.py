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
        return {
            "q": self.request.GET.get("q", ""),
            "mode": self.request.GET.get("mode", "hybrid"),
            "sort": self.request.GET.get("sort", "relevance"),
            "strictness": self.request.GET.get("strictness", ""),
            "publication_type": self.request.GET.get("publication_type", ""),
            "publication_subtype": self.request.GET.get("publication_subtype", ""),
            "language": self.request.GET.get("language", ""),
            "periodicity": self.request.GET.get("periodicity", ""),
            "author": self.request.GET.get("author", ""),
            "keyword": self.request.GET.get("keyword", ""),
            "publisher": self.request.GET.get("publisher", ""),
            "publication_place": self.request.GET.get("publication_place", ""),
            "year_from": self.request.GET.get("year_from", ""),
            "year_to": self.request.GET.get("year_to", ""),
            "include_fulltext_in_keyword": self.request.GET.get("include_fulltext_in_keyword", ""),
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
            "publication_type": cleaned_data.get("publication_type"),
            "publication_subtype": cleaned_data.get("publication_subtype"),
            "language": cleaned_data.get("language"),
            "periodicity": cleaned_data.get("periodicity"),
            "author": cleaned_data.get("author"),
            "keyword": cleaned_data.get("keyword"),
            "publisher": cleaned_data.get("publisher"),
            "publication_place": cleaned_data.get("publication_place"),
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
            "publication_type": getattr(cleaned_data.get("publication_type"), "pk", None),
            "publication_subtype": getattr(cleaned_data.get("publication_subtype"), "pk", None),
            "language": getattr(cleaned_data.get("language"), "pk", None),
            "periodicity": getattr(cleaned_data.get("periodicity"), "pk", None),
            "author": getattr(cleaned_data.get("author"), "pk", None),
            "keyword": getattr(cleaned_data.get("keyword"), "pk", None),
            "publisher": getattr(cleaned_data.get("publisher"), "pk", None),
            "publication_place": getattr(cleaned_data.get("publication_place"), "pk", None),
            "year_from": cleaned_data.get("year_from"),
            "year_to": cleaned_data.get("year_to"),
            "include_fulltext_in_keyword": bool(cleaned_data.get("include_fulltext_in_keyword")),
            "relative_score_floor": cleaned_data.get("strictness") or None,
        }
        return json.dumps({key: value for key, value in payload.items() if value not in (None, "")}, ensure_ascii=False)

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
        return any(cleaned_data.get(key) not in (None, "") for key in meaningful_keys) or self.request.GET.get("mode") not in (
            None,
            "",
            "hybrid",
        )

    def paginate_results(self, results):
        paginator = Paginator(results, settings.SEARCH_PAGE_SIZE)
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

        paginator, page_obj = self.paginate_results(results)
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
