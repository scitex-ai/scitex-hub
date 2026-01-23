# Dockerfile Optimization

## Key Optimizations

1. **Layer ordering** - Least to most frequently changing
2. **Cache mounts** - Reuse pip/playwright downloads
3. **Multi-stage** - Production only, smaller images

## Build Times

| Change | Time |
|--------|------|
| Code only | ~10 sec |
| Requirements | ~3 min |
| Full rebuild | ~15 min |
