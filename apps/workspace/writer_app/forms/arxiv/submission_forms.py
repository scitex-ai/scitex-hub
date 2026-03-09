from django import forms
from ...models import ArxivSubmission, ArxivCategory


class ArxivSubmissionForm(forms.ModelForm):
    primary_category = forms.ModelChoiceField(
        queryset=ArxivCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = ArxivSubmission
        fields = ["title", "abstract", "authors", "primary_category", "submission_type"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "abstract": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "authors": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "submission_type": forms.Select(attrs={"class": "form-control"}),
        }
