from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Publication


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = [
            "title",
            "subject_code",
            "publication_year",
            "language",
            "publication_subtype",
            "periodicity",
            "grif_text",
            "volume_number",
            "issue_number",
            "start_page",
            "end_page",
            "contents",
            "grant_text",
            "authors",
            "scientific_supervisors",
            "keywords",
            "publication_places",
            "publishers",
            "copyrights",
            "bibliographies",
            "graphic_editions",
            "file",
            "publication_format_link",
        ]
        widgets = {
            "contents": forms.Textarea(attrs={"rows": 5}),
            "grant_text": forms.Textarea(attrs={"rows": 3}),
            "grif_text": forms.Textarea(attrs={"rows": 3}),
            "authors": forms.SelectMultiple(attrs={"size": 8}),
            "scientific_supervisors": forms.SelectMultiple(attrs={"size": 6}),
            "keywords": forms.SelectMultiple(attrs={"size": 8}),
            "publication_places": forms.SelectMultiple(attrs={"size": 6}),
            "publishers": forms.SelectMultiple(attrs={"size": 6}),
            "copyrights": forms.SelectMultiple(attrs={"size": 6}),
            "bibliographies": forms.SelectMultiple(attrs={"size": 6}),
            "graphic_editions": forms.SelectMultiple(attrs={"size": 6}),
        }
        help_texts = {
            "file": _(
                "Можно загрузить PDF, DOCX или файл любого другого формата. Если извлечь текст не удастся, система продолжит работать по метаданным."
            ),
            "contents": _("Краткое описание или аннотация издания. Может быть предзаполнено автоматически на основе файла."),
            "publication_format_link": _("Внешняя ссылка на издание или альтернативный источник файла, если это необходимо."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "language",
            "publication_subtype",
            "periodicity",
            "authors",
            "scientific_supervisors",
            "keywords",
            "publication_places",
            "publishers",
            "copyrights",
            "bibliographies",
            "graphic_editions",
        ):
            self.fields[field_name].required = False

        self.fields["title"].help_text = _(
            "Поле обязательно. Его можно заполнить вручную или получить предварительную подсказку из загруженного файла."
        )
        self.fields["publication_year"].required = False

        self.fields["file"].required = False
