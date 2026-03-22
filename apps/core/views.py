from django.views.generic import TemplateView

from apps.cms.models import AnnouncementPage
from apps.publications.models import Publication


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_publications"] = Publication.objects.filter(is_public=True).order_by("-created_at")[:5]
        context["latest_announcements"] = AnnouncementPage.objects.live().public().order_by("-first_published_at")[:5]
        return context
