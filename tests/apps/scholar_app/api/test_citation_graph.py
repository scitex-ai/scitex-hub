#!/usr/bin/env python3
"""Citation graph API returns a drawable network (nodes + citation edges)."""

from rest_framework.test import APIRequestFactory

from apps.workspace.scholar_app.api.citation_graph import (
    build_network_multi,
    build_network_query,
)
from apps.workspace.scholar_app.services.citation_graph.online import (
    OnlineCrossrefGraphSource,
    extract_doi,
)
from apps.workspace.scholar_app.services.citation_graph.service import (
    CitationGraphService,
)

SEED = "10.1000/seed"


def _work(doi, title, cited_by, refs, year=2020):
    return {
        "DOI": doi,
        "title": [title],
        "author": [{"family": "Doe", "given": "Jane"}],
        "issued": {"date-parts": [[year]]},
        "container-title": ["Journal of Fixtures"],
        "is-referenced-by-count": cited_by,
        "reference": [{"key": r, "DOI": r} for r in refs] + [{"key": "no-doi"}],
    }


WORKS = {
    SEED: _work(SEED, "Seed paper", 500, ["10.1000/a", "10.1000/b", "10.1000/c"]),
    "10.1000/a": _work("10.1000/a", "Paper A", 900, ["10.1000/b"], 2015),
    "10.1000/b": _work("10.1000/b", "Paper B", 300, [], 2010),
    "10.1000/c": _work("10.1000/c", "Paper C", 10, ["10.1000/a"], 2018),
}


def fixture_fetch(url, params):
    if "query.bibliographic" in params:
        return {"message": {"items": [{"DOI": SEED}]}}
    dois = [f.split(":", 1)[1] for f in params["filter"].split(",")]
    return {"message": {"items": [WORKS[d] for d in dois if d in WORKS]}}


class _LocalServerDown:
    """What crossref-local's builder hands back when its server is unreachable."""

    class _Graph:
        def __init__(self, dois):
            self.dois = dois

        def to_dict(self):
            return {
                "seed": self.dois[0],
                "seed_dois": self.dois,
                "nodes": [{"id": d, "title": "", "is_seed": True} for d in self.dois],
                "edges": [],
                "metadata": {},
            }

    def build_from_dois(self, dois, num_related_per_doi):
        return self._Graph(dois)

    def build_from_query(self, query, num_related_per_doi, search_limit):
        raise ConnectionError("crossref-local refused")


def _service():
    return CitationGraphService(
        builder=_LocalServerDown(),
        online_source=OnlineCrossrefGraphSource(fetch_json=fixture_fetch),
    )


def _multi_request():
    return APIRequestFactory().get(
        "/apps/scholar/citation-graph/network/multi/",
        {"dois": SEED, "num_related_per_doi": "10", "no_cache": "true"},
    )


def _query_request():
    return APIRequestFactory().get(
        "/apps/scholar/citation-graph/network/query/",
        {"q": "fixture topic", "num_related_per_doi": "2", "no_cache": "true"},
    )


def test_multi_endpoint_returns_seed_and_cited_papers_as_nodes():
    # Arrange
    request = _multi_request()
    # Act
    response = build_network_multi(request, service=_service())
    # Assert
    assert {n["id"] for n in response.data["nodes"]} == {
        SEED,
        "10.1000/a",
        "10.1000/b",
        "10.1000/c",
    }


def test_multi_endpoint_marks_the_titled_seed_node():
    # Arrange
    request = _multi_request()
    # Act
    response = build_network_multi(request, service=_service())
    # Assert
    assert [(n["id"], n["title"]) for n in response.data["nodes"] if n["is_seed"]] == [
        (SEED, "Seed paper")
    ]


def test_multi_endpoint_returns_citation_edges_among_graph_papers():
    # Arrange
    request = _multi_request()
    # Act
    response = build_network_multi(request, service=_service())
    # Assert
    assert {(e["source"], e["target"]) for e in response.data["edges"]} == {
        (SEED, "10.1000/a"),
        (SEED, "10.1000/b"),
        (SEED, "10.1000/c"),
        ("10.1000/a", "10.1000/b"),
        ("10.1000/c", "10.1000/a"),
    }


def test_query_endpoint_keeps_most_cited_references_when_local_is_down():
    # Arrange
    request = _query_request()
    # Act
    response = build_network_query(request, service=_service())
    # Assert
    assert [n["id"] for n in response.data["nodes"] if not n["is_seed"]] == [
        "10.1000/a",
        "10.1000/b",
    ]


def test_query_endpoint_labels_the_online_crossref_source():
    # Arrange
    request = _query_request()
    # Act
    response = build_network_query(request, service=_service())
    # Assert
    assert response.data["metadata"]["source"] == "crossref_online"


def test_extract_doi_normalises_doi_org_urls():
    # Arrange
    text = "https://doi.org/10.1038/Nature14539"
    # Act
    doi = extract_doi(text)
    # Assert
    assert doi == "10.1038/nature14539"


def test_extract_doi_returns_none_for_topics():
    # Arrange
    text = "deep learning review"
    # Act
    doi = extract_doi(text)
    # Assert
    assert doi is None
