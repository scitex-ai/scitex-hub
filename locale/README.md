# locale/ — Django i18n message catalogs

Scope (2026-07 decision): only **legal / landing** surfaces are authored
in Japanese (e.g. `/tokushoho/` 特定商取引法に基づく表記). The app
interior stays English/untranslated for now.

Settings rails live in `config/settings/settings_shared.py`:
`USE_I18N`, `LocaleMiddleware`, `LANGUAGES = [en, ja]`,
`LOCALE_PATHS = [BASE_DIR / "locale"]`.

## Workflow

```bash
# Extract {% trans %} / gettext strings into .po catalogs
# (requires GNU gettext: apt-get install gettext)
python manage.py makemessages -l ja
python manage.py makemessages -l en

# Compile .po -> .mo (needed at runtime for translated locales)
python manage.py compilemessages
```

Note: pages authored in Japanese use the Japanese text as the msgid, so
the `ja` catalog needs no entries for them — the catalogs exist so an
English translation can be added later without touching templates.
