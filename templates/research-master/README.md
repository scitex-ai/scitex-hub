# SciTeX Research Template

> **Like GitHub, but for scientific research.** Version control your papers, data, and analysis - all in one place.

## 🚀 Quick Start

| What you want to do | Where to go |
|---------------------|-------------|
| **Write a paper** | `scitex/writer/` → Open in [Writer](/writer/) |
| **Manage references** | `scitex/scholar/` → Open in [Scholar](/scholar/) |
| **Run analysis** | `scripts/` → Open in [Console](/console/) |
| **Create figures** | `scitex/vis/` → Open in [Visualizer](/visualizer/) |

## 📁 Project Structure

```
your-project/
├── config/          # Settings (like .github/ but for research)
├── data/            # Your datasets (raw → processed)
├── docs/            # Documentation & notes
├── scripts/         # Analysis code (Python, R, etc.)
├── scitex/          # SciTeX-managed folders
│   ├── writer/      # Manuscripts (.tex files)
│   ├── scholar/     # References (.bib files)
│   └── vis/         # Figures (.pltz, .figz)
├── tests/           # Test your analysis code
├── Makefile         # Automation (like GitHub Actions)
└── README.md        # You are here
```

## 🔄 Typical Workflow

1. **Add data** → Upload to `data/raw/`
2. **Write scripts** → Create in `scripts/` using Console
3. **Run analysis** → Submit jobs via SLURM or run directly
4. **Generate figures** → Auto-saved to `scitex/vis/`
5. **Write paper** → Edit in Writer, cite from Scholar
6. **Compile PDF** → One-click in Writer
7. **Commit & push** → Version everything like GitHub

## ⌨️ Makefile Commands

```bash
make help           # Show all available commands
make run            # Run main analysis
make test           # Run test suite
make figures        # Generate all figures
make compile        # Compile manuscript to PDF
make clean          # Clean temporary files
```

## 📖 Learn More

- [SciTeX Documentation](https://scitex.ai/docs/)
- [GitHub Repository](https://github.com/ywatanabe1989/scitex)
- [Self-hosting Guide](https://github.com/ywatanabe1989/scitex#self-hosting)

---

*This project is managed by [SciTeX](https://scitex.ai) - Where Research Happens.*
