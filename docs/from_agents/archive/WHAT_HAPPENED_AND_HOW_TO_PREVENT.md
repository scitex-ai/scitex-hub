<!-- ---
!-- Timestamp: 2025-10-18 13:50:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/WHAT_HAPPENED_AND_HOW_TO_PREVENT.md
!-- --- -->

# What Happened: App Conflicts and Migration Issues

## Summary of Issues

You encountered two main problems:
1. **URL namespace conflict**: `cloud_app` namespace was registered twice
2. **Database corruption**: Duplicate users in the database after manual migration file renaming

## Issue #1: URL Namespace Conflict

### What Happened

```
System check identified some issues:
WARNINGS:
?: (urls.W005) URL namespace 'cloud_app' isn't unique
```

### Root Cause

In `config/urls.py`:
1. `discover_app_urls()` auto-discovered and registered `cloud_app` at `/cloud/`
2. Manual registration also included `cloud_app` at `/` (root)
3. Both used the same namespace `cloud_app`, causing duplication

### The Fix

Modified `discover_app_urls()` to skip apps that are manually configured:

```python
def discover_app_urls():
    """Discover and register URLs for all apps in ./apps/."""
    # Apps to skip because they're manually configured below
    skip_apps = {'cloud_app'}

    for app_dir in sorted(apps_dir.iterdir()):
        app_name = app_dir.name

        # Skip apps that are manually configured
        if app_name in skip_apps:
            continue

        # ... rest of discovery logic
```

### Lesson Learned

**When manually configuring URLs for an app, exclude it from auto-discovery** to avoid namespace conflicts.

---

## Issue #2: Database Corruption from Manual Migration Renaming

### What Happened

```python
django.contrib.auth.models.User.MultipleObjectsReturned:
get() returned more than one User -- it returned 2!
```

You had:
- 2 users with email `ywata1989@gmail.com`
- ID: 3 (username: `ywatanabe1989`)
- ID: 6 (username: `ywatanabe`)

### Root Cause

When refactoring `workspace_app` to `profile_app`, you:
1. Created `profile_app` with new models
2. Manually renamed migration files using `~/.bin/utils/rename.sh`
3. This broke Django's migration history tracking

**The Problem**: Django tracks applied migrations in the `django_migrations` table. When you rename migration files:
- Django thinks old migrations (e.g., `workspace_app.0001_initial`) are still pending
- Django thinks new migrations (e.g., `profile_app.0001_initial`) haven't run
- This causes migrations to run multiple times or in wrong order
- Database state becomes inconsistent with migration history

### Migration History Analysis

Looking at the migrations:

```
apps/workspace_app/migrations/
├── 0001_initial.py
├── 0002_userprofile_avatar_userprofile_location.py
├── 0003_alter_project_collaborators.py
├── 0004_userprofile_last_active_project.py
├── 0005_remove_userprofile_last_active_project_and_more.py
└── 0006_delete_userprofile.py  # Deleted UserProfile from workspace_app

apps/profile_app/migrations/
└── 0001_initial.py  # Created UserProfile in profile_app
```

The migration shows `UserProfile` was:
1. Created in `workspace_app`
2. Modified several times
3. Deleted from `workspace_app` (0006)
4. Re-created in `profile_app` (0001)

**But the table name shows the issue:**

```python
# profile_app/migrations/0001_initial.py
options={
    "db_table": "workspace_app_userprofile",  # ❌ Still using workspace_app table name!
    "ordering": ["user__last_name", "user__first_name"],
},
```

This suggests you copied and renamed files, but Django's migration system lost track.

---

## How to Properly Refactor Apps (Core → Profile)

### ❌ WRONG WAY (What You Did)

```bash
# Don't do this!
cd apps/workspace_app/migrations/
~/.bin/utils/rename.sh workspace_app profile_app *.py
```

**Problems:**
- Breaks Django migration history
- Database thinks migrations haven't run
- Causes duplicate data
- Creates orphaned tables

### ✅ CORRECT WAY #1: Using Django Migrations (Recommended)

When you **cannot** start with a fresh database:

#### Step 1: Create the new app

```bash
python manage.py startapp profile_app apps/profile_app
```

#### Step 2: Copy models to new app

```python
# apps/profile_app/models.py
from django.db import models

class UserProfile(models.Model):
    # Copy model definition from workspace_app
    pass
```

#### Step 3: Create migration for new app

```bash
python manage.py makemigrations profile_app
```

#### Step 4: Create a data migration to copy data

```bash
python manage.py makemigrations profile_app --empty --name migrate_from_workspace_app
```

Edit the migration:

```python
# apps/profile_app/migrations/0002_migrate_from_workspace_app.py
def migrate_data_forward(apps, schema_editor):
    # Get old model from workspace_app
    OldUserProfile = apps.get_model('workspace_app', 'UserProfile')
    # Get new model from profile_app
    NewUserProfile = apps.get_model('profile_app', 'UserProfile')

    # Copy all data
    for old_profile in OldUserProfile.objects.all():
        NewUserProfile.objects.create(
            user=old_profile.user,
            bio=old_profile.bio,
            # ... copy all fields
        )

def migrate_data_backward(apps, schema_editor):
    # Reverse migration if needed
    NewUserProfile = apps.get_model('profile_app', 'UserProfile')
    NewUserProfile.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('profile_app', '0001_initial'),
        ('workspace_app', '0005_last_migration_before_split'),
    ]

    operations = [
        migrations.RunPython(migrate_data_forward, migrate_data_backward),
    ]
```

#### Step 5: Delete old model from workspace_app

```python
# apps/workspace_app/models.py
# Delete or comment out UserProfile class
```

```bash
python manage.py makemigrations workspace_app --name delete_userprofile
```

#### Step 6: Run all migrations

```bash
python manage.py migrate
```

This ensures:
- ✅ Django tracks all changes
- ✅ Data is preserved
- ✅ Can roll back if needed
- ✅ Production-safe

### ✅ CORRECT WAY #2: Fresh Start (What We Did)

When you **can** start with a fresh database:

```bash
# 1. Backup database
cp data/scitex_cloud_dev.db data/scitex_cloud_dev.db.backup_$(date +%Y%m%d_%H%M%S)

# 2. Delete database
rm data/scitex_cloud_dev.db

# 3. Update code (models, migrations properly created)

# 4. Run fresh migrations
python manage.py migrate

# 5. Create new superuser
python manage.py createsuperuser
```

**Advantages:**
- ✅ Clean slate
- ✅ No migration conflicts
- ✅ Fast for development

**Only use when:**
- Development environment
- No production data
- Single developer or small team

---

## Prevention Strategies

### 1. Never Manually Rename Migration Files

**DON'T:**
```bash
mv 0001_initial.py 0002_new_name.py
rename.sh old_name new_name migrations/
```

**DO:**
```bash
python manage.py makemigrations
python manage.py makemigrations --empty --name descriptive_name
```

### 2. Always Use Django's Migration System

```bash
# Create new migration
python manage.py makemigrations

# Check migration plan
python manage.py showmigrations

# Check SQL that will run
python manage.py sqlmigrate app_name migration_number

# Apply migrations
python manage.py migrate

# Rollback migration
python manage.py migrate app_name previous_migration_number
```

### 3. Test Migrations Before Production

```bash
# 1. Backup production database
pg_dump -U user database > backup.sql

# 2. Test on staging with production data copy
python manage.py migrate --database=staging

# 3. If successful, run on production
python manage.py migrate --database=production
```

### 4. Use Version Control for Migrations

```bash
# Always commit migrations
git add apps/*/migrations/
git commit -m "Add migration for UserProfile refactor"

# Never modify committed migrations that have run in production
```

### 5. Check Migration State

```bash
# List all migrations and their status
python manage.py showmigrations

# Check for unapplied migrations
python manage.py migrate --plan

# Check for migration conflicts
python manage.py makemigrations --check
```

### 6. Document Major Refactorings

Create a migration plan document before major changes:

```markdown
## Migration Plan: Refactor workspace_app → profile_app

### Current State
- UserProfile in workspace_app
- 150 users in production

### Steps
1. Create profile_app with UserProfile model
2. Create data migration to copy data
3. Update all ForeignKeys pointing to old model
4. Delete old model
5. Test on staging
6. Deploy to production

### Rollback Plan
If migration fails:
1. python manage.py migrate profile_app 0001_initial
2. Restore from backup
```

---

## Emergency Recovery Procedures

### If You Corrupt the Database

#### Option 1: Roll Back Migrations

```bash
# Find last good migration
python manage.py showmigrations

# Roll back to it
python manage.py migrate app_name migration_name
```

#### Option 2: Restore from Backup

```bash
# PostgreSQL
psql -U user -d database < backup.sql

# SQLite
cp backup.db current.db
```

#### Option 3: Fake Migrations (Use with Caution!)

If migrations are out of sync with database:

```bash
# Mark migration as applied without running it
python manage.py migrate --fake app_name migration_name

# Mark all migrations as applied
python manage.py migrate --fake-initial
```

**⚠️ WARNING**: Only use `--fake` if you know the database state matches the migration!

### If You Have Duplicate Data

```python
# Script to find and remove duplicates
from django.contrib.auth.models import User

# Find duplicates
duplicates = User.objects.values('email').annotate(
    count=Count('email')
).filter(count__gt=1)

for dup in duplicates:
    email = dup['email']
    users = User.objects.filter(email=email).order_by('date_joined')

    # Keep oldest, delete others
    keep = users.first()
    delete = users.exclude(pk=keep.pk)

    print(f"Keeping {keep.username}, deleting {[u.username for u in delete]}")
    delete.delete()
```

---

## Checklist for Future App Refactoring

- [ ] Create detailed migration plan
- [ ] Backup database
- [ ] Create new app using `startapp`
- [ ] Copy models to new app
- [ ] Create initial migration: `makemigrations new_app`
- [ ] Create data migration: `makemigrations new_app --empty`
- [ ] Write data migration code (forward and backward)
- [ ] Update all ForeignKey references
- [ ] Test on development database
- [ ] Test on staging with production data copy
- [ ] Document rollback procedure
- [ ] Run on production
- [ ] Monitor for errors
- [ ] Keep old app for one release cycle (for rollback)

---

## Key Takeaways

1. **Never manually rename migration files** - Always use Django's migration commands
2. **Test migrations thoroughly** - Especially with production data copies
3. **Use data migrations** - For moving data between apps
4. **Backup before migrating** - Always have a rollback plan
5. **Fresh start is OK for development** - But not for production!
6. **Check migration state regularly** - `python manage.py showmigrations`
7. **Document complex migrations** - Future you will thank you

---

## Resources

- [Django Migrations Documentation](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Data Migrations Guide](https://docs.djangoproject.com/en/5.2/topics/migrations/#data-migrations)
- [Migration Operations Reference](https://docs.djangoproject.com/en/5.2/ref/migration-operations/)

<!-- EOF -->
