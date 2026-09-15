"""Citation network from the public Crossref REST API.

Used when the crossref-local server is unreachable (dev has none), so the
Citations tab still draws a real graph: seed papers, the works they cite
(ranked by citation count) and the citation links among all of them.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Optional

CROSSREF_WORKS = "https://api.crossref.org/works"
USER_AGENT = "SciTeX/1.0 (https://scitex.ai; mailto:contact@scitex.ai)"
SELECT = "DOI,title,author,issued,container-title,is-referenced-by-count,reference"
# Crossref rejects very long filter strings; 40 DOIs stays well under the limit.
BATCH = 40
MAX_CANDIDATES = 120

_DOI_RE = re.compile(r"(10\.\d{4,9}/\S+)", re.IGNORECASE)

FetchJson = Callable[[str, Dict[str, object]], Dict]


def _requests_fetch(url: str, params: Dict[str, object]) -> Dict:
    import requests

    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def extract_doi(text: str) -> Optional[str]:
    match = _DOI_RE.search(text.strip())
    if not match:
        return None
    return match.group(1).rstrip(".,;)").lower()


def _year(item: Dict) -> int:
    parts = (item.get("issued") or {}).get("date-parts") or [[None]]
    return int(parts[0][0]) if parts and parts[0] and parts[0][0] else 0


def _authors(item: Dict) -> List[str]:
    names = []
    for a in (item.get("author") or [])[:6]:
        family = a.get("family") or a.get("name") or ""
        given = a.get("given") or ""
        names.append(f"{family} {given[:1]}".strip())
    return [n for n in names if n]


def _ref_dois(item: Dict) -> List[str]:
    return [r["DOI"].lower() for r in item.get("reference") or [] if r.get("DOI")]


def _node(item: Dict, is_seed: bool) -> Dict:
    titles = item.get("title") or [""]
    journals = item.get("container-title") or [""]
    return {
        "id": item["DOI"].lower(),
        "title": (titles[0] or "")[:300],
        "year": _year(item),
        "authors": _authors(item),
        "journal": journals[0] if journals else "",
        "citation_count": int(item.get("is-referenced-by-count") or 0),
        "reference_count": len(item.get("reference") or []),
        "similarity_score": 100.0 if is_seed else 0.0,
        "is_seed": is_seed,
    }


class OnlineCrossrefGraphSource:
    """Build graph dicts (same shape as CitationGraph.to_dict()) from Crossref."""

    def __init__(self, fetch_json: Optional[FetchJson] = None):
        self.fetch_json = fetch_json or _requests_fetch

    def _works(self, dois: Iterable[str]) -> List[Dict]:
        dois = list(dict.fromkeys(d.lower() for d in dois))
        items: List[Dict] = []
        for i in range(0, len(dois), BATCH):
            chunk = dois[i : i + BATCH]
            data = self.fetch_json(
                CROSSREF_WORKS,
                {
                    "filter": ",".join(f"doi:{d}" for d in chunk),
                    "select": SELECT,
                    "rows": len(chunk),
                },
            )
            items.extend((data.get("message") or {}).get("items") or [])
        return [it for it in items if it.get("DOI")]

    def search_seed_dois(self, query: str, limit: int = 1) -> List[str]:
        doi = extract_doi(query)
        if doi:
            return [doi]
        data = self.fetch_json(
            CROSSREF_WORKS,
            {
                "query.bibliographic": query,
                "filter": "has-references:true",
                "select": "DOI",
                "rows": limit,
            },
        )
        items = (data.get("message") or {}).get("items") or []
        return [it["DOI"].lower() for it in items if it.get("DOI")][:limit]

    def build_from_dois(self, dois: List[str], num_related_per_doi: int = 20) -> Dict:
        seeds = self._works(dois)
        seed_ids = {s["DOI"].lower() for s in seeds}

        candidates: List[str] = []
        for s in seeds:
            candidates.extend(d for d in _ref_dois(s) if d not in seed_ids)
        candidates = list(dict.fromkeys(candidates))[:MAX_CANDIDATES]
        related = self._works(candidates)
        related.sort(key=lambda it: it.get("is-referenced-by-count") or 0, reverse=True)
        related = related[: num_related_per_doi * max(1, len(seeds))]

        nodes = [_node(s, True) for s in seeds] + [_node(r, False) for r in related]
        top = max((n["citation_count"] for n in nodes if not n["is_seed"]), default=0)
        for n in nodes:
            if not n["is_seed"] and top:
                n["similarity_score"] = round(100.0 * n["citation_count"] / top, 1)

        ids = {n["id"] for n in nodes}
        edges = []
        seen = set()
        for item in seeds + related:
            src = item["DOI"].lower()
            for tgt in _ref_dois(item):
                if tgt in ids and tgt != src and (src, tgt) not in seen:
                    seen.add((src, tgt))
                    edges.append(
                        {"source": src, "target": tgt, "type": "cites", "weight": 1.0}
                    )

        seed_list = [s["DOI"].lower() for s in seeds]
        return {
            "seed": seed_list[0] if seed_list else "",
            "seed_dois": seed_list,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "source": "crossref_online",
                "num_related_per_doi": num_related_per_doi,
                "num_seeds": len(seed_list),
            },
        }

    def build_from_query(
        self, query: str, num_related_per_doi: int = 20, search_limit: int = 1
    ) -> Dict:
        dois = self.search_seed_dois(query, limit=search_limit)
        if not dois:
            return {
                "seed": "",
                "seed_dois": [],
                "nodes": [],
                "edges": [],
                "metadata": {
                    "source": "crossref_online",
                    "query": query,
                    "error": "No papers with DOI found",
                },
            }
        graph = self.build_from_dois(dois, num_related_per_doi=num_related_per_doi)
        graph["metadata"]["query"] = query
        return graph
