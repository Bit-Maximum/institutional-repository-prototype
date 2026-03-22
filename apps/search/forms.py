from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(label="Запрос", max_length=500)
    mode = forms.ChoiceField(
        choices=[
            ("hybrid", "Гибридный"),
            ("semantic", "Семантический"),
            ("keyword", "Традиционный"),
        ],
        initial="hybrid",
    )
