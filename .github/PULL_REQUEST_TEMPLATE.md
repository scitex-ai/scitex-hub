<!--
Delete any section that does not apply. Keep the guard section honest — it is the
only one that exists because we shipped the same defect four times in one session.
-->

## What

<!-- What changes, and why. One paragraph. -->

## How it was verified

<!--
State WHERE you ran it, not just that it passed. The same command on two fleet
hosts has given a pass and a crash.

If you could not run something, say so plainly rather than leaving it implied.
"CI is the gate here" is an acceptable answer; silence is not.
-->

## Guard tests — paste the RED

<!--
ONLY if this PR adds or changes a test that exists to stop a named defect
(`@pytest.mark.guards`). Otherwise delete this section.

Paste the observed FAILING output of the guard against the defect it defends
against — the actual terminal text, not a description of it.

WHY WE ASK FOR THIS. A guard that has never been seen failing is unverified in
exactly the way an unrun fix is. On 2026-08-15 four gates that could not fail were
found in one session; two had been written that morning by the person who then
found them. In both cases producing a red would have been impossible without
discovering the bug — which is the whole point. Reproducing the defect is the
cheapest way to learn that your guard does not catch it.

    $ pytest tests/... -q
    FAILED tests/... - AssertionError: ...

If you cannot produce a red, that is the finding. Say so here and explain why the
guard is still worth landing.
-->

## Cards

<!-- scitex-cards ids this closes or advances. -->
