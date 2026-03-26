from django import forms

from .models import Collection


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Например, Материалы по цифровым библиотекам"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Кратко опишите, для чего создана коллекция и кому она может быть полезна.",
                }
            ),
        }


class CollectionPublicationSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Найти издание для добавления",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Введите название, автора или ключевые слова",
            }
        ),
    )
