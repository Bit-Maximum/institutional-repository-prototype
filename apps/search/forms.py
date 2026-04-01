from django import forms
from django.utils.translation import gettext_lazy as _

from apps.publications.models import (
    Author,
    Keyword,
    PublicationLanguage,
    PublicationPeriodicity,
    PublicationPlace,
    PublicationSubtype,
    PublicationType,
    Publisher,
)


FILTER_PAGE_SIZE_CHOICES = [
    ("10", _("10 на страницу")),
    ("20", _("20 на страницу")),
    ("50", _("50 на страницу")),
]


class BaseSearchableSelectMixin:
    def _init_search_attrs(self, placeholder: str = "", enable_search: bool = True):
        attrs = self.attrs
        attrs.setdefault("data-enhance-search-select", "true")
        attrs.setdefault("data-placeholder", placeholder)
        attrs.setdefault("data-no-results-label", _("Ничего не найдено"))
        attrs.setdefault("data-selected-many-label", _("Выбрано значений"))
        attrs.setdefault("data-enable-search", "true" if enable_search else "false")

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if hasattr(label, "publication_type_id"):
            option["attrs"]["data-publication-type"] = str(label.publication_type_id)
            option["label"] = str(label)
        return option


class SearchableSelectMultiple(BaseSearchableSelectMixin, forms.SelectMultiple):
    def __init__(self, *args, placeholder: str = "", enable_search: bool = True, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        super().__init__(*args, **kwargs)
        self._init_search_attrs(placeholder=placeholder, enable_search=enable_search)


class SearchableSelect(BaseSearchableSelectMixin, forms.Select):
    def __init__(self, *args, placeholder: str = "", enable_search: bool = False, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        super().__init__(*args, **kwargs)
        self._init_search_attrs(placeholder=placeholder, enable_search=enable_search)


class SearchForm(forms.Form):
    q = forms.CharField(
        label=_("Запрос"),
        max_length=500,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Название, автор, ключевое слово, издатель…"),
            }
        ),
    )
    mode = forms.ChoiceField(
        choices=[
            ("hybrid", _("Гибридный")),
            ("semantic", _("Семантический")),
            ("keyword", _("Традиционный")),
        ],
        initial="hybrid",
        label=_("Режим поиска"),
        widget=SearchableSelect(placeholder=_("Режим поиска"), enable_search=False),
    )
    sort = forms.ChoiceField(
        choices=[
            ("relevance", _("По релевантности")),
            ("newest", _("Сначала новые")),
            ("oldest", _("Сначала старые")),
            ("year_desc", _("По году: новые")),
            ("year_asc", _("По году: старые")),
            ("title_asc", _("По названию: А–Я")),
            ("title_desc", _("По названию: Я–А")),
        ],
        initial="relevance",
        label=_("Сортировка"),
        required=False,
        widget=SearchableSelect(placeholder=_("Сортировка"), enable_search=False),
    )
    strictness = forms.ChoiceField(
        choices=[
            ("", _("По умолчанию из конфига")),
            ("0", _("Не отсекать слабые результаты")),
            ("0.35", _("Мягкий отсев")),
            ("0.5", _("Сбалансированный отсев")),
            ("0.65", _("Строгий отсев")),
            ("0.8", _("Очень строгий отсев")),
        ],
        initial="",
        label=_("Строгость отсечения по score"),
        required=False,
        widget=SearchableSelect(placeholder=_("Строгость отсечения по score"), enable_search=False),
    )
    results_per_page = forms.ChoiceField(
        choices=FILTER_PAGE_SIZE_CHOICES,
        initial="10",
        required=False,
        widget=forms.HiddenInput(),
    )
    publication_type = forms.ModelMultipleChoiceField(
        queryset=PublicationType.objects.all(),
        required=False,
        label=_("Тип издания"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите типы изданий")),
    )
    publication_subtype = forms.ModelMultipleChoiceField(
        queryset=PublicationSubtype.objects.select_related("publication_type").all(),
        required=False,
        label=_("Подтип издания"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите подтипы изданий")),
    )
    language = forms.ModelMultipleChoiceField(
        queryset=PublicationLanguage.objects.all(),
        required=False,
        label=_("Язык"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите языки")),
    )
    periodicity = forms.ModelMultipleChoiceField(
        queryset=PublicationPeriodicity.objects.all(),
        required=False,
        label=_("Периодичность"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите периодичность")),
    )
    author = forms.ModelMultipleChoiceField(
        queryset=Author.objects.select_related("academic_degree").all(),
        required=False,
        label=_("Автор"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите авторов")),
    )
    keyword = forms.ModelMultipleChoiceField(
        queryset=Keyword.objects.all(),
        required=False,
        label=_("Ключевое слово"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите ключевые слова")),
    )
    publisher = forms.ModelMultipleChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        label=_("Издатель"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите издателей")),
    )
    publication_place = forms.ModelMultipleChoiceField(
        queryset=PublicationPlace.objects.all(),
        required=False,
        label=_("Место публикации"),
        widget=SearchableSelectMultiple(placeholder=_("Выберите места публикации")),
    )
    year_from = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=9999,
        label=_("Год издания от"),
    )
    year_to = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=9999,
        label=_("Год издания до"),
    )
    include_fulltext_in_keyword = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Для традиционного поиска учитывать совпадения в основном тексте"),
    )

    multiselect_field_names = (
        "publication_type",
        "publication_subtype",
        "language",
        "periodicity",
        "author",
        "keyword",
        "publisher",
        "publication_place",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        publication_types = cleaned_data.get("publication_type")
        publication_subtypes = cleaned_data.get("publication_subtype")
        year_from = cleaned_data.get("year_from")
        year_to = cleaned_data.get("year_to")

        if publication_types and publication_subtypes:
            valid_type_ids = {item.pk for item in publication_types}
            invalid_subtypes = [item for item in publication_subtypes if item.publication_type_id not in valid_type_ids]
            if invalid_subtypes:
                self.add_error(
                    "publication_subtype",
                    _("Среди выбранных подтипов есть значения, не относящиеся к указанным типам изданий."),
                )

        if year_from is not None and year_to is not None and year_from > year_to:
            self.add_error("year_to", _("Верхняя граница диапазона не может быть меньше нижней."))

        results_per_page = cleaned_data.get("results_per_page") or "10"
        if results_per_page not in {"10", "20", "50"}:
            cleaned_data["results_per_page"] = "10"

        return cleaned_data
