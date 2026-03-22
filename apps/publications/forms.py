from django import forms

from .models import Publication


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = [
            "title",
            "slug",
            "abstract",
            "publication_year",
            "language",
            "isbn_or_identifier",
            "publication_type",
            "authors",
            "file",
            "cover",
            "copyright_note",
            "keywords",
            "metadata",
            "status",
            "is_public",
        ]
