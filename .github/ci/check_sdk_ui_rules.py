"""Run the SDK's scoped UI gate without hiding runtime or JSON failures."""

import json
from pathlib import Path
import subprocess

TARGETS = (
    "apps/workspace/writer_app",
    "apps/workspace/apps_app/launcher_links",
    "apps/workspace/scholar_app/static/scholar_app/css/common/",
)
ENFORCED = {f"STX-UI{i}" for i in (108, 109, 110, 111)}


def checked_findings(status: int, stdout: str, stderr: str) -> list[dict]:
    """Accept only the SDK's complete coverage-plus-violation JSONL contract."""
    if status not in (0, 1) or stderr.strip():
        raise ValueError("SDK UI linter did not complete cleanly")
    records = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    coverage = [r for r in records if isinstance(r, dict) and r.get("kind") == "coverage"]
    if len(coverage) != 1 or not isinstance(coverage[0].get("not_inspected"), list):
        raise ValueError("SDK UI linter returned no unique coverage record")
    findings = [r for r in records if r is not coverage[0]]
    if any(not isinstance(r, dict) or not isinstance(r.get("rule"), str)
           or not r["rule"].startswith("STX-UI") or not isinstance(r.get("path"), str)
           or type(r.get("line")) is not int for r in findings):
        raise ValueError("SDK UI linter returned malformed findings")
    if bool(findings) != (status == 1):
        raise ValueError("SDK UI linter status disagrees with its findings")
    return findings


def main() -> int:
    """Retain the existing rule scope; every invocation must produce valid output."""
    failures = []
    reports = []
    for target in TARGETS:
        result = subprocess.run(["scitex-sdk", "ui", "lint", "--json", target],
                                capture_output=True, text=True, timeout=120)
        findings = checked_findings(result.returncode, result.stdout, result.stderr)
        reports.append({"target": target, "findings": findings})
        failures.extend(r for r in findings if r["rule"] in ENFORCED)
    Path("ui-violations.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps({"enforced_rules": sorted(ENFORCED), "enforced_findings": len(failures),
                      "informational_findings": sum(len(r["findings"]) for r in reports) - len(failures)}))
    for row in failures:
        print(f"{row['path']}:{row['line']}: {row['rule']}")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
