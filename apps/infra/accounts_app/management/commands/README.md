# Account Management Commands

Django management commands for user account administration.

## Available Commands

### `list_users` - List all users in database

List all users with filtering and formatting options.

#### Basic Usage

```bash
# Production
docker exec scitex-cloud-prod-django-1 python manage.py list_users

# Development
docker exec scitex-cloud-dev-django-1 python manage.py list_users
```

#### Options

```bash
# Show detailed information
python manage.py list_users --verbose

# Output as JSON
python manage.py list_users --format json

# Output as CSV
python manage.py list_users --format csv

# Filter by user type
python manage.py list_users --staff-only
python manage.py list_users --superuser-only
python manage.py list_users --active-only
python manage.py list_users --inactive-only
```

#### Examples

```bash
# List all users in table format (default)
docker exec scitex-cloud-prod-django-1 python manage.py list_users

# List only staff users with details
docker exec scitex-cloud-prod-django-1 python manage.py list_users --staff-only --verbose

# Export all users as JSON
docker exec scitex-cloud-prod-django-1 python manage.py list_users --format json > users.json

# List inactive users only
docker exec scitex-cloud-prod-django-1 python manage.py list_users --inactive-only
```

## Quick Access Script

For convenience, a shell script is also available that doesn't require rebuilding containers:

```bash
# Production
./scripts/maintenance/list_users.sh prod

# Development
./scripts/maintenance/list_users.sh dev
```

## Output Format

### Table Format (default)

```
================================================================================
Total users: 2
================================================================================

Username             Email                               Active   Staff    Super    Joined
------------------------------------------------------------------------------------------------
ywatanabe            ywatanabe@scitex.ai                 Yes      No       No       2025-11-01
eloghosa             eloghosaefficiency@gmail.com        Yes      No       No       2025-11-17
```

Color coding:
- **Red**: Superuser accounts
- **Yellow**: Staff accounts
- **Gray**: Inactive users
- **Default**: Regular active users

### JSON Format

```json
[
  {
    "username": "ywatanabe",
    "email": "ywatanabe@scitex.ai",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "date_joined": "2025-11-01T12:34:56Z"
  }
]
```

### CSV Format

```csv
username,email,is_active,is_staff,is_superuser,date_joined
ywatanabe,ywatanabe@scitex.ai,True,False,False,2025-11-01T12:34:56Z
```

## Notes

- The Django management command requires the container to be rebuilt to be available
- The shell script (`./scripts/maintenance/list_users.sh`) works immediately without rebuild
- Both methods query the same database and return the same information
