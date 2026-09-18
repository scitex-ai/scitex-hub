#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``{% chat_error_card %}`` — resolve a provider-failure category to a card.

Kept as a tag so the copy table lives in Python (translatable, testable) while
the markup stays dumb: the template renders `card` and never sees the provider's
own message, which :func:`chat_error_cards.error_card` discards.
"""

from __future__ import annotations

from django import template

from apps.infra.llm_app.chat_error_cards import error_card

register = template.Library()


@register.simple_tag
def chat_error_card(
    category=None,
    provider_message: str = "",
    retry_after: str = "",
    support_id: str = "",
):
    return error_card(
        category,
        provider_message=provider_message,
        retry_after=retry_after,
        support_id=support_id,
    )
