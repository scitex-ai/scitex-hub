"""Japanese academic email recognition — the ONE canonical checker.

Ownership (operator CCT4555): ``is_japanese_academic_email`` +
``JAPANESE_ACADEMIC_DOMAINS`` here are the SURVIVING checker. Two notes on
what this is not:

* ``apps.infra.auth_app.models`` and ``apps.infra.accounts_app.models.profile``
  both re-export these names (backwards compatibility for every existing
  import); neither defines its own copy. A second copy is how the flags
  drifted apart before — there is exactly one definition, in this module.
* The worldwide ``is_academic_email`` built on PyPI ``swot`` (PLUS the JP
  list) lives only on branch ``feature/lp-beta-polish`` and was never merged
  to develop. It is NOT ported here: it needs a new dependency and a
  worldwide-eligibility decision the operator has not made. If that lands,
  it lands here, behind this module's interface.

Deliberately dependency-free (stdlib only, no Django): the signup funnel,
the billing selector and the unit tests all import this without a settings
context.
"""

from __future__ import annotations

__all__ = ["JAPANESE_ACADEMIC_DOMAINS", "is_japanese_academic_email"]

# Japanese Academic domains to recognize
JAPANESE_ACADEMIC_DOMAINS = [
    # Japanese Academic (.ac.jp) - All academic institutions
    ".ac.jp",
    ".u-tokyo.ac.jp",
    ".kyoto-u.ac.jp",
    ".osaka-u.ac.jp",
    ".tohoku.ac.jp",
    ".nagoya-u.ac.jp",
    ".kyushu-u.ac.jp",
    ".hokudai.ac.jp",
    ".tsukuba.ac.jp",
    ".hiroshima-u.ac.jp",
    ".kobe-u.ac.jp",
    ".waseda.jp",
    ".keio.ac.jp",
    # Government Research Institutions (.go.jp)
    ".go.jp",  # Broader government research support
    ".riken.jp",
    ".aist.go.jp",
    ".nict.go.jp",
    ".jaxa.jp",
    ".jst.go.jp",
    ".nims.go.jp",
    ".nies.go.jp",
]


def is_japanese_academic_email(email):
    """Check if email belongs to Japanese academic institution"""
    if not email:
        return False
    try:
        domain = email.lower().split("@")[1]
        # Check if domain matches exactly or ends with the academic domain
        for academic_domain in JAPANESE_ACADEMIC_DOMAINS:
            # Remove leading dot for exact matching
            clean_domain = academic_domain.lstrip(".")
            if domain == clean_domain or domain.endswith(academic_domain):
                return True
        return False
    except (IndexError, AttributeError):
        return False
