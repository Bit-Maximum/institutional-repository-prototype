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
    )
    publication_type = forms.ModelChoiceField(
        queryset=PublicationType.objects.all(),
        required=False,
        empty_label=_("Любой тип издания"),
        label=_("Тип издания"),
    )
    publication_subtype = forms.ModelChoiceField(
        queryset=PublicationSubtype.objects.select_related("publication_type").all(),
        required=False,
        empty_label=_("Любой подтип издания"),
        label=_("Подтип издания"),
    )
    language = forms.ModelChoiceField(
        queryset=PublicationLanguage.objects.all(),
        required=False,
        empty_label=_("Любой язык"),
        label=_("Язык"),
    )
    periodicity = forms.ModelChoiceField(
        queryset=PublicationPeriodicity.objects.all(),
        required=False,
        empty_label=_("Любая периодичность"),
        label=_("Периодичность"),
    )
    author = forms.ModelChoiceField(
        queryset=Author.objects.select_related("academic_degree").all(),
        required=False,
        empty_label=_("Любой автор"),
        label=_("Автор"),
    )
    keyword = forms.ModelChoiceField(
        queryset=Keyword.objects.all(),
        required=False,
        empty_label=_("Любое ключевое слово"),
        label=_("Ключевое слово"),
    )
    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        empty_label=_("Любой издатель"),
        label=_("Издатель"),
    )
    publication_place = forms.ModelChoiceField(
        queryset=PublicationPlace.objects.all(),
        required=False,
        empty_label=_("Любое место публикации"),
        label=_("Место публикации"),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        publication_type = None
        raw_publication_type = self.data.get("publication_type") or self.initial.get("publication_type")
        if raw_publication_type:
            try:
                publication_type = PublicationType.objects.filter(pk=raw_publication_type).first()
            except (TypeError, ValueError):
                publication_type = None

        subtype_queryset = PublicationSubtype.objects.select_related("publication_type")
        if publication_type is not None:
            subtype_queryset = subtype_queryset.filter(publication_type=publication_type)
        self.fields["publication_subtype"].queryset = subtype_queryset

    def clean(self):
        cleaned_data = super().clean()
        publication_type = cleaned_data.get("publication_type")
        publication_subtype = cleaned_data.get("publication_subtype")
        year_from = cleaned_data.get("year_from")
        year_to = cleaned_data.get("year_to")

        if publication_type and publication_subtype and publication_subtype.publication_type_id != publication_type.pk:
            self.add_error(
                "publication_subtype",
                _("Выбранный подтип не относится к указанному типу издания."),
            )

        if year_from is not None and year_to is not None and year_from > year_to:
            self.add_error("year_to", _("Верхняя граница диапазона не может быть меньше нижней."))

        return cleaned_data
