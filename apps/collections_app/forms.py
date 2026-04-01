from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Collection


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "description"]
        labels = {
            "name": _("Название"),
            "description": _("Описание"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Например, Материалы по цифровым библиотекам")}),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": _(
                        "Кратко опишите, для чего создана коллекция и кому она может быть полезна."
                    ),
                }
            ),
        }


class CollectionPublicationSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label=_("Найти издание для добавления"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Введите название, автора или ключевые слова"),
            }
        ),
    )
