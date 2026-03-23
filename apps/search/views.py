from django.contrib import messages
from django.views.generic import FormView

from apps.search.models import SearchQuery
from apps.vector_store.exceptions import VectorStoreDependencyError

from .forms import SearchForm
from .services import HybridSearchService, KeywordSearchService, SemanticSearchService


class SearchView(FormView):
    template_name = "search/results.html"
    form_class = SearchForm

    def get_initial(self):
        return {"q": self.request.GET.get("q", ""), "mode": self.request.GET.get("mode", "hybrid")}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.GET:
            kwargs["data"] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["results"] = []
        if form.is_valid():
            query = form.cleaned_data["q"]
            mode = form.cleaned_data["mode"]
            if self.request.user.is_authenticated:
                SearchQuery.objects.create(
                    query_text=query,
                    filters=f"mode={mode}",
                    user=self.request.user,
                )
            try:
                if mode == "keyword":
                    context["results"] = KeywordSearchService().search(query)
                elif mode == "semantic":
                    context["results"] = SemanticSearchService().search(query)
                else:
                    context["results"] = HybridSearchService().search(query)
            except VectorStoreDependencyError as exc:
                messages.error(self.request, str(exc))
        return context
