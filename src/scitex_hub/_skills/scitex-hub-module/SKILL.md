---
name: scitex-hub-module
description: Mark functions as SciTeX workspace modules with the @module decorator and collect structured outputs. Canonical home — the umbrella scitex.module re-exports from here.
user-invocable: false
---

# scitex-hub: Workspace Modules

`scitex_hub.module` is the canonical implementation of the SciTeX workspace
module API: the `@module` decorator, the `output`/`html` helpers, the
`INJECTED` sentinel, `ModuleManifest`, and the file runner. The umbrella
`scitex.module` (and the legacy `scitex_cloud.module` alias) re-export from
here.

## Sub-skills

| File | Description |
|------|-------------|
| [01_module-decorator.md](01_module-decorator.md) | @module decorator, output/html helpers, INJECTED sentinel, ModuleManifest, CLI runner |

## Quick Reference

```python
from scitex_hub.module import module, output, html, INJECTED

@module(label="My Analysis", category="analysis")
def run(project=INJECTED, plt=INJECTED, logger=INJECTED):
    fig, ax = plt.subplots()
    output(fig, title="Result")
```
