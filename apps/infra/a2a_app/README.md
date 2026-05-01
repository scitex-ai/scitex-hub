# a2a_app — A2A protocol surface for scitex.ai

Serves [Google A2A](https://a2a-protocol.org/) AgentCards and JSON-RPC
dispatch at **`https://a2a.scitex.ai/`** for the SciTeX / Orochi
agent fleet.

## What it serves

| Method | URL | Returns |
| --- | --- | --- |
| GET | `/.well-known/agent.json` | Fleet-level AgentCard (roster of 18+) |
| GET | `/v1/agents/` | JSON list of agents |
| GET | `/v1/agents/<name>/.well-known/agent.json` | Per-agent AgentCard |
| POST | `/v1/agents/<name>` | JSON-RPC `tasks/send`, `tasks/get` (auth required) |

GET endpoints are public discovery surface. POST requires an
`Authorization: Bearer <gitea-pat>` header — the bearer is validated
at runtime against `git.scitex.ai` (`GET /api/v1/user`), with positive
results cached for 60 seconds.

## How it works

```
client ──HTTP──► Cloudflare ──tunnel──► nginx ──proxy_pass──► django
                                                                │
                                                          a2a_app/views.py
                                                                │
                                  reads ${SCITEX_OROCHI_AGENTS_DIR}
                                  (mounted from ~/.scitex/orochi/shared/agents)
                                                                │
                                  projects v3 YAML → A2A AgentCard JSON
                                  via apps/infra/a2a_app/_card.py
```

The projection is request-aware: every AgentCard's `url` field is
built from `request.build_absolute_uri('/')`, so dev/prod surfaces
self-describe correctly without config.

## Files

| Path | Purpose |
| --- | --- |
| `_card.py` | v3 YAML → A2A AgentCard projection |
| `_auth.py` | Bearer-token validation at Gitea, with cache |
| `views.py` | 3 GET handlers + 1 POST JSON-RPC dispatcher |
| `urls.py` | Mounted at root by `config/urls.py` |
| `apps.py` | `AppConfig(label="a2a_app")` |

## Tests

```bash
docker exec scitex-cloud-prod-django-1 \
  python -m pytest /app/tests/apps/infra/a2a_app/ -v
```

5 structural tests run against every projected AgentCard. 2 schema
tests skip until `tests/fixtures/a2a_schema/agent_card.schema.json`
is bundled.

## Deploy

Code changes in `apps/infra/a2a_app/` need a Django image rebuild to
become durable across container recreates:

```bash
cd ~/proj/scitex-cloud/deployment/docker/docker_prod
docker compose build django && docker compose up -d --force-recreate django
```

For nginx config (`deployment/docker/common/nginx/nginx_prod.conf`),
the file is bind-mounted but the bind is keyed to the inode at
container start — atomic-write edits (Python `write_text`, `mv`) need
`docker compose up -d --force-recreate nginx` to pick up the new
inode. In-place edits (`sed -i`) survive a `nginx -s reload`.

## Cross-references

- Master nav (fleet-wide): `~/proj/scitex-orochi/GITIGNORED/A2A_PROTOCOL_SUPPORT.md`
- Cloud-side ops: `~/proj/scitex-cloud/GITIGNORED/A2A_PROTOCOL_SUPPORT-CLOUD.md`
- Identity sister track: `~/proj/scitex-orochi/GITIGNORED/GITEA_FORK_MODEL.md`
- Client-side skill: `scitex-orochi/_skills/scitex-orochi/51_a2a-client.md`

<!-- EOF -->
