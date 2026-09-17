# writer_app

Manuscript writing and collaboration system for document creation, collaborative editing, and multi-format export.

## Writer's Git surfaces — inventory for the consolidation (compass L411 / L407 / L655)

Measured 2026-09-17 on `develop`, because the card that asks for "consolidate Git
controls into the file/version area" needs to know how many surfaces exist and
which of them are reachable. Every path below was verified by grep/ls at that
commit; nothing here is inferred from the card's own text.

**FOUR writer_app-owned Git surfaces, plus one that is not ours:**

| # | surface | files | reachable? |
| - | ------- | ----- | ---------- |
| 1 | Right-pane **History** tab (commit form + timeline + diff viewer) | `templates/writer_app/index_partials/history_panel.html`, `static/writer_app/ts/modules/_git-history.ts` | **the only WORKING Git UI** — it is what `GitHistoryManager` binds (`gitCommitForm`, `gitCommitTimeline`, `gitDiffViewer`, `gitStatusBadge`, `gitBranchSelect`, …) and it loads only when that tab is opened |
| 2 | **Git history modal** (branch select + diff) | `templates/writer_app/index_partials/git_history_modal.html` | included from **two** templates (`writer_partial.html` AND `index.html`), so it can render twice; opens on demand |
| 3 | **Version-control dashboard** (separate page) | `templates/writer_app/version_control/index.html`, `static/writer_app/ts/version_control/index.ts`, view `writer_app/views/version_control/dashboard.py` (exported as `version_control_index`) | a route of its own, i.e. a third place a user meets Git |
| 4 | **Sidebar "Version History Timeline"** | `templates/writer_app/index_partials/sidebar.html` (`history-timeline-section`, `history-timeline-container`) | **DEAD CODE** — `grep -rn "index_partials/sidebar.html"` finds no `{% include %}` anywhere in this repo |
| 5 | the **left file tree** the card wants Git moved into | `apps/infra/workspace_app` + `static/shared/ts/components/workspace-files-tree/` | **not writer_app's** — `writer_app/templates/writer_app/index.html:88` says so in its own comment: *"Writer workspace — file tree provided by shared worktree pane in three-column layout"* |
| 6 | the shared file tree's **own** Git modals | `static/shared/ts/components/workspace-files-tree/_modals/GitHistoryModal.ts`, `_modals/GitDiffModal.ts` (each `document.createElement(...)`, exported as singletons) | **LIVE, and built by shared TS — it needs no writer_app markup at all** |

**Correction this inventory produced:** there are now **two independent Git-history
modals** in the system — writer_app's Bootstrap modal (surface 2) and the shared
tree's own (surface 6). The shared one lives in the exact place the card wants
Git to be, so the "move Git into the file area" part of L411 is **already half
true** in the shell, while writer_app keeps three surfaces of its own.

**What this means for L411 / L407 / L655, stated so the decision is small:**

1. Moving Git *into the left file area* is a **shared-shell** change (surface 5
   above). It needs the workspace-shell owner to host a Git workbench slot in
   `.ws-worktree-pane`, or to confirm writer_app may add one there.
2. Everything else is **writer_app-internal and can be consolidated without the
   shell**: surfaces 1–3 are three entry points to the same domain, and surface 4
   is already dead. Retiring one of them (which one is a product call) is a
   normal writer_app PR.
3. **L407** ("remove Branch information from the right details pane"): the details
   pane itself has no Branch block. The remaining branch display is surface 1/2
   (`gitBranchSelect`), so L407 is part of the same consolidation rather than a
   separate edit.
4. **L412 / L413** ("Commit" → "Save checkpoint" for researchers, raw labels in
   advanced): there is no researcher/advanced mode in this app to gate a label
   by. The rename cannot be implemented truthfully until that mode exists — and
   the scitex-writer leaf re-port has no Commit control at all (verified by grep:
   two unrelated `commit` hits, in annotation marks and a voice phrase).
