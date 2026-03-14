<!-- ---
!-- Timestamp: 2026-03-15 01:57:12
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/README.md
!-- --- -->

<!-- ---
!-- Timestamp: 2026-03-15
!-- File: /home/ywatanabe/proj/scitex-cloud/README.md
!-- --- -->

# SciTeX Cloud (<code>scitex-cloud</code>)

<p align="center">
  <a href="https://scitex.ai">
    <img src="static/shared/images/scitex_logos/logo-files/png/scitex-logo-blue-cropped.png" alt="SciTeX Cloud" width="400">
  </a>
</p>

<p align="center"><b>GitHub for research — verifiable, AI-native, self-hosted infrastructure for scientists</b></p>

<p align="center"><sub>For researchers and lab teams who want a unified, open-source platform<br>to manage the full research lifecycle — from literature to manuscript — under their own control.<br><a href="https://scitex.ai">scitex.ai</a> is a live instance of this project.</sub></p>

<p align="center">
  <a href="https://pypi.org/project/scitex-cloud/"><img src="https://badge.fury.io/py/scitex-cloud.svg" alt="PyPI version"></a>
  <a href="https://scitex-cloud.readthedocs.io/"><img src="https://readthedocs.org/projects/scitex-cloud/badge/?version=latest" alt="Documentation"></a>
  <a href="https://github.com/ywatanabe1989/scitex-cloud/actions/workflows/tests.yml"><img src="https://github.com/ywatanabe1989/scitex-cloud/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/ywatanabe1989/scitex-cloud/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
</p>

<p align="center">
  <a href="https://scitex-cloud.readthedocs.io/">Full Documentation</a> · <code>pip install scitex-cloud</code>
</p>

---

## Problem and Solution

<table>
<tr>
  <th align="center">#</th>
  <th>Problem</th>
  <th>Solution</th>
</tr>
<tr valign="top">
  <td align="center">1</td>
  <td><h4>Fragmented tools</h4>Literature, writing, analysis, and visualization require separate, often proprietary applications, forcing constant context-switching and making it difficult for AI agents to build sufficient context across the research workflow.</td>
  <td><h4>Unified platform</h4>Scholar, Writer, FigRecipe, Console, Hub, and Clew in a single Django web application, deployable anywhere with Docker. All apps share the same project filesystem and integrate through the <code>scitex</code> Python package.</td>
</tr>
<tr valign="top">
  <td align="center">2</td>
  <td><h4>No custom tooling</h4>Every research group needs domain-specific tools (e.g., clinical trial dashboards, spike-sorting interfaces, compound screening pipelines), yet building and sharing them requires deep computational knowledge and creating components from scratch.</td>
  <td><h4>App Maker and Store</h4>Researchers create, publish, and install custom research tools on top of shared components — user/group permissions, AI infrastructure, containerized computation, and file operations are handled by the platform.</td>
</tr>
<tr valign="top">
  <td align="center">3</td>
  <td><h4>AI tools not research-aware</h4>Existing tools often lack AI assistant capabilities and domain-specific skills for scientific work, unable to operate across the full research lifecycle (literature review, analysis, writing, verification).</td>
  <td><h4>Built-in AI co-pilot</h4>Platform-aware context, skills, and tools such as MCP (Model Context Protocol) and CLI span the full research lifecycle, providing an AI assistant that understands the entire project from natural language.</td>
</tr>
<tr valign="top">
  <td align="center">4</td>
  <td><h4>Review crisis</h4>The growing volume and heterogeneity of published papers overwhelms a limited, volunteer-based peer review process that cannot scale.</td>
  <td><h4>Open review via Issues and PRs</h4>GitHub-style issue tracking and pull requests bring transparent, structured, and scalable peer review to research projects — anyone can inspect, comment, and propose changes.</td>
</tr>
<tr valign="top">
  <td align="center">5</td>
  <td><h4>Broken provenance</h4>Papers, code, and execution environments are rarely tied together, making it difficult for reviewers to verify claims and for other researchers to replicate results — slowing cumulative scientific progress.</td>
  <td><h4>Verifiable provenance</h4>Clew links papers, code, data, and execution environments into a hash-verified DAG (Directed Acyclic Graph) with visualization that serves as a compressed view of the research workflow and logic — reducing the decision points reviewers must check.</td>
</tr>
<tr valign="top">
  <td align="center">6</td>
  <td><h4>Lost knowledge on handoff</h4>When researchers graduate or leave a project, successors inherit scattered files with little context, making it difficult to understand where to pick up and continue the work.</td>
  <td><h4>Seamless project handoff</h4>The full project state — code, data, provenance graph, manuscript drafts, and execution environment — lives in one place, so successors can understand and continue work immediately.</td>
</tr>
<tr valign="top">
  <td align="center">7</td>
  <td><h4>No research community platform</h4>No GitHub-like infrastructure exists for research-project-centric, fully traceable, parallel-working collaboration.</td>
  <td><h4>GitHub-style project hub</h4>Repository hosting and ticket-based development with co-authors and the community enable efficient research advancement and collaboration.</td>
</tr>
<tr valign="top">
  <td align="center">8</td>
  <td><h4>No control</h4>Researchers have no ownership over their infrastructure: vendor lock-in, opaque algorithms, unilateral pricing changes, and data policies they cannot influence.</td>
  <td><h4>Self-hosted, open-source, runnable from anywhere</h4>Deploy on your laptop, lab server, or cloud. AGPL-3.0 licensed — inspect every line, customize freely, no vendor lock-in, no data surrender.</td>
</tr>
</table>

<p align="center"><sub><b>Table 1.</b> Eight infrastructure challenges in scientific research and how SciTeX Cloud addresses each. These gaps fuel the reproducibility crisis, limit what AI can do for research, and leave knowledge stranded when people move on.</sub></p>

SciTeX Cloud is an AI-native infrastructure so that researchers can focus on science, not on tooling.

## Screenshots

<p align="center"><b>Writer</b><br><img src="docs/images/screenshot-writer.png" alt="Writer" width="100%"></p>

<p align="center"><b>Scholar</b><br><img src="docs/images/screenshot-scholar.png" alt="Scholar" width="100%"></p>

<p align="center"><b>Apps</b><br><img src="docs/images/screenshot-apps.png" alt="Apps" width="100%"></p>

<p align="center"><sub><b>Figure 1.</b> Core application modules. Writer provides a LaTeX manuscript environment with live compilation. Scholar offers literature discovery, BibTeX enrichment, and PDF management. The Apps panel shows the project-centric hub linking all modules.</sub></p>

## Installation

```bash
pip install scitex-cloud              # CLI only
pip install scitex-cloud[mcp]         # CLI + MCP server
pip install scitex-cloud[all]         # Everything
```

## Quick Start

```bash
git clone https://github.com/ywatanabe1989/scitex-cloud.git
cd scitex-cloud
make start                    # Start development environment

# Access at: http://localhost:8000
# Gitea: http://localhost:3000
# Test user: test-user / Password123!
```

## Three Interfaces

<details>
<summary><strong>Python API</strong></summary>

<br>

```python
import scitex_cloud

# Version and health
scitex_cloud.__version__        # "0.15.0"
scitex_cloud.get_version()      # Version string
scitex_cloud.health_check()     # Service health status
```

> **[Full API reference](https://scitex-cloud.readthedocs.io/)**

</details>

<details>
<summary><strong>CLI Commands</strong></summary>

<br>

```bash
scitex-cloud --help                    # Help
scitex-cloud --help-recursive          # All commands recursively
scitex-cloud --version                 # Version

# Git hosting (Gitea)
scitex-cloud gitea list                # List repositories
scitex-cloud gitea clone user/repo     # Clone repository
scitex-cloud gitea push                # Push changes
scitex-cloud gitea pr create           # Create pull request
scitex-cloud gitea issue create        # Create issue

# Docker management
scitex-cloud docker status             # Container status
scitex-cloud docker logs               # View logs

# MCP server
scitex-cloud mcp start                 # Start MCP server
scitex-cloud mcp list-tools            # List available tools
scitex-cloud mcp doctor                # Diagnose setup
scitex-cloud mcp installation          # Client config instructions

# Utilities
scitex-cloud status                    # Deployment status
scitex-cloud completion                # Shell completion setup
scitex-cloud list-python-apis          # List all Python APIs
```

> **[Full CLI reference](https://scitex-cloud.readthedocs.io/)**

</details>

<details>
<summary><strong>MCP Server — for AI Agents</strong></summary>

<br>

AI agents can interact with the SciTeX Cloud platform autonomously via MCP (Model Context Protocol) tools.

| Category | Tools | Description |
|----------|-------|-------------|
| cloud | 14 | Git operations (clone, push, pull, PR, issues) |
| api | 9 | Scholar search, CrossRef, BibTeX enrichment |

<sub><b>Table 2.</b> MCP tool categories. All tools accept JSON parameters and return JSON results. Use <code>scitex-cloud mcp list-tools</code> for the full list.</sub>

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "scitex-cloud": {
      "command": "scitex-cloud",
      "args": ["mcp", "start"]
    }
  }
}
```

> **[Full MCP specification](https://scitex-cloud.readthedocs.io/)**

</details>

## Web Platform

<details>
<summary><strong>Deployment</strong></summary>

<br>

```bash
make start                    # Development (default)
make ENV=prod start           # Production
make ENV=prod status          # Health check
make ENV=prod db-backup       # Backup database
make help                     # All available commands
```

</details>

<details>
<summary><strong>Configuration</strong></summary>

<br>

`.env` files in `deployment/docker/envs/` (gitignored):

```bash
.env.dev        # Development
.env.prod       # Production
.env.staging    # Staging
.env.example    # Template (tracked)
```

Key variables:
```bash
SCITEX_CLOUD_DJANGO_SECRET_KEY=your-secret-key
SCITEX_CLOUD_POSTGRES_PASSWORD=strong-password
SCITEX_CLOUD_GITEA_TOKEN=your-token
```

</details>

<details>
<summary><strong>Project Structure</strong></summary>

<br>

```
scitex-cloud/
├── apps/                    # Django applications
│   ├── scholar_app/        # Literature discovery
│   ├── writer_app/         # Scientific writing
│   ├── console_app/        # Terminal & code execution
│   ├── figrecipe_app/      # Data visualization
│   ├── hub_app/            # Project hub & file browser
│   ├── project_app/        # Project management
│   ├── clew_app/           # Verification pipeline
│   └── public_app/         # Landing page & tools
│
├── deployment/docker/
│   ├── docker_dev/         # Development compose
│   ├── docker_prod/        # Production compose
│   └── envs/               # .env files (gitignored)
│
├── config/                  # Django settings
├── static/                  # Shared frontend assets
├── src/scitex_cloud/        # pip package (CLI + MCP)
├── tests/                   # Test suite
└── Makefile                 # Thin dispatcher
```

</details>

## Part of SciTeX

SciTeX Cloud is part of [**SciTeX**](https://scitex.ai). When modules work together, each output feeds naturally into the next:

| From | Produces | To | Outcome |
|------|----------|----|---------|
| **Scholar** | Citations as cards | **Writer** | Convenient, evidence-based referencing |
| **SciTeX-followed Analysis** | Artifacts | **Writer** | AI writes a manuscript based on actual results |
| **FigRecipe** | Style-editable, composable figures | **Writer** | Publication-ready figures in context |
| **Clew** | Verification and DAG visualization | **Writer** | Proven reproducibility for every claim |

The SciTeX system follows the Four Freedoms for Research below, inspired by [the Free Software Definition](https://www.gnu.org/philosophy/free-sw.en.html):

>Four Freedoms for Research
>
>0. The freedom to **run** your research anywhere — your machine, your terms.
>1. The freedom to **study** how every step works — from raw data to final manuscript.
>2. The freedom to **redistribute** your workflows, not just your papers.
>3. The freedom to **modify** any module and share improvements with the community.
>
>AGPL-3.0 — because we believe research infrastructure deserves the same freedoms as the software it runs on.

## Status

SciTeX Cloud is in **alpha**. Core functionality is working and under active development. Data formats may change between releases — back up important work.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<p align="center">
  <a href="https://scitex.ai" target="_blank"><img src="static/shared/images/scitex_logos/scitex-icons/scitex-icon-navy-inverted.png" alt="SciTeX" width="40"/></a>
</p>

<!-- EOF -->
