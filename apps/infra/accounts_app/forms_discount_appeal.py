"""Academic discount appeal form: what the requester must state.

Kept as a plain ``forms.Form`` (not a ModelForm) on purpose: field shape is
validatable with Django forms alone, no apps registry, so the validation
tests run in containers without postgres. The view maps cleaned data onto
``DiscountAppeal``; the one-open-per-account rule lives there (it needs the
database) plus the partial unique constraint (it needs nothing).
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

__all__ = ["DiscountAppealForm"]


class DiscountAppealForm(forms.Form):
    """What the requester must state for a review to be possible."""

    claimed_email = forms.EmailField(
        label=_("Institutional email"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@your-institution.ac.jp",
            }
        ),
        help_text=_(
            "The address that proves the affiliation — often, but not "
            "necessarily, your account address."
        ),
    )
    institution = forms.CharField(
        label=_("Institution"),
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Tohoku University"}),
    )
    evidence = forms.CharField(
        label=_("Affiliation evidence"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Staff page URL or affiliation note a reviewer can check",
            }
        ),
        help_text=_(
            "A public staff page or personnel listing is ideal; "
            "never upload documents here."
        ),
    )
