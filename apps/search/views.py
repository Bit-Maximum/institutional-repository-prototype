from django.views.generic import FormView

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
            if mode == "keyword":
                context["results"] = KeywordSearchService().search(query)
            elif mode == "semantic":
                context["results"] = SemanticSearchService().search(query)
            else:
                context["results"] = HybridSearchService().search(query)
        return context
