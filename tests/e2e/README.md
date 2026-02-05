# E2E Tests for SciTeX Cloud

Minimal end-to-end tests that must pass before deployment.

## Philosophy

> "デプロイ押すのが怖くない" 状態を作る

These tests verify critical user flows against a running server. They don't test everything - just the things that, if broken, would make the app unusable.

## Test Categories

| File | Priority | What it tests |
|------|----------|---------------|
| `test_00_health.py` | CRITICAL | Services running, DB connected |
| `test_01_visitor_flow.py` | HIGH | Anonymous user experience, visitor pool |
| `test_02_auth.py` | HIGH | Login/logout, session security |
| `test_03_project.py` | HIGH | Project creation, listing |
| `test_04_modules.py` | MEDIUM | Module pages accessible |
| `test_05_api_endpoints.py` | HIGH | Critical APIs respond |
| `test_06_signup_email.py` | HIGH | Registration, email verification |

## Usage

```bash
# Quick check against local dev
./tests/e2e/run_e2e.sh

# Against production
./tests/e2e/run_e2e.sh prod

# Against staging
./tests/e2e/run_e2e.sh staging

# Against custom URL
./tests/e2e/run_e2e.sh https://my-server.com
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCITEX_BASE_URL` | `http://127.0.0.1:8000` | Server URL to test |
| `SCITEX_E2E_TEST_USER` | `test-e2e-user` | Test user username |
| `SCITEX_E2E_TEST_PASS` | `TestE2E123!` | Test user password |
| `SCITEX_E2E_TIMEOUT` | `30` | Request timeout (seconds) |

## Creating Test User

For authenticated tests, create a test user:

```bash
# In Django container
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user, created = User.objects.get_or_create(
    username='test-e2e-user',
    defaults={
        'email': 'e2e-test@example.com',
        'is_active': True,
    }
)
if created:
    user.set_password('TestE2E123!')
    user.save()
    print('Created test user')
else:
    print('Test user already exists')
"
```

## Pre-Deployment Checklist

Before deploying, these tests should pass:

1. **Health** - All services responding
2. **Auth** - Login/logout works
3. **Signup** - New users can register
4. **Project** - `/new/` page loads
5. **APIs** - Critical endpoints respond

## Deployment Workflow

```
MacBook (dev) → staging → production
     ↓               ↓         ↓
  run tests      run tests  run tests
```

```bash
# 1. Test locally
./tests/e2e/run_e2e.sh local

# 2. Push to staging, test there
ssh server "cd /srv/scitex-staging && git pull && docker-compose up -d"
./tests/e2e/run_e2e.sh staging

# 3. If passing, deploy to prod
ssh server "cd /srv/scitex-prod && git pull && docker-compose up -d"
./tests/e2e/run_e2e.sh prod
```

## Adding New Tests

1. Add to appropriate existing file, or create new `test_XX_name.py`
2. Keep tests fast (< 5 seconds each)
3. Use descriptive names: `test_<feature>_<behavior>`
4. Mark non-critical tests with `@pytest.mark.xfail` if they shouldn't block deployment
