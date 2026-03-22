from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView

from .forms import CollectionForm
from .models import Collection


class CollectionListView(ListView):
    model = Collection
    template_name = "collections/list.html"
    context_object_name = "collections"

    def get_queryset(self):
        return Collection.objects.filter(is_public=True).select_related("owner")


class CollectionDetailView(DetailView):
    model = Collection
    template_name = "collections/detail.html"
    context_object_name = "collection"
    slug_field = "slug"
    slug_url_kwarg = "slug"


class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "collections/create.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
