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

## Eleven application capture set: SDK and Hub

`product-captures-eleven-apps-20261103.json` retains the nine leaf-app captures,
adds the actual SDK creator view, and reuses the actual Hub launcher from
`product-captures-20261102.json`. Both earlier manifests and every historical
asset remain unchanged. It indexes eleven applications and thirty-three responsive
renditions; image timestamps and filenames use the capture host's observed UTC
date rather than forcing the manifest task date.

- `sdk-20261102-*`: actual authenticated `/apps/sdk/` default starter catalog
  and creation form, with four real starter options. The screenshot does not
  claim that an app was scaffolded or validated. Owner/project controls and
  target/app/server/token fields were privacy-filtered before any PNG was saved.
  The recorded original hash identifies that privacy-filtered browser capture;
  an unmasked private-data image was not persisted.

The SDK capture allowed GET only. No create, scaffold, validate, filesystem/user
write, dev-install, publish, model call or other POST was executed. No application
HTML, data or asset response was substituted. The dock was minimized through its
normal control; only faithful resize/compression followed the privacy filter.
This records actual interface state, not complete backend feature health or
production availability.

## Nine leaf application capture set

`product-captures-nine-apps-20261103.json` indexes the nine leaf applications:
Agent Container, Cards, Storage, Scholar, Stats, FigRecipe, Writer, Live Paper,
and Agentic Journal. It combines five unchanged earlier captures with four new
actual development captures. The Hub launcher is excluded from this nine-app set;
its historical assets and `product-captures-20261102.json` remain unchanged.
The manifest task date is 2026-11-03; new image filenames and per-image timestamps
use the capture host's observed UTC date, 2026-11-02, rather than forcing that date.

The new four images are actual authenticated development views at
<https://compute-03-net.scitex.ai/>, captured at 1440 × 900, device scale 1:

- `agent-container-20261102-*`: cached fleet inventory and controls, with 21
  roster rows. The visible stale-cache banner is preserved. Liveness badges are
  cached inventory metadata, not evidence of model activity or goal completion.
  Non-public agent labels and account/project controls are hidden. No agent
  conversation, detail/status/tail read, control or goal operation was performed.
- `cards-20261102-*`: the real dedicated task-board Stats view. Private task
  content and account/project identifiers are hidden. Activity/status counts are
  the actual visible UI values; this is not a seeded MNIST task dataset. No DM
  API or message request was allowed; no tasks were edited or sent.
- `storage-20261102-*`: the actual MNIST project-scoped Usage iframe after its
  sunburst finished rendering (36 SVG segments). Path/generation/breadcrumb
  labels are hidden. No move, delete, duplicate scan or planning operation was
  performed. The chart is not substituted with a PNG or a different frame.
- `agentic-journal-20261102-*`: the native author guidance and submission workflow,
  with an honestly empty user archive. No sample submission, review, publication,
  model call or fabricated record was created for the screenshot.

For these four operational views, privacy filters were applied before the first
PNG was persisted. The recorded raw/original hash therefore identifies the
privacy-filtered browser capture, not an unmasked private-data image. Account and
project controls, private task text, non-public agent names and relevant path
labels are masked; exact selectors/styles are recorded in the manifest. The dock
was minimized using its normal control. No application HTML, data, script or
stylesheet response was replaced. Only faithful resizing and JPEG/WebP compression
were applied after capture; no generated imagery was used.

These four captures allow GET only, block DM/control/message/goal endpoints,
block all POSTs, and disable WebSockets/SSE. The manifest separately preserves
historical exceptions for the earlier Stats sample computation and Writer Abstract
preview; neither was repeated for this four-app extension. Captures document
visible interface state, not complete feature health, independent scientific
verification or production availability.

## Earlier six-screen development capture group — 2026-11-02 UTC

`product-captures-20261102.json` records the actual capture times, original PNG
hashes, privacy-masked PNG hashes, responsive rendition hashes and dimensions.
The six new capture sets were taken from the running development site at
<https://compute-03-net.scitex.ai/> with a 1440 × 900 viewport and device scale 1.
The date comes from the capture host's observed UTC clock.

- `hub-20261102-*`: current application launcher. The account/project label is
  hidden; the actual app tiles and their labels are unchanged. A tile is not
  evidence that its backend is available.
- `figrecipe-20261102-*`: existing six-row synthetic worksheet, showing separate
  X/Y axis-role badges and unchanged column names. This worksheet is not MNIST.
- `scholar-20261102-*`: the actual MNIST project's four curated references and
  native metadata reader, after the real library seed and deployed reader UI.
  The selected OpenML paper has no stored abstract, which is shown honestly.
  No search, enrichment, download or citation-graph operation was performed.
  The served reader stylesheet matched SHA-256
  `623735bc562ea3018760502ab1e368944b9722146b53ac851689ef072e61b3f1`;
  the visible title measured 241 pixels wide and the close button 44 × 44 pixels.
- `writer-20261102-*`: actual MNIST example Abstract source and its genuinely
  compiled one-page section preview. The source explicitly says this is not a
  research finding and the claims have not been independently verified. Exactly
  one approved Abstract-preview POST was permitted, pinned to the authorized
  project, section path and content SHA-256
  `6933993915a0903e8b14b294756430f88a3b10a44209760c326a5ca79b1f3f2c`.
  It returned HTTP 200 and the actual PDF SHA-256 was
  `c60728aa3910c56534be7af09caa453d0274d15e26cf8d103562161288a2d364`.
  Abstract/Methods/Results, claims, provenance and the existing root PDF hashes
  stayed unchanged; the full Writer manuscript PDF remained absent. No save or
  full-manuscript compile was allowed. The root Live Paper PDF was not imported
  as Writer output.
- `stats-20261102-*`: built-in two-group sample, showing the actual recommended
  Welch test and computed result. This sample is not MNIST.
- `live-paper-20261102-*`: existing MNIST demonstration bundle with its claims
  and PDF. The document explicitly labels these as example claims, not research
  findings. No models were trained or downloaded during capture.

These are actual application responses, without replacement HTML, scripts,
styles or application data. Privacy masking hides account/project controls and
file-tree/tooltips if present; it does not replace any application content.
The dock was minimized through its normal control. After masking, only faithful
resizing and JPEG/WebP compression were applied; no generated imagery was used.
The original PNGs remain in the private audit capture bundle, rather than exposing
unmasked account context in public static files.

All non-GET application requests were blocked except the pinned Writer Abstract
preview described above and the three source-reviewed, stateless Stats sample operations: `api/recommend-test`, `api/run`, and `api/plot`.
They compute recommendations, a test result, and an in-memory SVG/PNG; project
save, report-save and FigRecipe import endpoints remained blocked. WebSockets and
SSE were disabled. No full-manuscript compile, annotation, message, project save,
recipe write, model call, or Scholar Graph backfill was performed. The approved
single-section preview operation genuinely compiles an isolated Abstract artifact.

The recorded source checkouts are contextual evidence, not proof that an
unpublished source preview is an official package release. The captures likewise
prove the visible state at their recorded time, not complete feature coverage,
performance, independent scientific verification or production availability.

## Historical product-guide captures

The historical renditions below come from tracked in-repository guide screenshots,
except the older Stats capture (see below). They are
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
`scholar-demo.mp4`, `writer-demo.mp4`, and `visualizer-demo.mp4`. These legacy
recordings and guide renditions remain as historical sources. The earlier six-screen group uses the dated actual development captures documented
above; the separate nine-leaf manifest identifies the expanded set.

## SciTeX Clew DAG

- Source: `src/scitex_clew/dag.png` in the public
  [scitex-ai/scitex-clew](https://github.com/scitex-ai/scitex-clew) repository.
- Source repository commit at retrieval: `cf79b2bc1c4eed0b9e865d8e07b08cf152de58f6`.
- Raw file SHA-256:
  `d0bc3e398f9214e0b1423afe0d467c520b588be656f8b3ced37cea7608393508`.
- `clew-dag.png` is the unmodified upstream file. `clew-dag-640.webp` is a responsive
  rendition of that file.

## FigRecipe representative Figure scene (2026-11-03 gallery cohort)

The active gallery uses the native Figure view with three synthetic example recipes, a selected Training line and its eight-point Details. Figure 1/2/3 navigation and the Objects list show the actual hierarchy; one canvas is visible at a time. Values are illustrative, not MNIST results. Reproduce the fixture with `scripts/demo/landing_figrecipe_scene/generate_examples.py`; its adjacent README and PROVENANCE.json record capture hashes and the real UTC timestamp. Historical worksheet images are retained.

## Cards MNIST Board replacement (2026-11-03)

The active eleven-app gallery's Cards entry replaces the historical Stats image
with the actual authenticated development `/apps/cards/board-v3` Timeline → Simple view at
1440 × 875, naturally cropped to the actual 1296 × 810 app area. Four `Demo:`
cards illustrate an MNIST workflow; these are synthetic
UI stages, **not research progress or agent activity**. The Show done filter is
on. Account/project controls and human card metadata were masked before the
first saved image; the four example titles remain visible. The three new
renditions total 90,682 bytes. Historical Stats images and manifests remain.

The unchanged Cards source was `bfebb541a36cf0d8438b92ca86904a7ca0c426b6`
(version 0.56.22). Hub `fc46fb5782ef114bae90ae5d30e391c0f071831b`
scopes utility-sidebar sizing to the host's own panes: previously a broad host
rule forced nested Cards Details to full width and hid the Board. The final
capture used the actually served fixed CSS, without response substitution.

`scripts/showcase/mnist_cards_board.py` reproduces the explicitly approved,
idempotent fixture through the public Cards task API. It uses the authenticated
human CLI principal, fixed IDs and a fixture marker. `kind=status` is descriptive;
non-runnable statuses/blockers are checked independently by Cards' classifier.
External plugin handlers are disabled only for fixture insertion; builtin
created-event notifications are separately muted and checked to have zero
recipients. Core validation and persistence remain active. No agent assignment,
DM, model, relay, session or compute action is requested. The script defaults to
read-only planning and offers guarded cleanup of unchanged fixture rows only.
The live browser capture blocked application writes, real WebSockets and native
agent routes, and verified unchanged project-scope and owner-session-file hashes.

To reproduce the view, open the Board, search `project:example-project-mnist`,
clear any existing Board-local project filter chip, select Details → Board →
Timeline → Simple, and enable Details → Filters → Show done. These local
controls do not change the account's selected project. Capture only after the visible rows are
confirmed to be the four fixture IDs, and mask account/project/lane identifiers.
