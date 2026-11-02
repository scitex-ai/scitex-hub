# Landing page structure

The anonymous landing page is assembled by `apps/infra/public_app/templates/public_app/landing.html`. Edit the source partials, not saved browser HTML. Its section navigator and visible section labels use these canonical links:

| Order | Heading | Link | Other supported hashes |
| --- | --- | --- | --- |
| 1 | Where Research Happens | `#overview` | `#home`, `#hero`, `#apps`, `#hub`, `#screenshots` |
| 2 | The Python toolkit in action | `#demo` | `#research-demo` (video disclosure) |
| 3 | Work from your phone, laptop, or HPC | `#workflow` | `#context`, `#devices` |
| 4 | Trace claims back to their sources | `#provenance` | `#clew` |
| 5 | Build apps your research needs | `#custom-apps` | `#sdk` |
| 6 | Your projects. Your infrastructure | `#deployment` | `#open`, `#byox` |
| 7 | Open source, throughout the stack | `#open-source` | `#github` |
| 8 | Pricing (expected from beta) | `#pricing` | |

The hero pairs its introduction with the actual app screenshot carousel. On phones, the carousel follows the introduction. The separate Apps directory has been removed. Its legacy hash links now target the Overview gallery. The dedicated Demo section shows the recorded Python/MCP backend research workflow. Asset provenance remains in `apps/infra/public_app/static/public_app/images/landing-v2/PROVENANCE.md`, including retained historical assets. The global Alpha notice is a one-line rectangular banner; it and the landing notice use the SDK/UI semantic `--status-warning-*` triplet. The demo player is expanded initially, with native controls and no autoplay or video preloading. Its caption identifies the recorded SciTeX v2.10 version; it is not presented as current web UI footage. Pricing data continues to come from the existing comparison provider rather than this document.

`landing_section_nav.html` provides native links; `landing/section-nav.css` reserves space below the global header. `landing/target-layout.css` styles linked section labels, legacy aliases and the text hero. Both stylesheets use the SDK `app_static` helper so source changes produce new asset query hashes.

Gallery selectors use `stx-content-tabs` / `stx-content-tabs__tab` and the SDK `content-tabs.css` underline primitive, with stable `aria-controls` panel IDs. Landing styles adjust wrapping only; they do not redefine the selected tab or focus ring.

The eleven screenshots are grouped by interface role: Platform (Hub, SDK), Infrastructure (Agent Container, Cards, Storage), Research (Scholar, Stats, FigRecipe, Writer), and Publication (Live Paper, Agentic Journal). These visible categories are not a package dependency graph. A single tablist maintains roving focus in the same order as the visible groups. Captures record their actual origin, observation time, privacy masks, sample context and hashes in a packaged manifest. A screenshot is evidence of the captured interface, not proof of every advertised feature or production availability. Preserve historical captures and their provenance when replacing the active gallery.

Validate source rendering in English and Japanese, native section links and aliases, desktop and phone layout, every gallery slide, keyboard and touch controls, delivered image hashes, and absence of horizontal overflow. The existing landing template, asset and carousel checks cover these contracts; current live browser receipts are retained separately from source tests.
