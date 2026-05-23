<!-- ---
!-- Timestamp: 2025-10-21 20:00:18
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/static/css/PROGRAMMATIC_DESIGN_SYSTEM.md
!-- --- -->

# Programmatic Design System Documentation

## 1. Storybook (Most Popular)

**What it is:** Component library documentation tool with live previews

**How it works:**

```javascript
// Button.stories.js
import { Button } from './Button';

export default {
  title: 'Components/Button',
  component: Button,
};

export const Primary = {
  args: {
    variant: 'primary',
    label: 'Click me',
  },
};

export const Secondary = {
  args: {
    variant: 'secondary',
    label: 'Secondary',
  },
};
```

**Pros:**

- Live component previews
- Auto-generates from components
- Interactive documentation
- Great for React/Vue/Angular

**Cons:**

- Requires frontend framework
- Build step needed
- Not ideal for server-rendered Django apps

**Best for:** Modern frontend frameworks

---

## 2. Pattern Lab

**What it is:** Pattern-driven documentation focused on atomic design

**Structure:**

```
patterns/
├── 00-atoms/
│   ├── buttons/
│   │   ├── button.html
│   │   ├── button.css
│   │   └── button.md
│   └── forms/
├── 01-molecules/
└── 02-organisms/
```

**Pros:**

- Atomic design methodology
- Pattern reusability
- Framework-agnostic
- Static output

**Cons:**

- Requires Pattern Lab setup
- Node-based build process

**Best for:** Design-first teams with atomic design philosophy

---

## 3. Fractal (Good for Django)

**What it is:** Standalone component documentation tool

**Setup:**

```bash
npm install @frctl/fractal
```

**Component file structure:**

```
components/
├── button/
│   ├── button.html
│   ├── button.css
│   ├── button.config.js
│   └── button.md
```

**Component config:**

```javascript
// button.config.js
module.exports = {
  title: 'Button',
  label: 'Button',
  status: 'ready',
  context: {
    variants: [
      { label: 'Primary', modifier: 'btn-primary' },
      { label: 'Secondary', modifier: 'btn-secondary' },
    ]
  }
};
```

**Pros:**

- Static site generation
- Works with any templating language
- Django-friendly
- CLI-based

**Cons:**

- Less interactive than Storybook
- Smaller community

**Best for:** Django apps with static components

---

## 4. Living Style Guides (LSG)

**What it is:** Python library for Django-based documentation

```bash
pip install django-lsg
```

**Usage:**

```python
# settings.py
LSG = {
    'COMPONENTS': 'path/to/components/',
    'OUTPUT': 'path/to/docs/',
}
```

**Pros:**

- Pure Python/Django
- No build process
- Integrated with Django
- Simple configuration

**Cons:**

- Smaller community
- Limited features

**Best for:** Pure Django projects

---

## 5. Custom Django App Approach

**Most control, built specifically for your needs**

### Structure:

```
design_system/
├── apps.py
├── views.py
├── templates/
│   └── design_system/
│       ├── index.html
│       ├── component.html
│       └── components/
│           ├── button.html
│           ├── card.html
│           └── form.html
├── static/
│   ├── css/components/
│   │   ├── button.css
│   │   └── card.css
│   └── js/
│       └── component-previewer.js
├── models.py (optional)
└── fixtures/
    └── components.json
```

### Component Definition (JSON):

```json
{
  "components": [
    {
      "id": "button",
      "name": "Button",
      "description": "Interactive button component",
      "css_file": "/static/css/components/button.css",
      "variants": [
        {
          "name": "Primary",
          "class": "btn btn-primary",
          "html": "<button class=\"btn btn-primary\">Click me</button>"
        },
        {
          "name": "Secondary",
          "class": "btn btn-secondary",
          "html": "<button class=\"btn btn-secondary\">Click me</button>"
        }
      ],
      "states": [
        { "name": "default", "html": "..." },
        { "name": "hover", "html": "..." },
        { "name": "disabled", "html": "..." }
      ],
      "docs": "Documentation in markdown"
    }
  ]
}
```

### Django View:

```python
# views.py
from django.shortcuts import render
from django.templatetags.static import static
import json
import os

def design_system(request):
    with open('design_system/fixtures/components.json') as f:
        components = json.load(f)

    return render(request, 'design_system/index.html', {
        'components': components['components']
    })

def component_detail(request, component_id):
    with open('design_system/fixtures/components.json') as f:
        components = json.load(f)

    component = next(c for c in components['components'] if c['id'] == component_id)

    return render(request, 'design_system/component.html', {
        'component': component
    })
```

### Template (auto-generates documentation):

```html
<!-- templates/design_system/index.html -->
{% extends "base.html" %}

{% block content %}
<div class="design-system">
  {% for component in components %}
  <section class="design-section" id="{{ component.id }}">
    <h2>{{ component.name }}</h2>
    <p>{{ component.description }}</p>

    <!-- Variants -->
    <div class="variants">
      {% for variant in component.variants %}
      <div class="variant">
        <h4>{{ variant.name }}</h4>
        <div class="preview">
          {{ variant.html|safe }}
        </div>
        <pre><code>{{ variant.html }}</code></pre>
      </div>
      {% endfor %}
    </div>

    <!-- States -->
    {% if component.states %}
    <div class="states">
      <h3>States</h3>
      {% for state in component.states %}
      <div class="state">
        <h4>{{ state.name }}</h4>
        <div class="preview">
          {{ state.html|safe }}
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <!-- Documentation -->
    {% if component.docs %}
    <div class="docs">
      {{ component.docs|markdown }}
    </div>
    {% endif %}
  </section>
  {% endfor %}
</div>
{% endblock %}
```

### Generate from CSS:

```python
# management/commands/generate_design_docs.py
import json
import re
import os

class Command(BaseCommand):
    def handle(self, *args, **options):
        components = []

        # Parse CSS files for component documentation
        css_dir = 'static/css/components/'
        for filename in os.listdir(css_dir):
            if filename.endswith('.css'):
                component_name = filename.replace('.css', '')

                with open(f'{css_dir}{filename}') as f:
                    content = f.read()

                    # Extract component info from CSS comments
                    match = re.search(r'/\*\s*(.*?)\*/', content, re.DOTALL)
                    if match:
                        components.append({
                            'id': component_name,
                            'name': component_name.title(),
                            'description': match.group(1).strip(),
                            'css_file': f'/static/css/components/{filename}',
                            'variants': self.extract_variants(content),
                        })

        with open('design_system/fixtures/components.json', 'w') as f:
            json.dump({'components': components}, f, indent=2)

        self.stdout.write(f"Generated docs for {len(components)} components")

    def extract_variants(self, css_content):
        # Parse CSS comments like /* variant: primary */
        variants = []
        for match in re.finditer(r'/\*\s*variant:\s*(\w+)\s*\*/', css_content):
            variants.append({
                'name': match.group(1).title(),
                'class': f'btn btn-{match.group(1)}',
            })
        return variants
```

### Run command:

```bash
python manage.py generate_design_docs
```

---

## 6. Zeroheight (SaaS Solution)

**What it is:** Cloud-based design system documentation

**Features:**

- Syncs with Figma/Sketch
- Auto-generates docs
- Team collaboration
- Component tracking

**Pros:**

- Zero setup
- Beautiful output
- Design-engineer sync

**Cons:**

- Paid service (~$15/month)
- Less control
- External dependency

**Best for:** Teams using design tools (Figma, Sketch)

---

## 7. Stylelint + Documentation Plugins

**Generate docs from CSS annotations:**

```css
/* @component Button
   @description Interactive button element
   @variant primary - Main call-to-action
   @variant secondary - Alternative action
   @state hover - Mouse over state
*/
.btn {
  /* ... */
}
```

**Then parse with custom script**

---

## Recommendation for SciTeX

**Option A: Custom Django App (Recommended)**

- Tightly integrated with your Django app
- No build process needed
- Full control over output
- Start with JSON fixtures, evolve to database models
- Can export static HTML for docs sites

**Option B: Fractal**

- Good middle ground
- Standalone documentation site
- Works alongside Django app
- Professional output
- ~1 hour setup

**Option C: Storybook**

- If you eventually move to React/Vue frontend
- Best for component-driven development
- But adds complexity now

---

## Implementation Path for SciTeX

### Week 1: Setup

1. Create `design_system` Django app
2. Define component JSON structure
3. Create base template engine

### Week 2: Components

1. Convert existing components to JSON
2. Create template for auto-generation
3. Set up component previewer

### Week 3: Automation

1. Write CSS parser
2. Create management command
3. Auto-generate component docs

### Week 4: Enhancement

1. Add interactive variants
2. Add dark mode toggling
3. Add copy code buttons

<!-- EOF -->
