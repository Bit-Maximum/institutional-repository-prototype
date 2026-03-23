from django import forms

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
            "is_draft",
        ]
        widgets = {
            "authors": forms.SelectMultiple(attrs={"size": 10}),
            "scientific_supervisors": forms.SelectMultiple(attrs={"size": 8}),
            "keywords": forms.SelectMultiple(attrs={"size": 8}),
            "publication_places": forms.SelectMultiple(attrs={"size": 6}),
            "publishers": forms.SelectMultiple(attrs={"size": 6}),
            "copyrights": forms.SelectMultiple(attrs={"size": 6}),
            "bibliographies": forms.SelectMultiple(attrs={"size": 6}),
            "graphic_editions": forms.SelectMultiple(attrs={"size": 6}),
        }
