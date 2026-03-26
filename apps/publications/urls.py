from django.urls import path

from .views import (
    DraftPublicationListView,
    PublicationCreateView,
    PublicationDetailView,
    PublicationListView,
    PublicationMetadataPrefillView,
    PublicationUpdateView,
)

app_name = "publications"

urlpatterns = [
    path("", PublicationListView.as_view(), name="list"),
    path("drafts/", DraftPublicationListView.as_view(), name="drafts"),
    path("upload/", PublicationCreateView.as_view(), name="upload"),
    path("upload/prefill/", PublicationMetadataPrefillView.as_view(), name="upload-prefill"),
    path("<int:pk>/edit/", PublicationUpdateView.as_view(), name="edit"),
    path("<int:pk>/", PublicationDetailView.as_view(), name="detail"),
]
