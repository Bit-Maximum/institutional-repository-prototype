from django.urls import path

from .views import SetLanguageView, SetThemeModeView

app_name = "ui"

urlpatterns = [
    path("preferences/theme/", SetThemeModeView.as_view(), name="set-theme"),
    path("preferences/language/", SetLanguageView.as_view(), name="set-language"),
]
