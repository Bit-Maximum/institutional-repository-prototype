from django.urls import path

from .views import CollectionCreateView, CollectionDetailView, CollectionListView

app_name = "collections"

urlpatterns = [
    path("", CollectionListView.as_view(), name="list"),
    path("create/", CollectionCreateView.as_view(), name="create"),
    path("<slug:slug>/", CollectionDetailView.as_view(), name="detail"),
]
