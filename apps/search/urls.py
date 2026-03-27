from django.urls import path

from .views import (
    RecommendationListView,
    SearchHistoryClearView,
    SearchHistoryDeleteView,
    SearchHistoryView,
    SearchView,
)

app_name = "search"

urlpatterns = [
    path("", SearchView.as_view(), name="results"),
    path("history/", SearchHistoryView.as_view(), name="history"),
    path("history/clear/", SearchHistoryClearView.as_view(), name="history-clear"),
    path("history/<int:pk>/delete/", SearchHistoryDeleteView.as_view(), name="history-delete"),
    path("recommendations/", RecommendationListView.as_view(), name="recommendations"),
]
