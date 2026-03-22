from django import forms

from .models import Collection


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "slug", "description", "is_public"]
