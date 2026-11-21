# Acceptance walk — research lifecycle on SciTeX Cloud (dev), 2026-11-19

**Definition of ready (user-confirmed):** a researcher can complete the whole
research lifecycle on SciTeX Cloud.

**Target:** the DEVELOPMENT stack on `scitex-compute-03` (Docker compose
project `scitex-hub-dev`, Django `127.0.0.1:8000`), reached through an SSH
tunnel; Playwright (headless Chromium, 1440x900) driven on compute-03.
Production was not touched. Hub banner: **SciTeX Cloud v0.22.0a7**; the dev
checkout was on `preview/docs-skill-summary-1116` (`cfcf8a861f`).

**Screenshots:** `/scratch/ywatanabe/hub-acceptance/` on `scitex-compute-02`
(mirrored from compute-03). Each `NN-name_K.png` has a sibling `NN-name.txt`
with the URL, visible page text and console/HTTP errors captured at that step.

## Verdict

**Not ready.** Sign-up, project creation, literature search, the Writer
editor/compiler, Stats/FigRecipe UIs and Live Paper rendering work. The
lifecycle breaks at three hard points:

1. **Run the analysis** — the browser terminal cannot start on dev (compute
   image unset), and there is no other Hub-side job runner.
2. **Clew** — `scitex.clew` is not importable in the dev image (umbrella /
   leaf version skew), so no run can be recorded, verified or claimed, and the
   Agentic Journal intake gate (which requires a verified Clew run) cannot pass.
3. **Research template** — choosing *SciTeX Full* yields the minimal skeleton;
   the scitex-template `research` scaffold is never applied.

## Lifecycle table

| # | Step | Result | Evidence | Owning package |
|---|------|--------|----------|----------------|
| 1a | Sign up (username/email/password + 6-digit email OTP) | **PASS** | `01-signup_1..2.png`, `01b-verify_1.png` — OTP auto-submits and lands on `/new/` | scitex-hub (auth_app) |
| 1b | Sign in with ORCID | **PARTIAL** | ORCID `SocialApp` row + client env are configured; `/auth/social/orcid/login/` → 302 to `orcid.org/oauth/authorize` (`/authenticate` scope). The user's dev account is **not linked** to its ORCID iD (no SocialAccount / LinkedIdentity; `profile.orcid` empty), and Settings has no "linked accounts" section to link one from an existing account. OAuth round-trip not exercised (would re-link the user's account). | scitex-hub (auth_app/account_linking) |
| 2 | Create project from the research template | **FAIL** | `03b-create-full_1..2.png`; server log `template_ops: Project path already exists … skipping template`. See finding F1. | scitex-hub (project_app) + scitex-template |
| 2b | Project is a git repo on Gitea | **PARTIAL** | Gitea repo created + cloned + 2 commits pushed. The seeded samples are left **uncommitted** (`?? data/ figures/ references.bib`, `M README.md`, dirty `.scitex/writer` submodule) and README says "This is an empty project directory" (`04-tour_1.png`). | scitex-hub (project_app) |
| 2c | Issues | **FAIL → fixed in this PR** | Creating an issue persisted #1 but answered **HTTP 500** `IssueEvent() got unexpected keyword arguments: 'actor'` (`08-issue_1.png`, `08-issue_2.png`). See F2. | scitex-hub (project_app/issues) |
| 3 | Scholar: find & add references | **PARTIAL** | Search works (47 results, local Crossref; `06-scholar_1.png`). **Save selected → HTTP 400** "unknown project: no such project in this library" for a new project (`06-scholar_2.png`); Library tab lists another project's papers while this project is selected (`06-scholar_3.png`). See F4. | scitex-scholar (leaf) + scitex-hub (scholar_app mount) |
| 4 | Data via scitex-dataset | **MISSING** | No Hub route/app; package not installed in the dev image (its mount source on compute-03 is an empty directory). | scitex-dataset / scitex-hub |
| 5 | Run the analysis (terminal / jobs / HPC) | **FAIL** | Console terminal: `WebSocket ✓ → Broker → SLURM → Apptainer ✗ — Terminal compute image is not configured on this service` (`05-apps_4.png`), reconnecting every 3 s. Dev env has `SCITEX_HUB_SLURM_CONTAINER_PATH` / `SCITEX_HUB_SLURM_USER_DATA_ROOT` still at the `/path/to/…` placeholders. scitex-hpc not installed; only the "Remote (HPC / Server)" project type exists. | deployment config (dev `.env`); scitex-hub (console_app) |
| 6a | Stats app | **PASS (UI)** | Loads with project selector, test catalogue, report export (`05-apps_3.png`). End-to-end analysis not run. | scitex-stats |
| 6b | FigRecipe app | **PARTIAL** | Loads (`05-apps_2.png`) but shows "No figures yet" although the project contains `figures/sample_plot.yaml`. `?project=<pk>` → 404 JSON (`04-tour_6.png`). | figrecipe / scitex-hub |
| 7 | Clew: verify, claims, graph | **FAIL** | "No DB" for every project, including the MNIST example (`04-tour_4.png`, `07-clew-lp_3.png`); "Add Examples" → HTTP 500 `scitex.clew requires additional dependencies` (`07-clew-lp_1.png`). See F3. | scitex-clew + scitex-python + scitex-hub (clew_app) |
| 8 | Writer: manuscript, claims via Clew | **PARTIAL** | Editor, section tree, compile and PDF preview work (`05-apps_1.png`). `/apps/writer/api/annotations` → HTTP 500 `StoreProvisionError: Store 'annotations' needs PostgreSQL DDL …` (store never provisioned on dev DB). Claims via Clew blocked by step 7. | scitex-writer + dev DB provisioning |
| 9 | Live Paper view | **PARTIAL** | Renders the MNIST example bundle with 3 REGISTERED claims (`07-clew-lp_4.png`). Dev runs **0.2.20**; the 0.5.0 in-paper evidence panels are not on dev (compute-03 `~/proj/scitex-live-paper` checkout is behind origin/develop). New projects have no bundle ("No paper selected", `04-tour_7.png`). | scitex-live-paper + dev deployment |
| 10 | Preprint / submission | **PARTIAL** | Agentic Journal v0.1.0a4 portal: Prepare checklist and submission records render (`04-tour_8.png`, `07-clew-lp_5.png`). Its intake gate requires a resolvable ORCID + clonable repo + ≥1 verified Clew run — unreachable today because of 1b and 7. Redesign in progress elsewhere. | scitex-agentic-journal |

Cross-cutting:

- **`?project=<numeric id>`** is not honoured: Scholar silently shows the last
  active project; Writer/FigRecipe answer `404 {"error": "Project not available"}`
  (`04-tour_3.png`, `04-tour_5.png`). `?project=<owner>/<slug>` works. Open PR
  #1133 (numeric pk alias) addresses this.
- The bottom app dock overlays page content on every app at 1440x900 (e.g. it
  hides the Clew quick-start command in `04-tour_4.png`).
- `/auth/signin/` still shows the sign-in form to an already-authenticated user.

## Findings (root causes)

**F1 — research template never applied.** `Project.objects.create()` fires the
Gitea post-save signal, which clones the new repo into the project path and
pushes the writer skeleton. Only afterwards does `handle_template_creation` →
`create_project_directory(use_template=True)` → `copy_from_example_template`
run, which returns `False` because the path exists and silently falls back to
`create_minimal_readme` ("This is an empty project directory"). Independently,
`copy_from_example_template` maps `research` to template id `minimal`, so even
without the clone the scitex-template `research` scaffold (writer + scholar +
MNIST pipeline, `templates/research`, v0.2.0) would not be used. Dev has
`scitex-template 0.7.1`.

**F2 — issue events crash (fixed here).** Every view-level
`IssueEvent.objects.create(...)` passed `actor=`; the model field is `user`.
Also `api_issue_reopen` called `issue.reopen()` without its required `user`,
and close/reopen views recorded a second event on top of the one
`Issue.close()/reopen()` already record. The view tests were skipped
placeholders, so nothing caught it.

**F3 — Clew unusable on Hub.** The dev image has `scitex 2.29.3` and
`scitex-clew 0.21.0`. `scitex/clew/__init__.py` imports `set_db` from
`scitex_clew`, which no longer exports it, so `import scitex.clew` fails and the
lazy loader reports "requires additional dependencies". Hub `clew_app` is
written against the legacy SQLite API (`stx.clew.set_db(<project>/scitex/clew.db)`)
while scitex-clew develop is **0.34.0** (Postgres stores, its own leaf GUI via
the `scitex.apps` entry point, and the live-paper evidence provider). The
compute-03 mount source `~/proj/scitex-clew` is an empty directory.

**F4 — Scholar cannot file into new projects.** The leaf's
`_checked_project_dir` requires `<library_root>/<project>/` to exist and fails
closed otherwise; nothing creates that directory when a Hub project is created.
Same code on scitex-scholar develop. Related open PR: #1174 (library root
resolution).

## Accounts and data created by this walk

- **Test user `accept-walker-1119`** (email `accept-walker-1119@example.com`,
  created through the normal sign-up + OTP flow before the walk switched to the
  owner's account; Gitea user auto-created). Safe to delete.
- Under the owner's dev account (authenticated with a server-minted dev
  session; password, email, ORCID link, permissions and 2FA untouched):
  - project `acceptance-20261119-research` (id 223, Minimal template) + Gitea repo
  - project `acceptance-20261119-full` (Full template) + Gitea repo
  - issue #1 in `acceptance-20261119-research`
  - one Django session row (expires after 2 days)

No existing project or data of the owner was modified.
