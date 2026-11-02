# Landing page structure

The anonymous landing page is assembled by `apps/infra/public_app/templates/public_app/landing.html`. Edit the source partials, not saved browser HTML. Its section navigator and visible section labels use these canonical links:

| Order | Heading | Link | Other supported hashes |
| --- | --- | --- | --- |
| 1 | Where Research Happens | `#overview` | `#home`, `#hero` |
| 2 | One project, connected research tools | `#apps` | `#hub`, `#screenshots` |
| 3 | Work from your phone, laptop, or HPC | `#workflow` | `#context`, `#devices` |
| 4 | Trace claims back to their sources | `#provenance` | `#clew` |
| 5 | Build apps your research needs | `#custom-apps` | `#sdk` |
| 6 | Your projects. Your infrastructure | `#deployment` | `#open`, `#byox` |
| 7 | Open source, throughout the stack | `#open-source` | `#github` |
| 8 | Pricing (expected from beta) | `#pricing` | |

The hero is text only. Asset provenance remains in `apps/infra/public_app/static/public_app/images/landing-v2/PROVENANCE.md`, including retained historical assets. The approved Cloud alpha notice stays visible. The optional full research demo belongs inside Apps, not a ninth top-level section. Pricing data continues to come from the existing comparison provider rather than this document.

`landing_section_nav.html` provides native links; `landing/section-nav.css` reserves space below the global header. `landing/target-layout.css` styles linked section labels, legacy aliases and the text hero. Both stylesheets use the SDK `app_static` helper so source changes produce new asset query hashes.

The carousel must represent Agent Container, Cards, Storage, Scholar, Stats, FigRecipe, Writer, Live Paper, and Agentic Journal. Captures record their actual origin, observation time, privacy masks, sample context and hashes in a packaged manifest. A screenshot is evidence of the captured interface, not proof of every advertised feature or production availability. Preserve historical captures and their provenance when replacing the active gallery.

Validate source rendering in English and Japanese, native section links and aliases, desktop and phone layout, every gallery slide, keyboard and touch controls, delivered image hashes, and absence of horizontal overflow. The existing landing template, asset and carousel checks cover these contracts; current live browser receipts are retained separately from source tests.
