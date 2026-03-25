from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.ingestion.services import generate_metadata_prefill_from_upload, ingest_publication

from .forms import PublicationForm
from .models import Publication


class PublicationListView(ListView):
    model = Publication
    template_name = "publications/list.html"
    context_object_name = "publications"
    paginate_by = settings.SEARCH_PAGE_SIZE

    def get_queryset(self):
        queryset = (
            Publication.objects.filter(is_draft=False)
            .select_related("publication_subtype", "publication_subtype__publication_type", "language")
            .prefetch_related("authors")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(contents__icontains=q) | Q(grif_text__icontains=q))
        return queryset


class PublicationDetailView(DetailView):
    model = Publication
    template_name = "publications/detail.html"
    context_object_name = "publication"

    def get_queryset(self):
        return (
            Publication.objects.select_related("publication_subtype", "publication_subtype__publication_type", "language")
            .prefetch_related("authors", "keywords", "chunks")
        )


class PublicationCreateView(LoginRequiredMixin, CreateView):
    model = Publication
    form_class = PublicationForm
    template_name = "publications/upload.html"
    success_url = reverse_lazy("publications:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["prefill_endpoint"] = reverse_lazy("publications:upload-prefill")
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.uploaded_by = self.request.user
        self.object.save()
        form.save_m2m()
        ingest_publication(self.object, index_in_vector_store=not self.object.is_draft)
        if self.object.has_extracted_text:
            messages.success(self.request, "Издание сохранено. Основной текст успешно извлечён и подготовлен к поиску.")
        else:
            messages.warning(
                self.request,
                "Издание сохранено в режиме metadata-only. Поиск будет работать по введённым метаданным.",
            )
        return HttpResponseRedirect(self.get_success_url())


class PublicationMetadataPrefillView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "Сначала выберите файл для анализа."}, status=400)

        try:
            payload = generate_metadata_prefill_from_upload(uploaded_file)
        except Exception as exc:  # pragma: no cover - defensive fallback for malformed uploads
            return JsonResponse(
                {"error": f"Не удалось проанализировать файл ({exc.__class__.__name__})."},
                status=400,
            )
        return JsonResponse(payload)
