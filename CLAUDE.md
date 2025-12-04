<!-- ---
!-- Timestamp: 2025-12-04
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/CLAUDE.md
!-- --- -->

## DO NOT EDIT
Agents: Never edit this file. Only user may modify.

## Skills Available
Detailed guidelines via skills (use `Skill` tool):
- `scitex-cloud` - Dev environment, Django organization, TypeScript, debugging
- `development-philosophy` - Cycles, naming, architecture, multi-agent coordination
- `programming-common` - Clean code, testing, refactoring

---

## Project Essentials

### SciTeX Principle
- Works everywhere: local, cloud, self-hosting
- `scitex` package = core logic + simple APIs
- Django = cloud interface
- Project-centric: all apps link to user/group projects

### Development
- Docker only: `make env=dev start|stop|restart`
- No direct `python manage.py` - use Docker
- Hot-reload enabled for Python, TypeScript, templates
- Test user: `test-user` / `Password123!`

### Deployment Environments
- dev: Development (127.0.0.1:8000)
- nas: Production (home NAS, not VPS)
- Key files: `SECRET/.env.{dev,nas}`, `config/settings/settings_{shared,dev,nas}.py`

---

## Philosophy
- Keep it simple - necessary and sufficient only
- Be explicit - no hidden fallbacks, errors with guidance
- No fake data - show real errors on website
- Intuitive UX - no learning curve needed

## File Size & Refactoring
- TS/PY: 256 lines, CSS: 512, HTML: 1024 - refactor proactively
- Check: `./scripts/check_file_sizes.sh --verbose`
- See `scitex-cloud` skill for full guidelines

---

## Reference Docs
- `./docs/PHILOSOPHY.md` - Full philosophy
- `./docs/MONETIZATION_STRATEGY_IMPLEMENTATION.md` - Business strategy
- `./externals/overleaf/` - Learn from Overleaf source

<!-- EOF -->
