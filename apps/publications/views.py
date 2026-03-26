from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.ingestion.services import generate_metadata_prefill_from_upload, ingest_publication

from .forms import PublicationForm
from .models import Publication


class PublicationEditorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and (getattr(user, "is_staff", False) or getattr(user, "is_admin", False) or getattr(user, "is_superuser", False)))

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise Http404
        return super().handle_no_permission()


class PublicationVisibilityMixin:
    def get_publication_queryset(self):
        queryset = (
            Publication.objects.select_related(
                "publication_subtype",
                "publication_subtype__publication_type",
                "language",
                "periodicity",
                "uploaded_by",
                "last_saved_by",
                "published_by",
            )
            .prefetch_related(
                "authors",
                "keywords",
                "publishers",
                "publication_places",
                "scientific_supervisors",
                "chunks",
            )
        )
        user = self.request.user
        if user.is_authenticated and (getattr(user, "is_staff", False) or getattr(user, "is_admin", False) or getattr(user, "is_superuser", False)):
            return queryset
        return queryset.filter(is_draft=False)


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


class DraftPublicationListView(PublicationEditorRequiredMixin, ListView):
    model = Publication
    template_name = "publications/drafts.html"
    context_object_name = "drafts"
    paginate_by = settings.SEARCH_PAGE_SIZE

    def get_queryset(self):
        queryset = (
            Publication.objects.filter(is_draft=True)
            .select_related(
                "publication_subtype",
                "publication_subtype__publication_type",
                "language",
                "uploaded_by",
                "last_saved_by",
            )
            .prefetch_related("authors")
            .order_by("-updated_at", "-uploaded_at")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(contents__icontains=q) | Q(authors__full_name__icontains=q)).distinct()
        return queryset


class PublicationDetailView(PublicationVisibilityMixin, DetailView):
    model = Publication
    template_name = "publications/detail.html"
    context_object_name = "publication"

    def get_queryset(self):
        return self.get_publication_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_manage_publication"] = bool(
            user.is_authenticated and (getattr(user, "is_staff", False) or getattr(user, "is_admin", False) or getattr(user, "is_superuser", False))
        )
        return context


class PublicationWorkflowMixin(PublicationEditorRequiredMixin):
    model = Publication
    form_class = PublicationForm
    template_name = "publications/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["prefill_endpoint"] = reverse_lazy("publications:upload-prefill")
        context["workflow_mode"] = getattr(self, "workflow_mode", "create")
        context["publication"] = getattr(self, "object", None)
        return context

    def _workflow_action(self) -> str:
        action = (self.request.POST.get("workflow_action") or "save_draft").strip()
        if action not in {"save_draft", "publish"}:
            return "save_draft"
        return action

    def _apply_workflow_state(self, publication: Publication, *, action: str) -> None:
        if action == "publish":
            publication.mark_as_published(actor=self.request.user)
        else:
            publication.mark_as_draft(actor=self.request.user)

    def _success_response(self, publication: Publication, *, action: str):
        if publication.is_draft:
            if action == "publish":
                messages.success(self.request, "Издание опубликовано и теперь доступно в основной коллекции.")
            else:
                messages.success(
                    self.request,
                    f"Черновик сохранён. Редакция №{publication.draft_revision or 1} доступна всем администраторам для дальнейшего заполнения.",
                )
            return HttpResponseRedirect(reverse("publications:edit", kwargs={"pk": publication.pk}))

        messages.success(self.request, "Издание опубликовано и проиндексировано для поиска.")
        return HttpResponseRedirect(publication.get_absolute_url())

    def form_valid(self, form):
        action = self._workflow_action()
        self.object = form.save(commit=False)
        if not self.object.pk and not self.object.uploaded_by_id:
            self.object.uploaded_by = self.request.user
        self._apply_workflow_state(self.object, action=action)
        self.object.save()
        form.save_m2m()
        ingest_publication(self.object, index_in_vector_store=not self.object.is_draft)
        if self.object.is_draft and self.object.has_extracted_text:
            messages.info(self.request, "Черновик обновлён. Текст извлечён и будет готов к публикации после подтверждения.")
        elif self.object.is_draft:
            messages.warning(self.request, "Черновик сохранён в режиме metadata-only. После публикации он будет доступен через поиск по метаданным.")
        elif self.object.has_extracted_text:
            messages.info(self.request, "Основной текст успешно извлечён и включён в индекс поиска.")
        else:
            messages.warning(self.request, "Издание опубликовано в режиме metadata-only. Поиск будет опираться на введённые метаданные.")
        return self._success_response(self.object, action=action)


class PublicationCreateView(PublicationWorkflowMixin, CreateView):
    success_url = reverse_lazy("publications:list")
    workflow_mode = "create"


class PublicationUpdateView(PublicationWorkflowMixin, UpdateView):
    workflow_mode = "edit"

    def get_queryset(self):
        return Publication.objects.all().select_related(
            "publication_subtype",
            "publication_subtype__publication_type",
            "language",
            "uploaded_by",
            "last_saved_by",
            "published_by",
        ).prefetch_related(
            "authors",
            "keywords",
            "publishers",
            "publication_places",
            "scientific_supervisors",
            "copyrights",
            "bibliographies",
            "graphic_editions",
        )


class PublicationMetadataPrefillView(PublicationEditorRequiredMixin, View):
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
