"""A synthetic Tokushoho row whose attributes are ALL dedicated columns.

WHY THIS FILE EXISTS, AND WHY THE PREVIOUS VERSION OF IT WAS NOT ENOUGH.
The template's 備考 cell used to fall back to the full included list when a row
had no remarks:

    {% if row.remarks %}…{% elif row.included %}…{% endif %}

A row whose attributes are ALL dedicated (storage / compute credit / overage) has
an EMPTY remarks list BY DESIGN, so that fallback would render those same three
values a SECOND time inside 備考. The catalogue ships no such row today, which is
what made it latent rather than visible.

An earlier version of this test asserted on ``remarks_items`` in isolation and on
the template's SOURCE TEXT. That proved the helper's contract, not the page: it
never rendered anything, so a template that ignored the helper entirely would have
passed. These tests instead RENDER THE REAL TEMPLATE PATH — the actual view, the
actual template — and COUNT OCCURRENCES IN THE RESULTING HTML.

The synthetic row is built from a REAL row and given the REAL rendered column
strings, so it is catalogue-shaped rather than a handful of invented scalars:
passing raw attribute values like ``50`` would not be the shape anything renders.
"""

from __future__ import annotations

import pytest

from apps.infra.public_app.pricing import included_items, published_price_rows

VIEW = "apps.infra.public_app.views.legal.published_price_rows"
TOKUSHOHO_URL = "/tokushoho/"

#: Real rendered column text, taken from the shipped catalogue so the synthetic
#: row carries the same shapes and phrasings a real row does.
_REAL = published_price_rows()[0]
STORAGE = _REAL["storage"]
COMPUTE_CREDIT = _REAL["compute_credit"]
OVERAGE = _REAL["overage"]

#: A GENUINE non-dedicated attribute: it has no column of its own, so it must
#: still reach 備考. Built through the public helper with a real catalogue value.
NON_DEDICATED = included_items({"included_traffic": "normal-use"})[0]


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


def _render(monkeypatch, client, row) -> str:
    """Render the REAL tokushoho view/template with this row as the price list."""
    monkeypatch.setattr(VIEW, lambda: [row])
    response = client.get(TOKUSHOHO_URL)
    assert response.status_code == 200, (
        f"{TOKUSHOHO_URL} returned {response.status_code}"
    )
    return response.content.decode()


@pytest.mark.django_db
def test_a_dedicated_only_row_renders_each_value_exactly_once(monkeypatch, client):
    """The dedicated values appear ONCE — in their own columns, never in 備考.

    If the fallback were restored, each of these would appear TWICE: once in its
    dedicated column and once more inside 備考.
    """
    html = _render(
        monkeypatch,
        client,
        _row(remarks=[], included=[STORAGE, COMPUTE_CREDIT, OVERAGE]),
    )

    for name, value in (
        ("storage", STORAGE),
        ("compute_credit", COMPUTE_CREDIT),
        ("overage", OVERAGE),
    ):
        count = html.count(value)
        assert count == 1, (
            f"{name} renders {count} times, expected exactly 1: a dedicated "
            "attribute is being repeated, which is the 備考 duplication this "
            f"guards against (value: {value!r})"
        )


@pytest.mark.django_db
def test_a_dedicated_only_row_does_not_put_them_in_the_remarks_cell(
    monkeypatch, client
):
    """Stronger than a count: the 備考 CELL itself must not contain them.

    Counts alone would also pass if a value were missing from its column and
    present once in 備考, so the cell is inspected directly.
    """
    html = _render(
        monkeypatch,
        client,
        _row(remarks=[], included=[STORAGE, COMPUTE_CREDIT, OVERAGE]),
    )

    remarks_cell = _remarks_cell(html)
    for name, value in (
        ("storage", STORAGE),
        ("compute_credit", COMPUTE_CREDIT),
        ("overage", OVERAGE),
    ):
        assert value not in remarks_cell, (
            f"{name} appears inside the 備考 cell, so the dedicated column is "
            f"duplicated there (value: {value!r})"
        )


@pytest.mark.django_db
def test_a_genuine_non_dedicated_attribute_is_still_visible(monkeypatch, client):
    """CONTROL the other way: 備考 must still carry what belongs in it.

    Without this, a template that dropped the 備考 content entirely would satisfy
    the two tests above while silently removing information from a legal page.
    """
    html = _render(
        monkeypatch,
        client,
        _row(
            remarks=[NON_DEDICATED],
            included=[STORAGE, COMPUTE_CREDIT, OVERAGE, NON_DEDICATED],
        ),
    )

    assert NON_DEDICATED in html, (
        "a non-dedicated attribute vanished from the page — 備考 content must "
        "survive the removal of the fallback"
    )
    assert NON_DEDICATED in _remarks_cell(html), (
        "the non-dedicated attribute rendered, but not in the 備考 cell where it "
        "belongs"
    )
    # And the dedicated values are still not duplicated by its presence.
    for value in (STORAGE, COMPUTE_CREDIT, OVERAGE):
        assert html.count(value) == 1, (
            f"adding a non-dedicated attribute changed a dedicated column's "
            f"occurrence count for {value!r}"
        )


@pytest.mark.django_db
def test_no_real_row_repeats_a_dedicated_column_in_its_remarks(monkeypatch, client):
    """Control on the REAL catalogue: the property holds for every shipped row."""
    rows = published_price_rows()
    assert rows, "the catalogue produced no price rows"

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

    assert not offenders, (
        f"these rows repeat a dedicated column inside 備考: {offenders} — the "
        "dedicated column and 備考 would show the same figure twice"
    )


def _remarks_cell(html: str) -> str:
    """The contents of the 備考 cell(s) — the last <td> of each price row.

    Located STRUCTURALLY (the last cell of a row) rather than by matching the
    template's source text, so this keeps working when the template's wording or
    markup changes.
    """
    cells = []
    for row_html in html.split("<tr"):
        if "合成プラン" not in row_html:
            continue
        parts = row_html.split("<td")
        if parts:
            cells.append(parts[-1])
    assert cells, "the synthetic row did not render as a table row at all"
    return "\n".join(cells)
