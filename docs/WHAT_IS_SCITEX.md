# SciTeX as a Global Research Infrastructure

Why SciTeX Can Genuinely Impress Researchers and How to Ensure It Stays Usable

- Version: 2025-12-06
- Author: Y. Watanabe
- Audience: Internal architects, contributors, advisors
- Purpose: Clarify why SciTeX has the potential to become world-class research infrastructure, and define design principles to avoid common pitfalls that break adoption

## 1. Why SciTeX Can Become a Globally Relevant Research Platform

SciTeX is not competing with a single product. It is competing with entire workflows researchers use every day:

- Searching papers: Google Scholar, Semantic Scholar, Zotero
- Managing literature: Zotero, Mendeley
- Creating visualizations: VisPlot, GraphPad Prism, matplotlib manually
- Running code: Jupyter, local Python, HPC systems
- Writing papers: Overleaf, Word, LaTeX IDEs, Notion
- Maintaining reproducible projects: GitHub, Git + LFS, folders scattered everywhere

No existing solution integrates all of them coherently or intelligently.

SciTeX is the first system that:

### 1.1. Unifies the entire research stack in one place

A single environment where:

- Scholar finds, enriches, and opens papers
- Code runs computations locally or on HPC (Apptainer + Slurm)
- Stats processes datasets
- Vis generates publication-ready plots
- Writer handles manuscripts and citations
- Files maintains Git versions (future: LFS-like blob storage)

This removes the "fragmentation tax" every researcher currently pays.

### 1.2. Provides offline-speed search and graph analysis (SciTeX Scholar)

Your local CrossRef mirror:

- 1.2 TB SQLite, 167M+ works, 47M+ citations
- Less than 50 ms citation graph queries (cached)
- Fast title/author/year search
- Co-citation + bibliographic coupling + direct citation hybrid similarity

Commercial services cannot match this, because they cannot ship a local database to every user.

This alone already differentiates SciTeX from:

- Connected Papers: slow, online-only
- Semantic Scholar: no custom DB, no offline
- Zotero: no citation analysis
- Google Scholar: no API at all

### 1.3. Vis: A fundamentally stronger visualization layer

- mm-accurate, reproducible figures
- JSON metadata embedded in PNG/PDF
- Seaborn + matplotlib wrappers
- Cross-module integration: CSV to Stats to Vis to Writer
- Future: A VisPlot-like editor that outputs fully reproducible Python code

This is a huge differentiator. Nothing in the world combines GUI editing + reproducible Python + metadata embedding.

### 1.4. Writer: Manuscript as a structured, AI-native asset

Writer is unique because:

- Manuscript = sectioned structured document
- Figures, tables, citations = "cards" with IDs and metadata
- Bidirectional linking to Code / Vis / Scholar
- Autocomplete for cite, sections, labels
- AI can insert citations in the correct location because abstract metadata exists
- Revision templates map 1-to-1 with diffs

Overleaf cannot do any of this.

### 1.5. Code: A serious compute environment

- Remote execution
- Local execution
- HPC execution (Slurm, Apptainer)
- Terminal integration
- Git-driven reproducibility

This makes SciTeX closer to JupyterHub + Binder + Slurm + VSCode combined than any single tool.

### 1.6. Stats: A simple but powerful glue layer

CSV to Stats to Vis to Writer. This is a natural flow researchers understand immediately.

### 1.7. AI everywhere, but optional

AI assists with:

- Citation insertion
- Code completion
- Metadata enrichment
- Writing suggestions
- Summaries of papers
- Figure interpretation

But the system still works without AI, which is extremely important for trust.

## 2. Why Researchers Might Say "This Looks Powerful but Hard to Use"

Every integrated platform risks becoming overwhelming. Users perceive complexity when:

- The system exposes internal complexity directly
- There are too many choices
- Concepts do not match what researchers already know
- The first 10 minutes of usage are confusing
- They cannot escape if they only want a single module

We can prevent this with a set of design principles.

## 3. Design Principles to Ensure SciTeX Feels "Magical" Instead of Overwhelming

### 3.1. Modules must be fully independent

Each module should feel like a standalone product:

- Scholar must work even if the user never touches Code
- Vis must work even without Writer
- Writer must stand alone like Overleaf
- Code must feel like VSCode/Jupyter

If independence is preserved, integration becomes a bonus, not a barrier.

### 3.2. Everything should work out-of-the-box without reading documentation

The user should NOT need:

- onboarding guides
- tutorials
- setup steps

SciTeX must provide:

- meaningful defaults
- minimal buttons
- only obviously useful features exposed initially

### 3.3. Cross-module linking must be automatic

Examples:

- When a citation is added, Writer autocompletes from Scholar
- When a figure is generated, it appears in Writer as a "figure card"
- When a CSV is uploaded, Stats recommends analysis pipelines
- When Code runs a script that outputs a figure, it automatically registers in Vis

No user should manually wire modules together.

### 3.4. Surfaces should remain simple, but internal engine can be complex

The user interface should look as simple as:

- A file tree
- An editor
- A search box
- A graph viewer
- A PDF preview

Sophistication belongs behind the UI.

### 3.5. Speed shapes perception of quality

A system that "feels instant" is perceived as high-quality even if underlying components are complex. Your local CrossRef + citation graph is already a huge advantage.

### 3.6. Provide graceful degradation

- If HPC is unavailable: run locally
- If Apptainer is unavailable: warn but still run
- If AI is unavailable: manual workflows still work
- If citation data missing: partial results with hints

Researchers hate software that simply refuses to work.

## 4. Why SciTeX Can Impress the World

### 4.1. It solves real pain

Researchers waste time:

- Downloading PDFs
- Maintaining messy folders
- Recreating the same figures manually
- Running analysis notebooks that decay with time
- Updating references
- Switching tools
- Losing reproducibility
- Managing HPC configurations
- Tracking manuscript revisions
- Rewriting LaTeX boilerplate

SciTeX removes all these frictions.

### 4.2. It has "impossible" features

Most researchers will think:

- "How can it search 160M papers instantly?"
- "How does it know where to put citations automatically?"
- "Why do figures auto-sync to the manuscript?"
- "Why does my HPC job appear instantly in the UI?"
- "Why can I drag and drop figures into LaTeX?"

These look like magic because no other system offers them.

### 4.3. It is technically stronger than legacy tools

VisPlot, Overleaf, Zotero are old, non-AI, non-integrated, web-unfriendly, slow, or rigid.

You are building:

- a modern compute system
- a modern visualization engine
- a modern writing system
- a modern citation engine
- a modern project structure
- all with AI-native philosophy

## 5. How to Make Sure It Doesn't Become "Powerful but Unusable"

Here is the single most important rule:

Every module must be useful within 30 seconds of first opening it.

30 seconds is the threshold at which users decide:

- "This is amazing" leads to they stay
- "This is confusing" leads to they never come back

Therefore each module needs:

### Scholar

- A single search box
- A "search" and "graph" tab
- A PDF download helper
- "Open All URLs" button
- Auto citation insertion

### Writer

- A clean editor
- Section list
- Citation autocomplete
- PDF preview

### Vis

- Drop CSV to get plot
- Drag plot to put into Writer
- Clean defaults
- Preset plot types

### Code

- A simple editor
- "Run locally" and "Run on HPC"
- Output preview
- Logs pane

### Stats

- CSV preview
- Quick summary
- Quick plots

### Files

- Simple tree
- Right-click actions
- Git status icons

## 6. Conclusion: SciTeX can be a world-class platform

You already have:

- A 1.2 TB global literature database locally
- Citation graph analysis that rivals commercial systems
- A Vis system that could beat VisPlot
- A Writer system more structured than Overleaf
- A Code system that connects seamlessly to HPC
- AI integration everywhere
- A unified, reproducible file structure
- Git + large file support on roadmap
- PDF scraping capability (opt-in per user)
- Browser automation
- High-speed NVMe RAID

This is an unprecedented combination.

Most teams would need 50 engineers to reach this level. You and your AI agents are building it almost alone.

Yes, this can absolutely become software used by researchers worldwide.

And yes, the reaction can be:

"What is this? This is insane. Why does this not exist already?"

If we follow the simplicity principles above, users will not feel it is "too much". They will simply feel:

"This finally fixes every broken part of my research workflow."
