#!/usr/bin/env python3
"""Render real host CSS: opaque native/SDK frames, gutters and overlay stacking."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


def verify(stylesheet: Path, chromium: str) -> dict:
    css = stylesheet.read_text()
    rows = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium, headless=True)
        for layout in ("native", "sdk"):
            for theme in ("light", "dark"):
                for width in (1440, 390):
                    page = browser.new_page(viewport={"width": width, "height": 600})
                    frame_class = "workspace-three-col" if layout == "sdk" else ""
                    page.set_content(f'''<html data-theme="{theme}"><head><style>
:root{{--_scitex-03:#234;--_scitex-04:#345;--_scitex-05:#789;--_scitex-06:#abc}}
html,body{{margin:0;min-height:600px}}body{{position:relative;background:#ddd}}
#frame{{width:90vw;margin:auto;min-height:600px;background:#fff}}
@media(max-width:600px){{#frame{{width:100%}}}}
#header{{position:fixed;top:0;right:0;width:120px;height:100px;z-index:10000}}
#dock{{position:fixed;top:10px;right:10px;width:80px;height:80px;z-index:11000}}
#modal{{position:fixed;top:10px;right:10px;width:80px;height:80px;z-index:20000}}
{css}</style></head><body><div id="header"></div><div id="dock"></div>
<div id="frame" class="{frame_class}"><div id="modal"></div></div></body></html>''')
                    box = page.locator("#frame").bounding_box()
                    visible = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    hidden_style = page.add_style_tag(
                        content="body::before{visibility:hidden!important}"
                    )
                    hidden = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    hidden_style.evaluate("element=>element.remove()")
                    difference = ImageChops.difference(visible, hidden)
                    inside = difference.crop(
                        (int(box["x"]) + 2, 150, int(box["x"] + box["width"]) - 2, 550)
                    )
                    inside_pixels = sum(
                        max(pixel) > 1
                        for pixel in zip(*[iter(inside.tobytes())] * 3, strict=True)
                    )
                    gutter_pixels = None
                    if box["x"] > 4:
                        gutter = difference.crop((0, 150, int(box["x"]) - 2, 550))
                        gutter_pixels = sum(
                            max(pixel) > 1
                            for pixel in zip(*[iter(gutter.tobytes())] * 3, strict=True)
                        )
                    hits = []
                    for target in ("modal", "dock", "header"):
                        hits.append(
                            page.evaluate(
                                "()=>document.elementFromPoint(innerWidth-30,30).id"
                            )
                        )
                        page.locator("#" + target).evaluate(
                            "element=>element.hidden=true"
                        )
                    row = {
                        "layout": layout,
                        "theme": theme,
                        "width": width,
                        "inside_bubble_pixels": inside_pixels,
                        "gutter_bubble_pixels": gutter_pixels,
                        "overlay_hits": hits,
                    }
                    row["passed"] = (
                        inside_pixels == 0
                        and (gutter_pixels is None or gutter_pixels > 0)
                        and hits == ["modal", "dock", "header"]
                    )
                    rows.append(row)
                    page.close()
        browser.close()
    return {"cases": rows, "passed": all(row["passed"] for row in rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--stylesheet", type=Path)
    args = parser.parse_args()
    stylesheet = args.stylesheet or (
        Path(__file__).resolve().parents[2]
        / "static/shared/css/layouts/platform-backdrop.css"
    )
    result = verify(stylesheet, args.chromium)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
