#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特商法 pages: detail-row layout and the JA/EN cross-links.

Operator, 2026-09-14: 「1番右のカラムが小さいのに詳細…中身がいっぱい書いてあった…
レイアウトが無駄が大きくて見にくい」. The price table's rightmost column (備考 /
Notes) was the narrowest and held the longest text. It is no longer a column:
each item is its own <tbody> with a short figures row and a full-width detail
row (one cell spanning every column) that carries 備考.

Both pages also carry a visible link to the other language; the Japanese page
stays the legally authoritative one (「日本語版（正本）」).
"""

import re

import pytest
from django.urls import reverse

PAGES = ["public_app:tokushoho", "public_app:tokushoho_en"]


def _html(client, url_name: str) -> str:
    return client.get(reverse(url_name)).content.decode("utf-8")


def _price_table(html: str) -> str:
    match = re.search(
        r'<table class="tokushoho-price-table[^"]*">.*?</table>', html, re.S
    )
    return match.group() if match else ""


@pytest.mark.django_db
def test_japanese_page_links_to_the_english_version(client):
    # Arrange
    link = re.compile(r'<a href="/tokushoho-en/"[^>]*>English version</a>')
    # Act
    html = _html(client, "public_app:tokushoho")
    # Assert
    assert link.search(html) is not None


@pytest.mark.django_db
def test_english_page_links_to_the_authoritative_japanese_version(client):
    # Arrange
    link = re.compile(r'<a href="/tokushoho/"[^>]*>日本語版（正本）</a>')
    # Act
    html = _html(client, "public_app:tokushoho_en")
    # Assert
    assert link.search(html) is not None


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", PAGES)
def test_notes_are_a_full_width_detail_row_not_a_narrow_column(client, url_name):
    """Six figure columns in the header; every detail cell spans all six."""
    # Arrange
    table = _price_table(_html(client, url_name))
    header = re.search(r"<thead>.*?</thead>", table, re.S)
    # Act
    header_columns = len(re.findall(r"<th\b", header.group())) if header else 0
    detail_spans = set(
        re.findall(r'<td class="tokushoho-detail-cell" colspan="(\d+)"', table)
    )
    # Assert
    assert (header_columns, detail_spans) == (6, {"6"})


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", PAGES)
def test_each_detail_row_sits_under_its_own_item_row(client, url_name):
    """Every item <tbody> opens with its figures row; a detail row never stands alone."""
    # Arrange
    table = _price_table(_html(client, url_name))
    # Act
    bodies = re.findall(
        r'<tbody class="tokushoho-price-item">(.*?)</tbody>', table, re.S
    )
    row_classes = [re.findall(r'<tr class="([^"]+)"', body) for body in bodies]
    # Assert
    assert bool(bodies) and all(
        classes and classes[0] == "tokushoho-item-row" for classes in row_classes
    )
