# Repository Template Cleanup Plan

**Goal**: Create a clean, educational boilerplate from scitex_template_research

## Files Analysis

### ✅ KEEP AS-IS (Educational Content)
- `paper/01_manuscript/contents/abstract.tex` - Perfect structure guide with 7-part format
- `paper/01_manuscript/contents/introduction.tex` - Excellent paragraph-by-paragraph guide
- Structure and guidelines in all `.tex` files

### 🔨 CLEAN (Remove Neurovista-Specific Content)

#### 1. Tables
**Location**: `paper/01_manuscript/contents/tables/caption_and_media/`
**Issues**:
- Symlinks to actual neurovista data files
- Neurovista-specific table captions

**Action**:
```bash
# Remove neurovista tables
rm paper/01_manuscript/contents/tables/caption_and_media/*.csv
rm paper/01_manuscript/contents/tables/caption_and_media/*.tex

# Create example table
cat > paper/01_manuscript/contents/tables/caption_and_media/example_table.tex << 'EOF'
%% Table caption template
%% Table ID: 01
%%
%% Guidelines:
%% - Keep captions concise but informative
%% - Define all abbreviations used in the table
%% - Reference the table in text as Table~\ref{tab:example}

\begin{table}[htbp]
\centering
\caption{Example table showing data organization}
\label{tab:example}
\begin{tabular}{lcc}
\hline
Category & Value & Percentage (\%) \\
\hline
Group A & 123 & 45.6 \\
Group B & 98 & 36.3 \\
Group C & 49 & 18.1 \\
\hline
Total & 270 & 100.0 \\
\hline
\end{tabular}
\end{table}

% For CSV/Excel tables, place files here and they will be auto-converted
% Supported formats: .csv, .xlsx
EOF
```

#### 2. Figures
**Location**: `paper/01_manuscript/contents/figures/caption_and_media/`
**Issues**:
- Symlinks to neurovista analysis figures
- Project-specific image files

**Action**:
```bash
# Remove neurovista figures
rm -rf paper/01_manuscript/contents/figures/caption_and_media/*.jpg
rm -rf paper/01_manuscript/contents/figures/caption_and_media/*.png
rm paper/01_manuscript/contents/figures/caption_and_media/*.tex

# Create example figure template
cat > paper/01_manuscript/contents/figures/caption_and_media/example_figure.tex << 'EOF'
%% Figure caption template
%% Figure ID: 01
%%
%% Guidelines:
%% - Describe what the figure shows
%% - Explain key patterns or results
%% - Define symbols, colors, error bars
%% - Keep technical details in caption, interpretation in main text

% Place your figure files here (.jpg, .png, .pdf, .tif supported)
% Mermaid diagrams (.mmd) will be auto-converted

\begin{figure}[htbp]
\centering
\includegraphics[width=0.8\textwidth]{figures/caption_and_media/example_figure.png}
\caption{Example figure caption. (A) First panel description. (B) Second panel
description. Error bars represent standard deviation. n=30 samples per group.}
\label{fig:example}
\end{figure}
EOF

# Create a simple example image (placeholder)
# Users will replace with their actual figures
```

#### 3. Bibliography
**Location**: `paper/shared/bib_files/`
**Issues**:
- Neurovista-specific .bib files
- Hundreds of epilepsy-related citations

**Action**:
```bash
# Keep only bibliography.bib with minimal examples
# Remove project-specific bib files
rm paper/shared/bib_files/coauthors.bib
rm paper/shared/bib_files/epilepsy*.bib
rm paper/shared/bib_files/neurovista.bib
rm paper/shared/bib_files/pac*.bib
rm paper/shared/bib_files/_pac*.bib

# Clean bibliography.bib - keep structure with 2-3 example entries
cat > paper/shared/bib_files/bibliography.bib << 'EOF'
%% Bibliography Template
%% Place your BibTeX entries here
%%
%% Tips:
%% - Use consistent citation keys (FirstAuthor2023keyword)
%% - Include DOI when available
%% - For journals, include impact factor in notes field
%% - Export from: Google Scholar, PubMed, arXiv, etc.

@article{example2023nature,
  title={Example research paper title},
  author={Smith, John and Doe, Jane},
  journal={Nature},
  volume={123},
  pages={456--789},
  year={2023},
  doi={10.1038/s41586-023-12345-6},
  note={Impact Factor: 42.8}
}

@article{reference2022science,
  title={Another example reference},
  author={Johnson, A. and Williams, B. and Brown, C.},
  journal={Science},
  volume={380},
  number={6644},
  pages={123--126},
  year={2022},
  doi={10.1126/science.abc1234}
}

@book{textbook2021,
  title={Foundational Textbook in Your Field},
  author={Expert, Field},
  publisher={Academic Press},
  year={2021},
  edition={3rd},
  isbn={978-0-12-345678-9}
}
EOF
```

#### 4. Data Files
**Location**: `data/mnist/` and other directories
**Issues**:
- Example uses MNIST dataset (good example!)
- But has actual downloaded data files

**Action**:
- **Keep** the MNIST example structure (it's educational!)
- Remove downloaded data files
- Add `.gitkeep` and README explaining where to get data

#### 5. Scripts
**Location**: `scripts/mnist/`
**Issues**:
- MNIST-specific scripts

**Action**:
- **Keep** as minimal working example!
- It shows users how to structure scripts
- Just clean up any large output files

### 📝 CREATE (Missing Educational Content)

#### 1. methods.tex Example
Add template for:
- Experimental design
- Data collection
- Statistical analysis
- Common methodological sections

#### 2. results.tex Example
Add template for:
- How to present findings
- Figure/table referencing
- Statistical reporting

#### 3. discussion.tex Example
Add template for:
- Interpreting results
- Comparing with literature
- Discussing limitations
- Future directions

## Cleaning Script

```bash
#!/bin/bash
# clean_template.sh - Remove neurovista-specific content

TEMPLATE_DIR="~/proj/scitex-cloud/externals/scitex_template_research"

# 1. Clean tables
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/tables/caption_and_media/*.csv
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/tables/caption_and_media/*seizure*.tex
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/tables/caption_and_media/*classification*.tex
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/tables/caption_and_media/*prediction*.tex

# 2. Clean figures
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/figures/caption_and_media/*.jpg
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/figures/caption_and_media/*.png
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/figures/caption_and_media/*demographic*.tex
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/figures/caption_and_media/*pac*.tex
rm -f $TEMPLATE_DIR/paper/01_manuscript/contents/figures/caption_and_media/*classification*.tex

# 3. Clean bibliography
cd $TEMPLATE_DIR/paper/shared/bib_files/
# Keep only bibliography.bib, remove rest
find . -name "*.bib" ! -name "bibliography.bib" -delete

# 4. Clean data files (keep structure, remove actual data)
rm -rf $TEMPLATE_DIR/data/mnist/processed/*
echo "Place your downloaded MNIST data here" > $TEMPLATE_DIR/data/mnist/.gitkeep

# 5. Create archive
cd ~/proj/scitex-cloud/docs/
tar -czf scitex_repository_template_clean.tar.gz \
  --exclude='.git' \
  --exclude='*.log' \
  --exclude='*.aux' \
  --exclude='*.pdf' \
  --exclude='__pycache__' \
  -C ~/proj/scitex-cloud/externals scitex_template_research/

echo "✅ Clean template created: scitex_repository_template_clean.tar.gz"
```

## What Makes a Good Template Section

### Structure
```latex
%% -*- coding: utf-8 -*-
%% [Section Name] template
%% Typical length: [word count guidance]

\section{[Section Name]}

%% ============================================================
%% [SECTION NAME] STRUCTURE GUIDE:
%% ============================================================
%% Paragraph 1: [Purpose]
%%   - [What to include]
%%   - [Best practices]
%%
%% Paragraph 2: [Purpose]
%%   - [What to include]
%% ============================================================

% PARAGRAPH 1: [Topic]
% Template:
% [Sentence template with [placeholders]]

[Instructional text in brackets explaining what users should write here.]

\label{sec:[section-name]}
```

### Key Elements
1. ✅ **Structure guide** - Clear paragraph organization
2. ✅ **Writing guidelines** - Tense, style, best practices
3. ✅ **Templates** - Example sentences with [placeholders]
4. ✅ **Instructions** - Bracketed text telling users what to do
5. ❌ **NO actual research content** - Only examples

## Priority

**High Priority** (Remove actual content):
1. Tables - neurovista-specific data
2. Figures - project-specific images
3. Bibliography - epilepsy papers
4. Data symlinks - remove broken links

**Medium Priority** (Enhance examples):
5. Methods - add more templates
6. Results - add reporting examples
7. Discussion - add interpretation guides

**Low Priority** (Already good):
8. Abstract - perfect!
9. Introduction - perfect!
10. README files - mostly good

---

**Next Step**: Run cleaning script to create `scitex_repository_template_clean.tar.gz`
