"""Current carousel references real captures with a bounded responsive asset set."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "apps/infra/public_app/static/public_app/images/landing-v2"
TEMPLATE = (
    ROOT
    / "apps/infra/public_app/templates/public_app/landing_partials/landing_app_gallery.html"
)


def test_all_eleven_carousel_pictures_reference_the_current_capture_manifest():
    source = TEMPLATE.read_text()
    start = source.index('<div class="landing-v2-carousel-track"')
    end = source.index('data-carousel-tabs', start)
    region = source[start:end]
    files = set(re.findall(r"public_app/images/landing-v2/([^']+)", region))
    manifest = json.loads((ASSETS / "product-captures-eleven-apps-20261103.json").read_text())
    captures = manifest["captures"]
    assert {c["app"] for c in captures} == {
        "hub",
        "sdk",
        "agent-container",
        "cards",
        "storage",
        "agentic-journal",
        "scholar",
        "figrecipe",
        "writer",
        "stats",
        "live-paper",
    }
    declared = {row["file"] for capture in captures for row in capture["renditions"]}
    assert files == declared
    assert len(files) == 33
    assert region.count("<picture>") == 11
    assert "-20261102-" in region
    for capture in captures:
        assert datetime.fromisoformat(capture["captured_at_utc"]).tzinfo is not None
        assert (
            len(capture["raw_sha256"])
            == len(capture["privacy_masked_png_sha256"])
            == 64
        )
        for row in capture["renditions"]:
            path = ASSETS / row["file"]
            assert path.parent == ASSETS and path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
            assert path.stat().st_size == row["bytes"] <= 350_000
            with Image.open(path) as image:
                assert image.size == (row["width"], row["height"])
                assert image.width * 5 == image.height * 8


def test_actual_capture_disclosure_does_not_claim_unedited_or_uniform_mnist_inputs():
    source = TEMPLATE.read_text()
    assert "Unedited interface captures" not in source
    assert "hidden for privacy" in source
    assert "Sample two-group analysis" in source
    assert "Three synthetic figures with a selected line" in source
    assert "not research findings" in source
    assert "MNIST reference library" in source
    manifest = json.loads((ASSETS / "product-captures-eleven-apps-20261103.json").read_text())
    assert manifest["asset_substitution"] is False
    assert manifest["allowed_stateless_post_exceptions"] == [
        "/apps/stats/api/recommend-test",
        "/apps/stats/api/run",
        "/apps/stats/api/plot",
        "/apps/figrecipe/api/switch",
    ]
    assert (
        sum(
            p.stat().st_size
            for p in ASSETS.iterdir()
            if p.suffix in {".jpg", ".png", ".webp"}
        )
        <= 2_500_000
    )
