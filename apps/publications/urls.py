from django.urls import path

from .views import PublicationCreateView, PublicationDetailView, PublicationListView

app_name = "publications"

urlpatterns = [
    path("", PublicationListView.as_view(), name="list"),
    path("upload/", PublicationCreateView.as_view(), name="upload"),
    path("<int:pk>/", PublicationDetailView.as_view(), name="detail"),
]
