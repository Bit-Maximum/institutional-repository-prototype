from __future__ import annotations

from typing import Any


class FieldLabelMixin:
    field_labels: dict[str, str] = {}
    field_help_texts: dict[str, str] = {}

    def _apply_form_customizations(self, form_class: type) -> type:
        for field_name, label in getattr(self, "field_labels", {}).items():
            field = form_class.base_fields.get(field_name)
            if field is not None:
                field.label = label

        for field_name, help_text in getattr(self, "field_help_texts", {}).items():
            field = form_class.base_fields.get(field_name)
            if field is not None:
                field.help_text = help_text

        return form_class


class LocalizedModelAdminMixin(FieldLabelMixin):
    def get_form(self, request, obj: Any | None = None, change: bool = False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        return self._apply_form_customizations(form)


class LocalizedInlineMixin(FieldLabelMixin):
    def get_formset(self, request, obj: Any | None = None, **kwargs):
        formset = super().get_formset(request, obj=obj, **kwargs)
        self._apply_form_customizations(formset.form)
        return formset
