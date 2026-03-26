from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail import urls as wagtail_urls

from apps.core.views import HealthLiveView, HealthReadyView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("health/", HealthReadyView.as_view(), name="health-ready"),
    path("health/live/", HealthLiveView.as_view(), name="health-live"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready-detail"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.users.urls")),
    path("accounts/", include("allauth.urls")),
    path("publications/", include("apps.publications.urls")),
    path("collections/", include("apps.collections_app.urls")),
    path("search/", include("apps.search.urls")),
    path("cms-admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("pages/", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
