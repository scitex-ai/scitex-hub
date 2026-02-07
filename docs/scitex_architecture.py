#!/usr/bin/env python3
"""SciTeX architecture diagram using figrecipe Schematic."""

import matplotlib

matplotlib.use("Agg")

import figrecipe as fr
import scitex as stx


@stx.session
def main(CONFIG=stx.session.INJECTED):
    fr.load_style("SCITEX")

    W, H = 170, 105
    s = fr.Schematic(title="", width_mm=W, height_mm=H)

    bw, bh = 24, 15

    # Row 1 (top): AI Engine centered
    s.add_box(
        "engine",
        "AI Engine",
        x_mm=W / 2,
        y_mm=H - 14,
        width_mm=bw,
        height_mm=bh,
        emphasis="warning",
    )

    # Project container — encloses Files + bottom modules
    s.add_container(
        "project",
        title="Project",
        children=["files", "writer", "scholar", "code", "vis"],
        x_mm=W / 2,
        y_mm=37,
        width_mm=148,
        height_mm=68,
        title_loc="upper left",
    )

    # Row 2 (middle): Files centered
    s.add_box(
        "files",
        "Files",
        x_mm=W / 2,
        y_mm=H / 2,
        width_mm=bw,
        height_mm=bh,
        emphasis="primary",
    )

    # Row 3 (bottom): Writer, Scholar, Code, Vis — same layer, evenly spaced
    bot_y = 13
    spacing = W / 5
    s.add_box(
        "writer",
        "Writer",
        x_mm=spacing * 1,
        y_mm=bot_y,
        width_mm=bw,
        height_mm=bh,
        emphasis="primary",
    )
    s.add_box(
        "scholar",
        "Scholar",
        x_mm=spacing * 2,
        y_mm=bot_y,
        width_mm=bw,
        height_mm=bh,
        emphasis="primary",
    )
    s.add_box(
        "code",
        "Code",
        x_mm=spacing * 3,
        y_mm=bot_y,
        width_mm=bw,
        height_mm=bh,
        emphasis="primary",
    )
    s.add_box(
        "vis",
        "Vis",
        x_mm=spacing * 4,
        y_mm=bot_y,
        width_mm=bw,
        height_mm=bh,
        emphasis="primary",
    )

    # Engine <-> Files
    s.add_arrow("engine", "files")
    s.add_arrow("files", "engine")

    # Files <-> bottom modules
    for mod in ("writer", "scholar", "code", "vis"):
        s.add_arrow("files", mod)
        s.add_arrow(mod, "files")

    # Code -> Vis
    s.add_arrow("code", "vis")

    # Scholar -> Writer
    s.add_arrow("scholar", "writer")

    fig, ax = fr.subplots()
    ax.schematic(s, id="scitex_arch")

    from pathlib import Path

    out = Path(CONFIG.SDIR_OUT) if CONFIG else Path("/tmp")
    output = out / "scitex_architecture.png"
    fr.save(fig, output, verbose=True, validate=False)
    from figrecipe._utils._crop import crop

    cropped, _ = crop(
        output,
        margin_left_mm=5,
        margin_right_mm=5,
        margin_top_mm=5,
        margin_bottom_mm=5,
        return_offset=True,
    )
    print(f"Saved: {cropped}")
    return 0


if __name__ == "__main__":
    main()
