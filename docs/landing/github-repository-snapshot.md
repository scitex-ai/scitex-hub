# Landing GitHub counts

Cards list the fixed public SciTeX platform, app and foundation repositories in
`services/landing_github.py`. The initial local snapshot renders immediately, then
`public_app/js/landing-github-counts.js` requests the anonymous GET-only endpoint
`/api/landing/github-counts/` on page load and every 60 seconds while visible.
Visibility restoration triggers a refresh too. Load the script as a module through
`app_static`. It sends no cookies or authorization header, has a ten-second browser
abort bound, and updates numeric text/accessibility labels only. No visible dated
snapshot notice is rendered. Errors, malformed counters and older source fallback
never replace visible last-known numbers with fabricated zeroes.

The endpoint fetches the [official public organization repository listing](https://docs.github.com/en/rest/repos/repos#list-organization-repositories),
not one API request per card. Only the fixed `scitex-ai` organization is queried;
there is no repository, URL or force-refresh parameter. Source qualification saw
78 public repositories on page 1 with no next page, containing all 17 selected
repositories. Up to three fixed pages of 100 are allowed. Redirects are refused,
each body is limited to 2 MB, socket operations time out at 2.5 seconds, and an
eight-second batch budget is checked between body chunks and pages. A blocked
socket operation can finish after the budget by at most its operation timeout.
Only exact expected public repository identities with nonnegative integer
`stargazers_count`/`forks_count` are admitted. No GitHub token is used or exposed.

The configured Django Redis cache shares a five-minute result and add-only refresh
lease across workers. Last-good live results are retained for 30 days. Failures
also receive a five-minute cooldown. A concurrent visitor uses last-good/source
fallback rather than starting another fetch; the lease expires naturally to avoid
one worker deleting a newer lease. Development's existing LocMem fallback provides
that gate per process, rather than across processes. An unavailable cache returns
source fallback without contacting GitHub. Dummy/database/unsupported cache types
also use source fallback, so this endpoint never provisions or uses application
DB state. It does not access auth, sessions, user files or models. Public HTTP
responses allow a further 30 seconds of HTTP caching.

`apps/infra/public_app/data/landing_github.json` is bootstrap-only when no last-good
live result exists. To maintain it explicitly from a normal Hub environment:

```bash
python -m apps.infra.public_app.services.refresh_landing_github
```

The manual refresher retains its fixed public-repository allowlist, bounded requests,
atomic snapshot replacement and honest unavailable/error status. Review the diff
before committing; no scheduler, service or automatic source-file writes are added.
Repository descriptions remain escaped GitHub metadata; each project has its own
license. The private presentation used to choose ecosystem layers is not published.

Offline cache/endpoint controls and the actual browser refresh protocol can be run
without GitHub/user traffic:

```bash
python -m unittest discover -s tests/apps/public_app/services -p 'test_landing_github*.py'
python .github/ci/check_landing_github_counts.py
```

The separate `landing_research_demo.html` is visible in the Demo section with
native playback controls and the existing media URLs; the counter feature does
not alter playback or add autoplay.

## Landing theme surfaces

Load `public_app/css/landing/theme.css` after the reference and target-layout
styles. It maps the active landing sections and panels to the shared
`--bg-page`, `--bg-surface`, `--bg-muted`, `--text-primary`, `--text-secondary`,
`--border-default` and `--accent` roles. It replaces fixed light paper/white
surfaces and the carousel's independent fixed palette; it does not filter,
recolor or replace screenshot/diagram image pixels. Shared SDK tab styles and
the existing semantic primary CTA tokens remain owned by their existing layers.
`python .github/ci/check_landing_themes.py` checks the actual styles in an owned
light/dark component fixture, including the 240px visible-label footer layout;
public-page acceptance remains a separate post-deployment check.
