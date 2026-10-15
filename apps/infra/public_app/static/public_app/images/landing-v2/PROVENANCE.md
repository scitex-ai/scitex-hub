# Landing V2 asset provenance

These files are production renditions, not invented interface mockups. Source paths and
hashes are recorded so the page can be re-audited from the repository.

## Research photography

- `research-collaboration-*`: Edward Jenner, “Two Scientists Working Inside the
  Laboratory,” Pexels photo 4031694.
  Source: <https://www.pexels.com/photo/two-scientists-working-inside-the-laboratory-4031694/>
  Downloaded source SHA-256: `23674654f7bc9d4e0bb672e5b8df53e514effeb9687d58dd7dd48be350318d21`.
- `research-computer-*`: Tima Miroshnichenko, “Medical Professional using
  Computer,” Pexels photo 9574502.
  Source: <https://www.pexels.com/photo/medical-professional-using-computer-9574502/>
  Downloaded source SHA-256: `712b33388281695233e85a5286ee2cb62347ed4b9b10dd86d572fbff5c73d066`.
- License: [Pexels License](https://www.pexels.com/license/). The photographs are
  stock imagery used as an illustrative human layer. The people shown are not SciTeX
  customers, employees, or endorsers; no endorsement is implied.

The 640 and 1280 pixel JPEG/WebP renditions were resized and cropped locally from the
source photographs with Pillow; no generated imagery was added.

## Actual SciTeX product captures

The carousel renditions come from tracked in-repository guide screenshots, except
Stats (see below). They are
real captures of the application; only resize/compression was applied. The captions on
the page describe only what is visible and do not claim that a static image proves
feature availability or performance.

| Slide | Tracked source | Source SHA-256 |
| --- | --- | --- |
| Hub | `apps/workspace/docs_app/static/docs_app/images/howto/projects-01-home.jpg` | `77651460679b2f4f19ebd1fa48dd9e6f8e9509435be5a104152ddb5643ba9cc5` |
| Scholar | `apps/workspace/docs_app/static/docs_app/images/howto/scholar-01-open.jpg` | `a5611dfa5714243db49c30cab715c320aa131d31bfadeab8be3efdc0c0f78aa5` |
| Writer | `apps/workspace/docs_app/static/docs_app/images/howto/writer-03-edit.jpg` | `a6757c06329754379b414ae17b8265d43bcbc6751169e8236cb54dcd2cf32b1e` |
| FigRecipe | `apps/workspace/docs_app/static/docs_app/images/howto/figrecipe-02-templates.jpg` | `69799755ac077da834eebf989d2de5031941412898eb7c4eff8ac71ada12b2a2` |
| Stats | Development capture `/tmp/shots/stats-1280.png` on scitex-compute-03 (no tracked guide source exists) | `4b8a0c4a348100999d834ec962b6e23c5eacc8ad3f09d4db9eefd146616a4678` |

### Stats slide source (development capture, not a tracked guide)

No tracked Stats guide screenshot exists under
`apps/workspace/docs_app/static/docs_app/images/howto/`, so the Stats renditions
(`stats-768.webp`, `stats-1200.webp`, `stats-1200.jpg`) were resized with Pillow
from a real capture of the Stats leaf app (`/apps/stats/`, v0.2.28) running in the
`scitex-hub-dev-django-1` container on scitex-compute-03 on 2026-09-27. The capture
used an anonymous session: the built-in sample two-group dataset was loaded
(Group 1 n=8, Group 2 n=8) and Calculate was pressed, so the shot shows the data
input, the recommended Welch's t-test, the results table (t(14) = -6.35,
p < .001, d = -3.18), and the box plot. Viewport capture only (1280x800, no
full-page stitching); the results pane was scrolled so the statistics and chart
are visible. No personal data, no local paths, no dock overlap, no broken icon
glyphs. Only resize/compression was applied to the renditions. The source PNG is
outside the repository; its SHA-256 is recorded in the table above.

Related tracked demo videos remain available at
`apps/infra/public_app/static/public_app/videos/landing/`: `hub-demo.mp4`,
`scholar-demo.mp4`, `writer-demo.mp4`, and `visualizer-demo.mp4`. The carousel uses the
cleaner tracked guide captures rather than frames that expose local paths, third-party
publisher pages, or unsupported manuscript claims.

## SciTeX Clew DAG

- Source: `src/scitex_clew/dag.png` in the public
  [scitex-ai/scitex-clew](https://github.com/scitex-ai/scitex-clew) repository.
- Source repository commit at retrieval: `cf79b2bc1c4eed0b9e865d8e07b08cf152de58f6`.
- Raw file SHA-256:
  `d0bc3e398f9214e0b1423afe0d467c520b588be656f8b3ced37cea7608393508`.
- `clew-dag.png` is the unmodified upstream file. `clew-dag-640.webp` is a responsive
  rendition of that file.
