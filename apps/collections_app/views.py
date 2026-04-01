from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.utils.translation import gettext as _

from apps.publications.models import Publication
from apps.publications.previews import ensure_publication_previews

from .forms import CollectionForm, CollectionPublicationSearchForm
from .models import Collection, CollectionPublication, CollectionReaction


class CollectionOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        collection = self.get_collection_object()
        user = self.request.user
        return bool(
            user.is_authenticated
            and (
                collection.author_user_id == user.id
                or getattr(user, "is_staff", False)
                or getattr(user, "is_admin", False)
                or getattr(user, "is_superuser", False)
            )
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise Http404
        return super().handle_no_permission()

    def get_collection_object(self) -> Collection:
        if not hasattr(self, "_collection_object"):
            self._collection_object = get_object_or_404(Collection, pk=self.kwargs["pk"])
        return self._collection_object


class CollectionListView(ListView):
    model = Collection
    template_name = "collections/list.html"
    context_object_name = "collections"
    paginate_by = 12

    def get_queryset(self):
        queryset = Collection.objects.with_stats().select_related("author_user")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(author_user__full_name__icontains=q) | Q(author_user__email__icontains=q)).distinct()
        sort = (self.request.GET.get("sort") or "popular").strip()
        if sort == "newest":
            queryset = queryset.order_by("-created_at", "name")
        elif sort == "updated":
            queryset = queryset.order_by("-updated_at", "name")
        else:
            queryset = queryset.order_by("-like_count", "dislike_count", "-updated_at", "name")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["sort_value"] = (self.request.GET.get("sort") or "popular").strip()
        if self.request.user.is_authenticated:
            context["my_collections"] = Collection.objects.with_stats().filter(author_user=self.request.user).select_related("author_user")[:5]
        else:
            context["my_collections"] = []
        return context


class MyCollectionListView(LoginRequiredMixin, ListView):
    model = Collection
    template_name = "collections/my_list.html"
    context_object_name = "collections"
    paginate_by = 12

    def get_queryset(self):
        return Collection.objects.with_stats().filter(author_user=self.request.user).select_related("author_user").order_by("-updated_at", "name")


class CollectionDetailView(DetailView):
    model = Collection
    template_name = "collections/detail.html"
    context_object_name = "collection"

    def get_queryset(self):
        return Collection.objects.with_stats().select_related("author_user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection: Collection = self.object
        user = self.request.user
        can_manage = bool(
            user.is_authenticated
            and (
                collection.author_user_id == user.id
                or getattr(user, "is_staff", False)
                or getattr(user, "is_admin", False)
                or getattr(user, "is_superuser", False)
            )
        )
        visible_publications = collection.publications.select_related(
            "publication_subtype",
            "publication_subtype__publication_type",
            "language",
        ).prefetch_related("authors")
        hidden_count = 0
        if not can_manage:
            hidden_count = visible_publications.filter(is_draft=True).count()
            visible_publications = visible_publications.filter(is_draft=False)
        visible_publications = visible_publications.order_by("-collectionpublication__added_at", "title")

        reaction = None
        if user.is_authenticated:
            reaction = CollectionReaction.objects.filter(collection=collection, user=user).values_list("value", flat=True).first()

        search_form = CollectionPublicationSearchForm(self.request.GET or None)
        search_query = ""
        candidate_publications = Publication.objects.none()
        if can_manage and search_form.is_valid():
            search_query = search_form.cleaned_data.get("q", "").strip()
            if search_query:
                existing_ids = collection.publications.values_list("pk", flat=True)
                candidate_publications = (
                    Publication.objects.filter(is_draft=False)
                    .filter(
                        Q(title__icontains=search_query)
                        | Q(contents__icontains=search_query)
                        | Q(authors__full_name__icontains=search_query)
                        | Q(keywords__name__icontains=search_query)
                        | Q(publishers__name__icontains=search_query)
                    )
                    .exclude(pk__in=existing_ids)
                    .select_related("publication_subtype", "publication_subtype__publication_type", "language")
                    .prefetch_related("authors")
                    .distinct()[:20]
                )

        visible_publications_list = list(visible_publications)
        candidate_publications_list = list(candidate_publications)
        ensure_publication_previews(visible_publications_list)
        ensure_publication_previews(candidate_publications_list)
        context.update(
            {
                "publications": visible_publications_list,
                "hidden_count": hidden_count,
                "can_manage_collection": can_manage,
                "user_reaction": reaction,
                "search_form": search_form,
                "search_query": search_query,
                "candidate_publications": candidate_publications_list,
            }
        )
        return context


class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "collections/create.html"

    def form_valid(self, form):
        form.instance.author_user = self.request.user
        messages.success(self.request, _("Коллекция создана. Теперь можно добавить в неё издания из репозитория."))
        return super().form_valid(form)


class CollectionUpdateView(CollectionOwnerRequiredMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = "collections/edit.html"

    def get_queryset(self):
        return Collection.objects.with_stats().select_related("author_user")

    def form_valid(self, form):
        messages.success(self.request, _("Коллекция обновлена."))
        return super().form_valid(form)


class CollectionAddPublicationView(CollectionOwnerRequiredMixin, UpdateView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        collection = self.get_collection_object()
        publication_id = request.POST.get("publication_id")
        publication = get_object_or_404(Publication, pk=publication_id, is_draft=False)
        _, created = CollectionPublication.objects.get_or_create(collection=collection, publication=publication)
        if created:
            messages.success(request, _("Издание «%(title)s» добавлено в коллекцию.") % {"title": publication.title})
        else:
            messages.info(request, _("Это издание уже есть в коллекции."))
        return redirect(reverse("collections:detail", kwargs={"pk": collection.pk}) + (f"?q={request.POST.get('q','').strip()}" if request.POST.get('q') else ""))


class CollectionRemovePublicationView(CollectionOwnerRequiredMixin, UpdateView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        collection = self.get_collection_object()
        publication_id = request.POST.get("publication_id")
        deleted, _ = CollectionPublication.objects.filter(collection=collection, publication_id=publication_id).delete()
        if deleted:
            messages.success(request, _("Издание удалено из коллекции."))
        else:
            messages.info(request, _("Издание уже отсутствует в коллекции."))
        return redirect("collections:detail", pk=collection.pk)


class CollectionReactView(LoginRequiredMixin, DetailView):
    http_method_names = ["post"]
    model = Collection

    def post(self, request, *args, **kwargs):
        collection = get_object_or_404(Collection, pk=kwargs["pk"])
        action = (request.POST.get("reaction") or "").strip()
        if action == "like":
            value = 1
        elif action == "dislike":
            value = -1
        elif action == "clear":
            CollectionReaction.objects.filter(collection=collection, user=request.user).delete()
            messages.success(request, _("Оценка коллекции удалена."))
            return redirect("collections:detail", pk=collection.pk)
        else:
            messages.error(request, _("Не удалось обработать оценку коллекции."))
            return redirect("collections:detail", pk=collection.pk)

        reaction, created = CollectionReaction.objects.update_or_create(
            collection=collection,
            user=request.user,
            defaults={"value": value},
        )
        if created:
            messages.success(request, _("Оценка коллекции сохранена."))
        else:
            messages.success(request, _("Оценка коллекции обновлена."))
        return redirect("collections:detail", pk=collection.pk)
