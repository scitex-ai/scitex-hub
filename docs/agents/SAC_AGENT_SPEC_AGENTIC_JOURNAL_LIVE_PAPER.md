<!-- ---
!-- Timestamp: 2026-06-12
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/agents/SAC_AGENT_SPEC_AGENTIC_JOURNAL_LIVE_PAPER.md
!-- --- -->

# SAC agent spec — proj-scitex-agentic-journal & proj-scitex-live-paper

Draft prepared by **proj-scitex-hub** for **lead** review. Actual agent startup is owned by **scitex-agent-container**.

## Why two new agents

Both `scitex-agentic-journal` and `scitex-live-paper` are now their own repos with their own roadmaps and their own release lifecycles. Carrying their work inside `proj-scitex-hub` would conflate three release surfaces (hub web platform, the journal pipeline, the live-paper renderer) and create cross-repo PR storms. Each gets a persistent agent that owns its repo's context across restarts.

## proj-scitex-agentic-journal

- **agent_id**: `proj-scitex-agentic-journal`
- **repo**: `ywatanabe1989/scitex-agentic-journal`
- **work dir**: `/home/ywatanabe/proj/scitex-agentic-journal` (rw)
- **venv**: same overlay pattern as other proj-* agents (`/uvwork/venv-agent/bin/python`)
- **parent**: `lead`
- **report channels**: `ProjSciTeXAgenticJournalBot` Telegram (new bot, request from operator) + `server:sac` as `proj-scitex-agentic-journal`
- **read visibility**: BROAD ro across `/home/ywatanabe/proj` (same as other proj-* agents); `gh` for repo-wide CI/PR status
- **constraints**: no mocks, no paid API (opus only), no Co-Authored-By trailer
- **first responsibility loop**:
  1. orient: read README + CHANGELOG + open issues
  2. M1 — implement submission gate 1 (Submission schema + structural checks: ORCID resolvable, code repo cloneable, `clew claim verify` >= 1 green claim)
  3. CLI `scitex-agentic-journal submit ./paper/` returns pass/fail + reasons (no mocks)
- **peers it talks to via a2a**:
  - `clew-agent` (claim model / DAG / verify owner — read-only contract)
  - `scitex-scholar` agent (novelty / literature triangulation, M2)
  - `proj-scitex-writer` agent (manuscript bundle ingestion)
  - `proj-scitex-hub` (reviewer dashboard mount surface, M5)
- **DO NOT**: define new claim types (owned by scitex-clew), implement its own DOI client (use Zenodo SDK / JaLC client as a thin wrapper)

## proj-scitex-live-paper

- **agent_id**: `proj-scitex-live-paper`
- **repo**: `ywatanabe1989/scitex-live-paper`
- **work dir**: `/home/ywatanabe/proj/scitex-live-paper` (rw)
- **venv**: same overlay pattern as other proj-* agents
- **parent**: `lead`
- **report channels**: `ProjSciTeXLivePaperBot` Telegram (new bot, request from operator) + `server:sac` as `proj-scitex-live-paper`
- **read visibility**: BROAD ro across `/home/ywatanabe/proj`; `gh` for repo-wide CI/PR status
- **constraints**: no mocks, no paid API (opus only), no Co-Authored-By trailer
- **first responsibility loop**:
  1. orient: read README + CHANGELOG + open issues
  2. M1 — implement read-only renderer (bundle dir -> static site: viewer PDF.js page + claims sidebar + DAG nav + per-claim page)
  3. CLI `scitex-live-paper render ./bundle/ --out ./site/` produces a working static site (no mocks)
- **peers it talks to via a2a**:
  - `clew-agent` (claim model / DAG read; verify call delegation, M2)
  - `proj-scitex-writer` (manuscript bundle layout, `\vclaim` macros)
  - `proj-scitex-hub` (mount as Django app at `/viewer-v2/`, M3)
  - `proj-scitex-agentic-journal` (receives accepted bundle + verification result, M4)
- **DO NOT**: implement claim verification logic (owned by scitex-clew), implement its own auth (use scitex-hub Auth)

## Shared rules (both agents)

- Use `/uvwork/venv-agent/bin/python`; `/opt` is read-only rootfs.
- Repo is at `/work` (== `/home/ywatanabe/proj/<repo>`, rw); everything else under `~/proj` is read-only.
- Branches always fork from `develop` and merge back to `develop`. Topic branches: `feat/<verb>-<object>` etc.
- All work in `.worktrees/<name>/` from `develop`; main checkout stays pinned to `develop`.
- File-size thresholds: PY 512 lines, TS/CSS 512, HTML 1024 — refactor proactively (CLAUDE.md rule from hub).
- Test rules: STX-TQ002/003/007 — AAA markers, >=3-token names, one assert per test.
- Errors with guidance, no silent fallbacks.
- a2a inbox: report progress/BLOCKED to `lead` on the cadence the lead sets per task.

## Bootstrap on first launch

For each agent the agent-container should:

1. Create the SAC agent record (agent_id, parent=lead, peers as above).
2. Provision the workdir at `/home/ywatanabe/proj/<repo>` from `git clone git@github.com:ywatanabe1989/<repo>` on the develop branch (both repos already have `feat/initial-skeleton` open — merge that to develop as first PR, then start the agent's loop on develop).
3. Wire the agent's overlay venv with the package installed editable (`uv pip install -e .`).
4. Hand the agent the standard startup protocol (read last 7 TG messages for context, send one short back-online ping, then orient: README + CHANGELOG + open issues + 3-line summary + nearest task + 1-line plan).
5. Report `DONE proj-<repo>-oriented` to lead on first successful orient.

## Open questions for lead / operator

1. **Telegram bot tokens** — operator needs to create `ProjSciTeXAgenticJournalBot` and `ProjSciTeXLivePaperBot` (or confirm reuse of an existing bot under different chat namespace).
2. **Resource budget** — both agents are mostly idle until M1 lands; can they share a single container with two named loops, or do they need separate containers? agent-container's call.
3. **First PR landing** — `feat/initial-skeleton` is open on both repos. Should lead/operator approve those merges before the agents start, or should the agents themselves open the PR and self-admin-merge once oriented?
4. **scitex-dev / scitex-ui pinning** — both pyproject.toml currently say `>=` ranges. The hub pattern is hard-pinning for prod; should new pre-alpha repos hard-pin too, or hold loose ranges until M2?

<!-- EOF -->
