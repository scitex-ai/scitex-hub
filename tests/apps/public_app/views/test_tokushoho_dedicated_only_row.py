"""A synthetic Tokushoho row whose attributes are ALL dedicated columns.

WHY THIS FILE EXISTS.
The template's 備考 cell used to fall back to the full included list when a row
had no remarks:

    {% if row.remarks %}…{% elif row.included %}…{% endif %}

A row whose attributes are ALL dedicated (storage / compute credit / overage) has
an EMPTY remarks list BY DESIGN, so that fallback would render those same three
values a SECOND time inside 備考. The catalogue ships no such row today, which is
what made it latent rather than visible.

These tests RENDER THE REAL TEMPLATE with the REAL view context
(``_tokushoho_context``, under ``translation.override("ja")`` exactly as the view
does) and swap in only the price list, then COUNT OCCURRENCES IN THE HTML. (An
earlier version patched the view's module attribute with ``monkeypatch``; the
context builder is called directly instead, so nothing in production is
rewritten.)

LAYOUT (2026-09-14): 備考 is no longer the last column of the figures row. Each
item is its own ``<tbody>`` holding the figures ``<tr>`` and then a full-width
detail ``<tr>`` whose single cell is 備考 — see ``_remarks_cell``.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import translation

from apps.infra.public_app.pricing import included_items, published_price_rows
from apps.infra.public_app.views.legal import _tokushoho_context

TEMPLATE = "public_app/legal/tokushoho.html"

#: Real rendered column text, taken from the shipped catalogue so the synthetic
#: row carries the same shapes and phrasings a real row does.
_REAL = published_price_rows()[0]
STORAGE = _REAL["storage"]
COMPUTE_CREDIT = _REAL["compute_credit"]
OVERAGE = _REAL["overage"]
DEDICATED = (STORAGE, COMPUTE_CREDIT, OVERAGE)

#: A GENUINE non-dedicated attribute: it has no column of its own, so it must
#: still reach 備考. Built through the public helper with a real catalogue value.
NON_DEDICATED = included_items({"included_egress": {"amount": 100}})[0]


def _row(*, remarks, included):
    """A catalogue-shaped row: every key a real row has, with these values."""
    row = dict(_REAL)
    row.update(
        {
            "id": "synthetic-dedicated-only",
            "label": "合成プラン",
            "storage": STORAGE,
            "compute_credit": COMPUTE_CREDIT,
            "overage": OVERAGE,
            "remarks": remarks,
            "included": included,
        }
    )
    return row


def _render(row) -> str:
    """Render the REAL tokushoho template + view context with this price list."""
    request = RequestFactory().get("/tokushoho/")
    request.user = AnonymousUser()
    request.session = {}
    with translation.override("ja"):
        context = _tokushoho_context(as_of_format="%Y年%m月%d日")
        context["published_price_rows"] = [row]
        return render_to_string(TEMPLATE, context, request=request)


def _remarks_cell(html: str) -> str:
    """The contents of the 備考 cell(s) for the synthetic item.

    Located STRUCTURALLY: the ``<td>`` of the item's LAST row inside its own
    ``<tbody>`` — and "" when the item has no detail row at all.
    """
    cells = []
    for item_html in html.split("<tbody")[1:]:
        item_html = item_html.split("</tbody>")[0]
        if "合成プラン" not in item_html:
            continue
        rows = item_html.split("<tr")
        last_row = rows[-1] if len(rows) > 2 else ""
        cells.append(last_row.split("<td")[-1] if "<td" in last_row else "")
    return "\n".join(cells)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value", DEDICATED, ids=["storage", "compute_credit", "overage"]
)
def test_a_dedicated_only_row_renders_each_value_exactly_once(value):
    """If the fallback were restored, each value would appear TWICE."""
    # Arrange
    row = _row(remarks=[], included=list(DEDICATED))
    # Act
    html = _render(row)
    # Assert
    assert html.count(value) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value", DEDICATED, ids=["storage", "compute_credit", "overage"]
)
def test_a_dedicated_only_row_does_not_put_them_in_the_remarks_cell(value):
    """Stronger than a count: the 備考 CELL itself must not contain them."""
    # Arrange
    row = _row(remarks=[], included=list(DEDICATED))
    # Act
    remarks_cell = _remarks_cell(_render(row))
    # Assert
    assert value not in remarks_cell


@pytest.mark.django_db
def test_a_genuine_non_dedicated_attribute_is_still_in_the_remarks_cell():
    """CONTROL the other way: 備考 must still carry what belongs in it."""
    # Arrange
    row = _row(remarks=[NON_DEDICATED], included=[*DEDICATED, NON_DEDICATED])
    # Act
    remarks_cell = _remarks_cell(_render(row))
    # Assert
    assert NON_DEDICATED in remarks_cell


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value", DEDICATED, ids=["storage", "compute_credit", "overage"]
)
def test_a_non_dedicated_remark_does_not_duplicate_a_dedicated_column(value):
    # Arrange
    row = _row(remarks=[NON_DEDICATED], included=[*DEDICATED, NON_DEDICATED])
    # Act
    html = _render(row)
    # Assert
    assert html.count(value) == 1


def test_no_real_row_repeats_a_dedicated_column_in_its_remarks():
    """Control on the REAL catalogue: the property holds for every shipped row."""
    # Arrange
    rows = published_price_rows()
    # Act
    offenders = [
        (row["id"], column)
        for row in rows
        for column in (
            row.get("storage"),
            row.get("compute_credit"),
            row.get("overage"),
        )
        if column and column != "—" and row.get("remarks") and column in row["remarks"]
    ]
    # Assert
    assert (bool(rows), offenders) == (True, [])
