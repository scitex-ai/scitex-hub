---
name: refactoring-rules
description: Refactoring rules for scitex-cloud Django/TypeScript codebase.
---

# Refactoring Rules

## File Size
- Keep files manageable — long files cause issues
- Check: `./scripts/check_file_sizes.sh --verbose`

## No Inline CSS/Script
- NEVER use inline CSS or script tags
- Always use external CSS and TypeScript files
- Link them properly in templates

## TypeScript Only
- NEVER use JavaScript — always TypeScript
- TS files are automatically built (see `tsconfig.json`)
- Check TypeScript compilation before committing

## Django Conventions
- Follow Django project structure rules
- See `./GITIGNORED/RULES/*.md` for detailed rules

## Commit Strategy
- Commit after each logical chunk of refactoring
- Use descriptive commit messages
