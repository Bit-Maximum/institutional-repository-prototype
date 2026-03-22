from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DetailView, ListView

from apps.ingestion.services import ingest_publication

from .forms import PublicationForm
from .models import Publication


class PublicationListView(ListView):
    model = Publication
    template_name = "publications/list.html"
    context_object_name = "publications"
    paginate_by = 20

    def get_queryset(self):
        queryset = Publication.objects.filter(is_public=True).select_related("publication_type").prefetch_related("authors")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(abstract__icontains=q))
        return queryset


class PublicationDetailView(DetailView):
    model = Publication
    template_name = "publications/detail.html"
    context_object_name = "publication"
    slug_field = "slug"
    slug_url_kwarg = "slug"


class PublicationCreateView(LoginRequiredMixin, CreateView):
    model = Publication
    form_class = PublicationForm
    template_name = "publications/upload.html"
    success_url = reverse_lazy("publications:list")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.uploaded_by = self.request.user
        self.object.save()
        form.save_m2m()
        ingest_publication(self.object, index_in_vector_store=True)
        return HttpResponseRedirect(self.get_success_url())
