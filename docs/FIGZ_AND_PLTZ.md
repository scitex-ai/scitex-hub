<!-- ---
!-- Timestamp: 2025-12-16 20:10:58
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/FIGZ_AND_PLTZ.md
!-- --- -->

# FIGZ and PLTZ Bundle Formats

## Overview

SciTeX uses two bundle formats for reproducible scientific figures:

| Format  | Purpose            | Contents                                    |
|---------|--------------------|---------------------------------------------|
| `.pltz` | Single plot bundle | spec.json, style.json, data.csv, exports/   |
| `.figz` | Multi-panel figure | spec.json, style.json, nested .pltz bundles |

## Format Variants

Each bundle can exist in two forms:

| Suffix                | Type        | Use Case                    |
|-----------------------|-------------|-----------------------------|
| `.pltz` / `.figz`     | ZIP archive | Storage, transfer, download |
| `.pltz.d` / `.figz.d` | Directory   | Editing, development        |

## Architecture Decision: ZIP-First

**Preferred**: Store as ZIP (`.pltz`, `.figz`), extract on-demand for editing.

```
Storage (primary)     Working (temp)           Download
-----------------     --------------           --------
Figure1.figz    -->   /tmp/.../Figure1.figz.d  -->  .figz or .figz.d
    |-A.pltz    -->       |-A.pltz.d           -->  .pltz or .pltz.d
```

### Benefits

- Single source of truth (no sync issues between .d and ZIP)
- Atomic operations (ZIP is all-or-nothing)
- Cleaner project tree
- Easier backup/transfer

## scitex.io.bundle as Proxy

Django delegates all bundle I/O to `scitex.io.bundle`, which handles format transparently:

```python
import scitex.io.bundle as bundle

# Or import specific functions
from scitex.io.bundle import (
    # Core operations
    load,             # Loads from .pltz or .pltz.d
    save,             # Saves with atomic writes
    copy,             # Copy between formats
    pack,             # Convert .pltz.d -> .pltz
    unpack,           # Convert .pltz -> .pltz.d

    # In-memory ZIP access (no extraction)
    ZipBundle,        # Context manager for atomic read/write
    open_zip,         # Convenience function
    create_zip,       # Create new bundle atomically
    zip_directory,    # Convert directory to ZIP

    # Nested bundles (figz containing pltz)
    nested,           # Namespace for nested operations
    # nested.resolve(), nested.get_file(), nested.get_json(),
    # nested.get_preview(), nested.put_file(), nested.put_json()
)
```

## Django Service Pattern

```python
# Django services are thin wrappers
from scitex.io.bundle import load, ZipBundle, nested

class PltzService:
    @staticmethod
    def load_bundle(bundle_path):
        return load(bundle_path, in_memory=True)

    @staticmethod
    def get_preview_image(bundle_path):
        with ZipBundle(bundle_path, mode='r') as zb:
            return zb.read_bytes('exports/plot.png')

    @staticmethod
    def get_nested_preview(bundle_path):
        # For paths like "Figure1.figz/A.pltz"
        return nested.get_preview(bundle_path)
```

## Bundle Structure

### .pltz Bundle

```
plot.pltz.d/
|- spec.json          # Plot specification (traces, axes, data refs)
|- style.json         # Visual styling (colors, fonts, sizes)
|- data.csv           # Source data
|- exports/
|   |- plot.png       # Rendered preview
|   |- plot_hitmap.png
|   |- plot.svg
|- cache/
    |- geometry_px.json
```

### .figz Bundle

```
Figure1.figz.d/
|- spec.json          # Figure layout, panel positions
|- style.json         # Figure-level styling
|- A.pltz.d/          # Panel A (nested pltz)
|- B.pltz.d/          # Panel B (nested pltz)
|- exports/
    |- Figure1.png    # Composed figure
```

## Key APIs

| Operation      | scitex.io.bundle Function                           |
|----------------|-----------------------------------------------------|
| Load bundle    | `bundle.load(path, in_memory=True)`                 |
| Save bundle    | `bundle.save(data, path, as_zip=True)`              |
| Read from ZIP  | `ZipBundle(path).read_json('spec.json')`            |
| Write to ZIP   | `ZipBundle(path, 'w').write_json('spec.json', data)`|
| Copy bundle    | `bundle.copy(src, dst)`                             |
| Pack directory | `bundle.zip_directory('plot.pltz.d')`               |
| Nested resolve | `bundle.nested.resolve('Figure1.figz/A.pltz')`      |
| Nested preview | `bundle.nested.get_preview('Figure1.figz/A.pltz')`  |
| Nested JSON    | `bundle.nested.get_json('Figure1.figz/A.pltz/spec.json')` |

## Migration Notes

Current state: Django services updated to use `scitex.io.bundle` API.

### API Migration (2025-12-16)

| Old Import | New Import |
|------------|------------|
| `from scitex.io import load_bundle` | `from scitex.io.bundle import load` |
| `from scitex.io import copy_bundle` | `from scitex.io.bundle import copy` |
| `from scitex.io import zip_directory_bundle` | `from scitex.io.bundle import zip_directory` |
| `from scitex.io import resolve_nested_bundle` | `from scitex.io.bundle import nested; nested.resolve()` |
| `from scitex.io import get_nested_preview` | `from scitex.io.bundle import nested; nested.get_preview()` |
| `from scitex.io import get_nested_json` | `from scitex.io.bundle import nested; nested.get_json()` |
| `from scitex.io import put_nested_file` | `from scitex.io.bundle import nested; nested.put_file()` |
| `from scitex.io import put_nested_json` | `from scitex.io.bundle import nested; nested.put_json()` |

### Target Architecture

1. Storage uses ZIP only (`.pltz`, `.figz`)
2. Editing extracts to temp directory on-demand
3. Save repacks to ZIP atomically
4. Django services delegate to `scitex.io.bundle`

<!-- EOF -->