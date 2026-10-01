---
description: Keep application behavior in leaf packages and mount it through SciTeX SDK contracts while preserving existing application quality.
---

# Leaf GUI ownership

Use the installed SDK GUI skill before choosing implementation commands.
The leaf's `src/<leaf_pkg>/_django` owns views, models/migrations, jobs,
templates and frontend assets. Hub supplies generic authentication, authorized
project/storage/store capabilities, app discovery, mounting and host chrome.
SDK connects standalone and hosted modes; native mobile clients remain future
work.

Owners: Agents → scitex-agent-container; Cards → scitex-cards; Storage →
scitex-storage; Stats/Scholar/Writer → their corresponding packages;
FigRecipe → figrecipe; Clew → scitex-clew.

Agents, Cards, Storage and Stats already use generic plugin mounts in audited
develop. Their SDK adoption and some host coupling still need work. Scholar,
Writer and FigRecipe retain legacy Hub surfaces. Writer collaboration/arXiv/
job state and Scholar ORM libraries/jobs are not replaced by their current
leaf GUIs. Preserve existing routes until equivalent features and migration
compatibility are tested. Moving only an include or import is insufficient.

The local Clew candidate removes the Hub domain implementation and uses its
leaf entry point, manifest, relative URLs, workspace partial and compiled
assets. Label `clew_app`, its table names and initial migration remain stable.
Hub's project store provider imports no Clew schemas or verification code.

For workspace embedding, the leaf declares `partial_template` and
`context_builder` in its manifest. Hub calls the builder, then injects the
registry's resolved URL as `stx_mount`; an explicit root mount becomes an
empty string. Leaf context must obtain authorized SDK capabilities before
rendering. The generic host preserves SDK access refusals as HTTP 4xx and
unavailable capabilities as 503, with non-cacheable responses that omit
private exception details. Other application errors still propagate.

`tests/architecture/test_leaf_gui_ownership.py` prevents adding/changing domain
implementation in the remaining legacy Hub app trees. Deleting migrated
files is allowed. Its exact-file baseline is reviewed migration debt, not a
template for new Hub code. Update the baseline only for a deliberate reviewed
exception; feature and UI work should move to the owning leaf.

Validate standalone/plugin browser behavior, per-request project identity,
read/write and CSRF boundaries, user isolation, jobs, persistence, historical
URLs and packaged assets before cutover. The SDK/leaf candidates are local
and unpublished; the running development and production services do not
automatically use them.
