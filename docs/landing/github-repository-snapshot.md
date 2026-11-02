# Landing repository cards

The open-source cards list public SciTeX platform, app, and foundation repositories.
The selection follows the ecosystem layers in the operator's presentation, with
repository existence checked against GitHub's official public REST endpoint.
The private presentation itself is not published with the site. The archived
`scitex-ui` repository is excluded; its maintained UI implementation is part of
`scitex-sdk`, which remains listed.

Stars and forks come from `stargazers_count` and `forks_count` in
[`GET /repos/{owner}/{repo}`](https://docs.github.com/en/rest/repos/repos#get-a-repository).
The checked-in snapshot is
`apps/infra/public_app/data/landing_github.json`; its visible `checked_at` is the
observed UTC refresh time, not a claim of live statistics. Repository descriptions
are GitHub metadata and are HTML-escaped by the template. Each repository retains
its own license; the cards do not claim that every dependency has one shared license.

From the repository root, refresh explicitly:

```bash
python -m apps.infra.public_app.services.refresh_landing_github
```

This command reads only the fixed public `scitex-ai` repository API endpoints,
without a GitHub token, and atomically replaces the snapshot. Each socket operation
has a four-second timeout; a sixty-second batch budget is checked between requests.
Responses are size-limited and must identify the exact expected public repository
with nonnegative integer counts. Redirects are refused. Review the diff before
committing. API limits, network errors and invalid responses produce explicitly
unavailable rows and a nonzero command exit, rather than fabricated zero counts.
The public metadata API's unauthenticated rate limit still applies.

Landing requests never invoke this refresher. The existing `landing_i18n` template
library reads the local snapshot, caching by file modification time; no database,
credential, user directory, scheduler or runtime network access is required. Missing
or malformed snapshots render links with “Counts unavailable”. The three group
headings do not create additional landing navigation sections.

`landing_research_demo.html` is a separate optional disclosure for the Apps section.
It uses the existing public-view media URL context and loads only on manual video
interaction (`preload="none"`, no autoplay), preserving the demos-index link.
