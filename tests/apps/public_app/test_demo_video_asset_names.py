"""Demo video URLs must name files that exist on the media volume.

The media volume holds recorded artifacts whose filenames predate the
SciTeX Cloud -> SciTeX Hub rename (``scitex-cloud-v0.11.5-demo.mp4``). The
rename rewrote the paths in code but not the files, so prod served 404s for
the Hub demo thumbnails and videos. The slugs may say ``scitex-hub``; the
file paths must match the published assets.
"""

from pathlib import Path

from apps.infra.public_app.views.pages_data import VIDEO_CATALOG

# Inventory of /app/media/videos on the prod media volume (2026-09-14).
PUBLISHED_MEDIA_VIDEOS = {
    "crossref-local-v0.3.1-demo-thumbnail.png",
    "crossref-local-v0.3.1-demo.mp4",
    "crossref-local-v0.3.1-demo.pdf",
    "figrecipe-v0.14.0-demo-thumbnail.png",
    "figrecipe-v0.14.0-demo.mp4",
    "figrecipe-v0.14.0-demo.pdf",
    "orochi-demo-thumbnail.jpg",
    "scitex-automated-research-demo-manuscript.pdf",
    "scitex-automated-research-demo-revision.pdf",
    "scitex-automated-research-demo-thumbnail.png",
    "scitex-automated-research-demo.mp4",
    "scitex-cloud-v0.11.5-demo-2x.gif",
    "scitex-cloud-v0.11.5-demo-4x.gif",
    "scitex-cloud-v0.11.5-demo-8x.gif",
    "scitex-cloud-v0.11.5-demo-thumbnail.png",
    "scitex-cloud-v0.11.5-demo.mp4",
    "scitex-cloud-v0.9.3-demo-thumbnail.png",
    "scitex-cloud-v0.9.3-demo.mp4",
    "scitex-writer-v2.2.0-demo-manuscript.pdf",
    "scitex-writer-v2.2.0-demo-revision.pdf",
    "scitex-writer-v2.2.0-demo-thumbnail.png",
    "scitex-writer-v2.2.0-demo.mp4",
    "scitex-writer-v2.2.0-demo.pdf",
}


def test_catalog_media_paths_name_published_files():
    # Arrange
    media_paths = [
        path
        for entry in VIDEO_CATALOG.values()
        for path in (entry.get("url"), entry.get("thumbnail"))
        if path and path.startswith("/media/videos/")
    ]

    # Act
    missing = sorted(
        path for path in media_paths if Path(path).name not in PUBLISHED_MEDIA_VIDEOS
    )

    # Assert
    assert missing == []
