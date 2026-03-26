from django.urls import path

from .views import (
    CollectionAddPublicationView,
    CollectionCreateView,
    CollectionDetailView,
    CollectionListView,
    CollectionReactView,
    CollectionRemovePublicationView,
    CollectionUpdateView,
    MyCollectionListView,
)

app_name = "collections"

urlpatterns = [
    path("", CollectionListView.as_view(), name="list"),
    path("my/", MyCollectionListView.as_view(), name="my-list"),
    path("create/", CollectionCreateView.as_view(), name="create"),
    path("<int:pk>/", CollectionDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", CollectionUpdateView.as_view(), name="edit"),
    path("<int:pk>/add-publication/", CollectionAddPublicationView.as_view(), name="add-publication"),
    path("<int:pk>/remove-publication/", CollectionRemovePublicationView.as_view(), name="remove-publication"),
    path("<int:pk>/react/", CollectionReactView.as_view(), name="react"),
]
