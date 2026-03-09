from django import forms
from ...models import Manuscript


class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
