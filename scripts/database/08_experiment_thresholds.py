#!/usr/bin/env python3
"""Experiment: Find optimal reference threshold for JCR-style IF calculation."""

import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "openalex.db"
JCR_PATH = Path("/home/ywatanabe/proj/crossref-local/examples/03_impact_factor/01_compare_jcr_out/all_combined.csv")

def load_jcr():
    jcr = {}
    with open(JCR_PATH) as f:
        for row in csv.DictReader(f):
            if row.get('issn') and row.get('jcr_if'):
                jcr[row['issn']] = float(row['jcr_if'])
    return jcr

def calculate_if(conn, issn, year, min_refs):
    """Calculate IF with given minimum references threshold."""
    window_years = (year - 2, year - 1)

    if min_refs > 0:
        ref_filter = f"AND json_array_length(referenced_works_json) > {min_refs}"
    else:
        ref_filter = ""

    # Denominator
    cursor = conn.execute(f"""
        SELECT COUNT(*) FROM works
        WHERE issn = ? AND year IN (?, ?)
        {ref_filter}
    """, (issn, *window_years))
    articles = cursor.fetchone()[0]

    if articles == 0:
        return None

    # Numerator
    cursor = conn.execute(f"""
        SELECT COUNT(*) FROM citations c
        JOIN works w ON c.cited_id = w.openalex_id
        WHERE w.issn = ? AND w.year IN (?, ?) AND c.citing_year = ?
        {ref_filter}
    """, (issn, *window_years, year))
    citations = cursor.fetchone()[0]

    return round(citations / articles, 1)

def main():
    jcr = load_jcr()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA cache_size=-1000000")

    # Test thresholds: 0, 10, 15, 20, 25, 30
    thresholds = [0, 10, 15, 20, 25, 30, 40]
    issns = list(jcr.keys())[:30]
    year = 2023

    print("=" * 100)
    print(f"{'Threshold':<12}", end="")
    print(f"{'Avg Ratio':<12}", end="")
    print(f"{'Good (0.8-1.2)':<16}", end="")
    print(f"{'Median Ratio':<14}", end="")
    print(f"{'Std Dev':<12}")
    print("=" * 100)

    for threshold in thresholds:
        ratios = []
        for issn in issns:
            calc_if = calculate_if(conn, issn, year, threshold)
            jcr_if = jcr.get(issn)
            if calc_if and jcr_if and jcr_if > 0:
                ratios.append(calc_if / jcr_if)

        if ratios:
            avg = sum(ratios) / len(ratios)
            good = sum(1 for r in ratios if 0.8 <= r <= 1.2)

            sorted_ratios = sorted(ratios)
            median = sorted_ratios[len(sorted_ratios)//2]

            variance = sum((r - avg)**2 for r in ratios) / len(ratios)
            std = variance ** 0.5

            print(f">{threshold:<11}", end="")
            print(f"{avg:<12.2f}", end="")
            print(f"{good}/{len(ratios):<14}", end="")
            print(f"{median:<14.2f}", end="")
            print(f"{std:<12.2f}")

    print("=" * 100)
    conn.close()

if __name__ == "__main__":
    main()
