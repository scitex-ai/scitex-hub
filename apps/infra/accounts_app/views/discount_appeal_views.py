"""Academic discount appeal: the form + review-queue entry point.

Operator CCT4558. A signed-in account whose address the automatic checker
missed states its case here; a reviewer decides in Django admin (or the
``approve_appeals`` action). One open appeal per account — the view refuses
a second while the first awaits review, and the partial unique constraint
(``unique_open_discount_appeal_per_user``) holds the line against a
double-click race the check-then-insert cannot see.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.infra.public_app.models import DiscountAppeal

from ..forms_discount_appeal import DiscountAppealForm

logger = logging.getLogger(__name__)

__all__ = ["discount_appeal"]


@login_required
def discount_appeal(request):
    """File (or check on) this account's academic discount appeal."""
    open_appeal = (
        DiscountAppeal.objects.filter(
            user=request.user, status=DiscountAppeal.Status.OPEN
        ).first()
    )
    if request.method == "POST" and open_appeal is None:
        form = DiscountAppealForm(request.POST)
        if form.is_valid():
            # One-open-per-account, checked here for the message and held by
            # the partial unique constraint for the race.
            if DiscountAppeal.objects.filter(
                user=request.user, status=DiscountAppeal.Status.OPEN
            ).exists():
                open_appeal = DiscountAppeal.objects.filter(
                    user=request.user, status=DiscountAppeal.Status.OPEN
                ).first()
                form = DiscountAppealForm(
                    initial={"claimed_email": request.user.email}
                )
            else:
                try:
                    open_appeal = DiscountAppeal.objects.create(
                        user=request.user,
                        claimed_email=form.cleaned_data["claimed_email"],
                        institution=form.cleaned_data["institution"],
                        evidence=form.cleaned_data["evidence"],
                    )
                except IntegrityError:
                    # Lost the double-click race against the partial unique
                    # constraint: the other insert IS the open appeal.
                    logger.info(
                        "Duplicate appeal insert collapsed for %s",
                        request.user.pk,
                    )
                    open_appeal = DiscountAppeal.objects.filter(
                        user=request.user,
                        status=DiscountAppeal.Status.OPEN,
                    ).first()
                    form = DiscountAppealForm(
                        initial={"claimed_email": request.user.email}
                    )
                else:
                    messages.success(
                        request,
                        _(
                            "Appeal received — a reviewer will check your "
                            "affiliation and decide. The academic price applies "
                            "from approval; nothing is charged differently "
                            "while you wait."
                        ),
                    )
                    form = DiscountAppealForm(
                        initial={"claimed_email": request.user.email}
                    )
    else:
        form = DiscountAppealForm(
            initial={"claimed_email": request.user.email}
        )
    history = (
        DiscountAppeal.objects.filter(user=request.user)
        .exclude(status=DiscountAppeal.Status.OPEN)
        .order_by("-created_at")[:5]
    )
    return render(
        request,
        "accounts_app/discount_appeal.html",
        {
            "form": form,
            "open_appeal": open_appeal,
            "history": history,
        },
    )
