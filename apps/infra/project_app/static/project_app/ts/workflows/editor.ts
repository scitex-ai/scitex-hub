// Workflow Editor JavaScript
// Template YAML definitions and template selection logic

(function () {
  "use strict";

  // type TemplateId = 'blank' | 'python-test' | 'latex-build' | 'code-lint' | 'docker-build';

  interface TemplateYamlMap {
    [key: string]: string;
  }

  interface TemplateNamesMap {
    [key: string]: string;
  }

  const templateYaml: TemplateYamlMap = {
    blank: `name: My Workflow
on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Run command
        run: echo "Hello, World!"
`,
    "python-test": `name: Python Tests
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ -v
`,
    "latex-build": `name: LaTeX Build
on:
  push:
    branches: [ main ]
    paths:
      - '**.tex'
      - 'scitex/writer/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Compile LaTeX
        run: |
          cd scitex/writer/00_shared
          pdflatex -synctex=1 main.tex
          bibtex main
          pdflatex -synctex=1 main.tex
          pdflatex -synctex=1 main.tex

      - name: Upload PDF
        uses: actions/upload-artifact@v3
        with:
          name: manuscript
          path: scitex/writer/00_shared/main.pdf
`,
    "code-lint": `name: Code Linting
on:
  push:
    branches: [ main, develop ]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install linting tools
        run: |
          pip install black flake8 mypy

      - name: Run black
        run: black --check .

      - name: Run flake8
        run: flake8 .

      - name: Run mypy
        run: mypy . --ignore-missing-imports
`,
    "docker-build": `name: Docker Build
on:
  push:
    branches: [ main ]
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build Docker image
        run: |
          docker build -t myapp:latest .

      - name: Test Docker image
        run: |
          docker run myapp:latest pytest
`,
  };

  function selectTemplate(templateId: string, event?: Event): void {
    console.log("Selecting template:", templateId);
    // Highlight selected template
    document.querySelectorAll(".template-item").forEach((item) => {
      item.classList.remove("selected");
    });

    if (event && event.target) {
      const target = event.target as HTMLElement;
      const templateItem = target.closest(".template-item");
      if (templateItem) {
        templateItem.classList.add("selected");
      }
    }

    // Set template input
    const templateInput = document.getElementById(
      "template-input",
    ) as HTMLInputElement;
    if (templateInput) {
      templateInput.value = templateId;
    }

    // Load template YAML
    const yamlEditor = document.getElementById(
      "yaml-editor",
    ) as HTMLTextAreaElement;
    if (yamlEditor && templateYaml[templateId]) {
      yamlEditor.value = templateYaml[templateId];
    }

    // Auto-fill workflow name if blank
    const nameInput = document.getElementById(
      "workflow-name",
    ) as HTMLInputElement;
    if (nameInput && !nameInput.value && templateId !== "blank") {
      const templateNames: TemplateNamesMap = {
        "python-test": "Python Tests",
        "latex-build": "LaTeX Build",
        "code-lint": "Code Linting",
        "docker-build": "Docker Build",
      };
      nameInput.value = templateNames[templateId] || "";
    }
  }

  // Expose function to global scope
  (window as any).selectTemplate = selectTemplate;
})();
