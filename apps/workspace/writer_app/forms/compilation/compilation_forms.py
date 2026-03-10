from django import forms
from ...models import CompilationJob


class CompilationForm(forms.Form):
    compilation_type = forms.ChoiceField(
        choices=CompilationJob.COMPILATION_TYPES,
        initial="full",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
