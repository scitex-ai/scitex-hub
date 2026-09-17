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

# Captioned guides under /app/media/videos/demos/, rendered by
# scripts/demo_videos/record.py and copied onto the volume (docs/ops/demo-videos.md).
RENDERED_DEMO_GUIDES = {
    "projects-2026-09-14.en.mp4",
    "projects-2026-09-14-thumbnail.png",
    "writer-2026-09-14.en.mp4",
    "writer-2026-09-14-thumbnail.png",
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
        path
        for path in media_paths
        if Path(path).name not in PUBLISHED_MEDIA_VIDEOS | RENDERED_DEMO_GUIDES
    )

    # Assert
    assert missing == []


def test_published_renditions_reference_named_media_files():
    """A rendition the player switches to must name a file the volume holds.

    The language switch points the player at the other language's video and
    captions. A typo in either path is a broken button, not a broken page, so it
    has to be caught here: every rendition a narrated guide advertises must name
    a file from the published inventory, and every alternate UI-locale rendition
    must carry a note saying what the viewer is looking at.
    """
    # Arrange
    from apps.infra.public_app.views.demo_video_languages import languages_for

    known = PUBLISHED_MEDIA_VIDEOS | RENDERED_DEMO_GUIDES

    # Act
    problems = []
    for key, entry in VIDEO_CATALOG.items():
        if not entry.get("narrated"):
            continue
        renditions = languages_for(entry)
        if len(renditions) < 2:
            problems.append(f"{key}: a narrated guide ships both languages")
        for rendition in renditions:
            for field in ("src", "captions"):
                name = Path(rendition[field]).name
                if name and name not in known:
                    problems.append(f"{key}: {field} names unpublished file {name}")
            if not rendition["canonical"] and not rendition["note"]:
                problems.append(f"{key}: alternate rendition {rendition['code']} needs a note")

    # Assert
    assert problems == []
