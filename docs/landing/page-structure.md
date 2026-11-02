# Landing page structure

The anonymous landing page is assembled by `apps/infra/public_app/templates/public_app/landing.html`. Edit the source partials, not saved browser HTML. Its section navigator and visible section labels use these canonical links:

| Order | Heading | Link | Other supported hashes |
| --- | --- | --- | --- |
| 1 | Open-source Ecosystem for Scientific Research | `#overview` | `#home`, `#hero`, `#apps`, `#hub`, `#screenshots` |
| 2 | Trace claims back to their sources | `#provenance` | `#clew` |
| 3 | AI Agent + SciTeX® | `#demo` | `#research-demo` (video player) |
| 4 | Open source, throughout the stack | `#open-source` | `#github` |
| 5 | Pricing (expected from beta) | `#pricing` | |

The hero pairs its introduction with the actual app screenshot carousel, with both desktop columns aligned at the top. On phones, the carousel follows the introduction. The separate Apps directory has been removed. Its legacy hash links now target the Overview gallery. The dedicated Demo section shows the recorded Python/MCP backend research workflow, with text on the left and the video on the right, top-aligned like Overview. Both sections stack on narrow viewports. Asset provenance remains in `apps/infra/public_app/static/public_app/images/landing-v2/PROVENANCE.md`, including retained historical assets. The global Alpha notice is a one-line rectangular banner; it and the landing notice use the SDK/UI semantic `--status-warning-*` triplet. The demo video is always visible, with native controls and no autoplay or video preloading. A short invitation appears in the left text column; there is no expandable heading or recorded-version caption. Pricing data continues to come from the existing comparison provider rather than this document.

`landing_section_nav.html` provides native links styled with SDK content tabs and `aria-current="location"`. The SDK `section-nav.js` controller tracks scrolling, hashes, history and header size without rewriting the URL or hiding sections; `landing/section-nav.css` reserves space below the global header. `landing/target-layout.css` styles linked section labels, legacy aliases and the text hero. Both stylesheets use the SDK `app_static` helper so source changes produce new asset query hashes.

Gallery selectors use `stx-content-tabs` / `stx-content-tabs__tab` and the SDK `content-tabs.css` underline primitive, with stable `aria-controls` panel IDs. Landing styles adjust wrapping only; they do not redefine the selected tab or focus ring.

The eleven screenshots are grouped by interface role: Platform (Hub, SDK), Infrastructure (Agent Container, Cards, Storage), Research (Scholar, Stats, FigRecipe, Writer), and Publication (Live Paper, Agentic Journal). These visible categories are not a package dependency graph. Two SDK underline-tab levels present these groups: categories first, then only the selected category's applications. App tabs display the captured screenshot's version badge, not a newly queried installed version. Stats has no visible badge, so its source-declared 1.0.0 is qualified in its title. FigRecipe retains its visible 0.44.0 label and discloses the recorded 0.44.1 source overlay in the tooltip. The existing capture manifest owns public presentation/version fields; a pure template tag projects them without importing or probing leaf packages. App-arrow/Home/End navigation stays within its group, category arrows change groups, and returning to a group restores its last selected app. Global previous/next, swipe and autoplay continue through all eleven slides and synchronize both tab rows. Captures record their actual origin, observation time, privacy masks, sample context and hashes in a packaged manifest. A screenshot is evidence of the captured interface, not proof of every advertised feature or production availability. Preserve historical captures and their provenance when replacing the active gallery.

Validate source rendering in English and Japanese, native section links and aliases, desktop and phone layout, every gallery slide, keyboard and touch controls, delivered image hashes, and absence of horizontal overflow. The existing landing template, asset and carousel checks cover these contracts; current live browser receipts are retained separately from source tests.

The separate Workflow, Custom Apps and Deployment sections were removed by the operator. Their former hash IDs remain zero-height aliases in Overview, so existing links still resolve without restoring removed content.

The pricing coupon field uses the translated placeholder “COUPON CODE”; actual coupon definitions and validation remain owned by the pricing provider.

The native section-navigation enhancement is pinned to scitex-sdk source `721c15fe18ccd1715c7e287832bd7bc556dd169a` under `static/vendor/scitex-sdk/721c15fe18cc/`, with original license, origin paths and exact artifact hashes. This is a provider build, not a host implementation fork or a changed installed SDK wheel. The pin supports `aria-current` underline styling and passive section tracking until a normal published SDK upgrade includes it.

Overview uses a three-item list to explain the ecosystem roles: scitex-clew as the verification foundation, deterministic SciTeX tools with native Clew support, and scitex-hub as the GUI/API layer. Provenance itself focuses on “Record Forward. Verify Backward.” and Clew’s claim-to-source tracing. This wording does not promise independent scientific truth or a globally minimal dependency set.

The hero omits the earlier “Literature, files, analysis…” introductory sentence; the ecosystem-role list carries the explanation instead.

The Clew section also top-aligns its text and diagram.

The screenshot gallery advances every six seconds while visible. Its counter includes a pause/resume control. Pointer hover, keyboard focus, hidden tabs, and an off-screen gallery pause rotation; reduced-motion preferences disable automatic rotation initially. Manual selection and swipe remain available, with SDK underline tabs unchanged.

Demo setup examples use `uv pip install 'scitex[all]'`, the umbrella stdio server (`scitex mcp start`), and `scitex-dev skills install` for the currently published umbrella dependency set (scitex2.30.8/dev0.28.0). Newer standalone Dev uses `scitex-dev dev skills install`; its older top-level alias is deprecated. The skills command collects installed providers into `~/.scitex/dev/skills/`; newer releases expose the same destination. MCP clients that do not inherit PATH need the environment’s absolute executable path. These commands were checked against CLI help and source; dependency resolution was checked with an isolated dry run, without installing into the live service.

Demo snippets declare `language-bash`/`language-json` and `data-language` for the existing shared highlighter and language labels. The skills examples include `--claude-symlink`, because collecting files in the central store does not itself register them with Claude Code. The optional link is `~/.claude/skills/scitex/` → the resolved shared destination; `$SCITEX_DIR` can change the default store. SAC/Hermes instead materializes audited installed-provider copies inside each isolated Hermes home and sets `skills.external_dirs` to the relative `scitex-skills` directory; host absolute symlinks are not required inside Apptainer.
