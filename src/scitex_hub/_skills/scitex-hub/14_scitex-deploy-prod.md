---
description: |
  [TOPIC] SciTeX Hub - Deploy Production
  [DETAILS] SciTeX Hub - Deploy Production.
tags: [scitex-hub-scitex-deploy-prod]
---

# Production deployment compatibility entry

Use [the canonical image deployment runbook](12_deployment-production.md).
It owns the candidate-only build, real resource limits, immutable image checks,
staging, targeted three-role swap, backup/rollback and post-boot verification.
This compatibility entry intentionally contains no independent raw-Compose or
job/data-deleting recovery recipe.
