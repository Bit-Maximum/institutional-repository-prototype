from collections import OrderedDict

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Publication
from .widgets import EditorClearableFileInput, EditorClearableImageInput


PUBLISH_REQUIREMENTS = OrderedDict([
    ("title", _("Название")),
    ("source_material", _("Файл или внешняя ссылка")),
    ("publication_year", _("Год издания")),
    ("language", _("Язык")),
    ("publication_subtype", _("Подтип издания")),
    ("authors", _("Авторы")),
    ("contents", _("Аннотация или описание")),
])


class PublicationForm(forms.ModelForm):
    createable_dictionary_fields = {
        "language": True,
        "periodicity": True,
        "authors": True,
        "scientific_supervisors": True,
        "keywords": True,
        "publication_places": True,
        "publishers": True,
        "copyrights": True,
        "bibliographies": True,
        "graphic_editions": True,
    }

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
            "preview_image",
            "file",
            "publication_format_link",
        ]
        labels = {
            "title": _("Название"),
            "subject_code": _("Код тематики"),
            "publication_year": _("Год издания"),
            "language": _("Язык"),
            "publication_subtype": _("Подтип издания"),
            "periodicity": _("Периодичность"),
            "grif_text": _("Гриф"),
            "volume_number": _("Номер тома"),
            "issue_number": _("Номер выпуска"),
            "start_page": _("Начальная страница"),
            "end_page": _("Последняя страница"),
            "contents": _("Аннотация или описание"),
            "grant_text": _("Сведения о гранте"),
            "authors": _("Авторы"),
            "scientific_supervisors": _("Научные руководители"),
            "keywords": _("Ключевые слова"),
            "publication_places": _("Места публикации"),
            "publishers": _("Издатели"),
            "copyrights": _("Копирайты"),
            "bibliographies": _("Библиографические описания"),
            "graphic_editions": _("Графические издания"),
            "preview_image": _("Превью издания"),
            "file": _("Файл издания"),
            "publication_format_link": _("Внешняя ссылка"),
        }
        widgets = {
            "contents": forms.Textarea(attrs={"rows": 5}),
            "grant_text": forms.Textarea(attrs={"rows": 3}),
            "grif_text": forms.Textarea(attrs={"rows": 3}),
            "preview_image": EditorClearableImageInput(),
            "file": EditorClearableFileInput(),
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
            "preview_image": _(
                "Необязательно. Можно загрузить или заменить превью вручную, если вы хотите управлять отображением издания в каталоге и коллекциях."
            ),
            "file": _(
                "Можно загрузить PDF, DOCX или файл любого другого формата. Если извлечь текст не удастся, система продолжит работать по метаданным."
            ),
            "contents": _("Краткое описание или аннотация издания. Может быть предзаполнено автоматически на основе файла."),
            "publication_format_link": _("Внешняя ссылка на издание или альтернативный источник файла, если это необходимо."),
        }

    def __init__(self, *args, workflow_action: str = "save_draft", **kwargs):
        self.workflow_action = workflow_action
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
        self.fields["preview_image"].required = False
        self.fields["file"].required = False

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
            field = self.fields[field_name]
            field.widget.attrs.setdefault("data-enhance-editor-select", "true")
            field.widget.attrs.setdefault("data-placeholder", str(field.label))
            field.widget.attrs.setdefault("data-no-results-label", str(_("Совпадений не найдено")))
            field.widget.attrs.setdefault("data-selected-many-label", str(field.label))
            field.widget.attrs.setdefault("data-show-selection-chips", "false")
            if field_name in {"copyrights", "bibliographies", "graphic_editions"}:
                field.widget.attrs.setdefault("data-summary-mode", "count")
            if self.createable_dictionary_fields.get(field_name):
                field.widget.attrs.setdefault("data-allow-create", "true")
                field.widget.attrs.setdefault("data-create-entity-label", str(field.label).lower())

    def _posted_or_initial_value(self, field_name: str):
        prefixed_name = self.add_prefix(field_name)
        field = self.fields.get(field_name)
        if self.is_bound:
            if getattr(field, "disabled", False):
                return self.initial.get(field_name, self.instance and getattr(self.instance, field_name, None))
            if hasattr(field, "to_python") and getattr(field.widget, "allow_multiple_selected", False):
                return self.data.getlist(prefixed_name)
            if field_name == "file":
                uploaded = self.files.get(prefixed_name)
                if uploaded:
                    return uploaded
                return getattr(self.instance, "file", None)
            return self.data.get(prefixed_name)

        if field_name == "file":
            return getattr(self.instance, "file", None)

        if field_name in {"authors", "scientific_supervisors", "keywords", "publication_places", "publishers", "copyrights", "bibliographies", "graphic_editions"}:
            if self.instance.pk:
                return list(getattr(self.instance, field_name).values_list("pk", flat=True))
            return []

        return self.initial.get(field_name, getattr(self.instance, field_name, None))

    def _has_meaningful_value(self, requirement_key: str) -> bool:
        if requirement_key == "source_material":
            file_value = self._posted_or_initial_value("file")
            link_value = self._posted_or_initial_value("publication_format_link")
            return bool(file_value) or bool(str(link_value or "").strip())

        value = self._posted_or_initial_value(requirement_key)
        if isinstance(value, (list, tuple, set)):
            return bool([item for item in value if str(item).strip()])
        return bool(str(value).strip()) if value is not None else False

    def get_progress_data(self):
        items = []
        filled_count = 0
        for key, label in PUBLISH_REQUIREMENTS.items():
            filled = self._has_meaningful_value(key)
            items.append({
                "key": key,
                "label": label,
                "filled": filled,
            })
            filled_count += int(filled)
        total = len(items)
        percent = int((filled_count / total) * 100) if total else 0
        return {
            "items": items,
            "filled_count": filled_count,
            "total": total,
            "percent": percent,
        }

    def save(self, commit=True):
        publication = super().save(commit=False)
        preview_value = self.cleaned_data.get("preview_image", None)
        if preview_value is False:
            publication.preview_image = None
            publication.preview_kind = ""
            publication.preview_generated_at = None
        elif preview_value is not None and getattr(preview_value, "name", ""):
            publication.preview_kind = "manual_upload"
            publication.preview_generated_at = timezone.now()

        if commit:
            publication.save()
            self.save_m2m()
        return publication

    def clean(self):
        cleaned_data = super().clean()
        if self.workflow_action != "publish":
            return cleaned_data

        missing = [key for key in PUBLISH_REQUIREMENTS if not self._has_meaningful_value(key)]
        if not missing:
            return cleaned_data

        field_required_message = _("Поле необходимо заполнить перед публикацией.")
        for key in missing:
            if key == "source_material":
                self.add_error("file", _("Добавьте файл или внешнюю ссылку перед публикацией."))
                self.add_error("publication_format_link", _("Добавьте файл или внешнюю ссылку перед публикацией."))
            elif key in self.fields:
                self.add_error(key, field_required_message)

        raise forms.ValidationError(
            _("Чтобы опубликовать издание, заполните ключевые поля и проверьте карточку перед выпуском.")
        )
