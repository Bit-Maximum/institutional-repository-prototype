from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.generic import FormView

from apps.search.models import SearchQuery
from apps.vector_store.exceptions import VectorStoreDependencyError

from .forms import SearchForm
from .services import HybridSearchService, KeywordSearchService, SemanticSearchService


class SearchView(FormView):
    template_name = "search/results.html"
    form_class = SearchForm

    def get_initial(self):
        return {
            "q": self.request.GET.get("q", ""),
            "mode": self.request.GET.get("mode", "hybrid"),
            "sort": self.request.GET.get("sort", "relevance"),
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
        }

    def get_serialized_filters(self, cleaned_data, mode: str):
        payload = {
            "mode": mode,
            "sort": cleaned_data.get("sort") or "relevance",
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
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["querystring"] = query_params.urlencode()

        if not form.is_valid():
            return context

        query = (form.cleaned_data.get("q") or "").strip()
        mode = form.cleaned_data["mode"]
        sort_by = form.cleaned_data.get("sort") or "relevance"
        filters = self.get_filter_payload(form.cleaned_data)

        if self.request.user.is_authenticated and self.has_active_criteria(form.cleaned_data):
            SearchQuery.objects.create(
                query_text=query,
                filters=self.get_serialized_filters(form.cleaned_data, mode),
                user=self.request.user,
            )

        try:
            if mode == "keyword":
                results = KeywordSearchService().search(
                    query=query,
                    filters=filters,
                    sort_by=sort_by,
                    include_fulltext=bool(form.cleaned_data.get("include_fulltext_in_keyword")),
                )
            elif mode == "semantic":
                results = SemanticSearchService().search(
                    query=query,
                    filters=filters,
                    limit=settings.SEARCH_CANDIDATE_POOL_SIZE,
                    sort_by=sort_by,
                )
            else:
                results = HybridSearchService().search(
                    query=query,
                    filters=filters,
                    limit=settings.SEARCH_CANDIDATE_POOL_SIZE,
                    sort_by=sort_by,
                )
        except VectorStoreDependencyError as exc:
            messages.error(self.request, str(exc))
            results = KeywordSearchService().search(query=query, filters=filters, sort_by=sort_by) if mode == "hybrid" else []

        paginator, page_obj = self.paginate_results(results)
        context["results"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["is_paginated"] = page_obj.has_other_pages()
        context["total_results"] = paginator.count
        context["active_mode"] = mode
        context["active_sort"] = sort_by
        context["has_active_filters"] = self.has_active_criteria(form.cleaned_data)
        return context
