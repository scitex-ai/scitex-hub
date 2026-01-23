"""Utility functions for diff operations."""

from typing import Dict, List


class DiffUtils:
    """Helper methods for diff calculations and analysis."""

    def calculate_diff_stats(self, diff_lines: List[str]) -> Dict[str, int]:
        """Calculate statistics from unified diff."""
        additions = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        return {
            "additions": additions,
            "deletions": deletions,
            "changes": additions + deletions,
        }

    def calculate_change_stats(self, changes: List[Dict]) -> Dict[str, int]:
        """Calculate statistics from structured changes."""
        additions = sum(
            len(c.get("lines", c.get("new_lines", [])))
            for c in changes
            if c["type"] in ["insert", "replace"]
        )
        deletions = sum(
            len(c.get("lines", c.get("old_lines", [])))
            for c in changes
            if c["type"] in ["delete", "replace"]
        )

        return {"additions": additions, "deletions": deletions, "changes": len(changes)}

    def assess_change_severity(
        self, old_sentences: List[str], new_sentences: List[str]
    ) -> str:
        """Assess the severity of semantic changes."""
        # Simple heuristic: length difference and word overlap
        old_text = " ".join(old_sentences)
        new_text = " ".join(new_sentences)

        length_ratio = abs(len(new_text) - len(old_text)) / max(
            len(old_text), len(new_text), 1
        )

        if length_ratio > 0.5:
            return "major"
        elif length_ratio > 0.2:
            return "moderate"
        else:
            return "minor"

    def describe_change(
        self, old_sentences: List[str], new_sentences: List[str]
    ) -> str:
        """Generate human-readable description of changes."""
        if not old_sentences:
            return f"Added {len(new_sentences)} new sentence(s)"
        elif not new_sentences:
            return f"Removed {len(old_sentences)} sentence(s)"
        else:
            return f"Modified {len(old_sentences)} sentence(s) to {len(new_sentences)} sentence(s)"

    def generate_diff_html(self, diff_data: Dict) -> str:
        """Generate HTML representation of diff data."""
        if diff_data["type"] == "side_by_side":
            return diff_data.get("html", "")

        # Generate simple HTML for other diff types
        html_parts = ['<div class="diff-container">']

        if diff_data["type"] == "unified":
            for change in diff_data["changes"]:
                html_parts.append('<div class="diff-hunk">')
                html_parts.append(f'<div class="diff-header">{change["header"]}</div>')

                for line in change["lines"]:
                    css_class = f"diff-{line['type']}"
                    html_parts.append(
                        f'<div class="{css_class}">{line["content"]}</div>'
                    )

                html_parts.append("</div>")

        elif diff_data["type"] == "word_level":
            for change in diff_data["changes"]:
                if change["type"] == "equal":
                    html_parts.append(
                        f'<span class="diff-equal">{" ".join(change["words"])}</span>'
                    )
                elif change["type"] == "insert":
                    html_parts.append(
                        f'<span class="diff-insert">{" ".join(change["words"])}</span>'
                    )
                elif change["type"] == "delete":
                    html_parts.append(
                        f'<span class="diff-delete">{" ".join(change["words"])}</span>'
                    )
                elif change["type"] == "replace":
                    html_parts.append(
                        f'<span class="diff-delete">{" ".join(change["old_words"])}</span>'
                    )
                    html_parts.append(
                        f'<span class="diff-insert">{" ".join(change["new_words"])}</span>'
                    )

        html_parts.append("</div>")
        return "".join(html_parts)

    def reconstruct_content(self, section_contents: Dict) -> str:
        """Reconstruct full content from section contents."""
        content_parts = []

        # Sort sections by order
        sorted_sections = sorted(
            section_contents.items(), key=lambda x: x[1].get("order", 0)
        )

        for section_type, section_data in sorted_sections:
            content_parts.append(f"# {section_data['title']}\n")
            content_parts.append(section_data["content"])
            content_parts.append("\n\n")

        return "".join(content_parts)


# EOF
