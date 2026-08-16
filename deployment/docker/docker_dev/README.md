# Development

## Start

```bash
make env=dev start
```

## URLs

| Service | URL |
|---------|-----|
| Django | http://localhost:8000 |
| Gitea | http://localhost:3001 |
| Flower | http://localhost:5555 |

## Test User

- Username: `test-user`
- Password: printed by `init_test_user` on first run (set `SCITEX_HUB_TEST_USER_PASSWORD` to choose it)

## Commands

```bash
make env=dev status
make env=dev logs
make env=dev restart
make env=dev rebuild
```
