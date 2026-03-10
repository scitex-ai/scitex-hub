"""Diff generation methods for manuscript comparison."""

import difflib
import re
from typing import Dict, List, Any
from .diff_utils import DiffUtils


class DiffEngine:
    """Advanced diff generation for manuscript content."""

    def __init__(self):
        self.word_pattern = re.compile(r"\b\w+\b|[^\w\s]")
        self.sentence_pattern = re.compile(r"[.!?]+")
        self.utils = DiffUtils()

    def generate_unified_diff(
        self, text1: str, text2: str, context_lines: int = 3
    ) -> Dict[str, Any]:
        """Generate unified diff between two text versions."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                lines1,
                lines2,
                fromfile="Version A",
                tofile="Version B",
                n=context_lines,
            )
        )

        # Parse diff into structured format
        changes = []
        current_hunk = None

        for line in diff:
            if line.startswith("@@"):
                if current_hunk:
                    changes.append(current_hunk)
                current_hunk = {"header": line.strip(), "lines": []}
            elif current_hunk and (
                line.startswith(" ") or line.startswith("+") or line.startswith("-")
            ):
                change_type = (
                    "context"
                    if line.startswith(" ")
                    else ("addition" if line.startswith("+") else "deletion")
                )
                current_hunk["lines"].append(
                    {
                        "type": change_type,
                        "content": line[1:],
                        "line_number": len(current_hunk["lines"]) + 1,
                    }
                )

        if current_hunk:
            changes.append(current_hunk)

        return {
            "type": "unified",
            "changes": changes,
            "raw_diff": "".join(diff),
            "stats": self.utils.calculate_diff_stats(diff),
        }

    def generate_side_by_side_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Generate side-by-side diff visualization."""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        # Use difflib.HtmlDiff for side-by-side comparison
        html_diff = difflib.HtmlDiff(wrapcolumn=80)
        html_content = html_diff.make_table(
            lines1,
            lines2,
            fromdesc="Previous Version",
            todesc="Current Version",
            context=True,
            numlines=3,
        )

        # Parse changes for structured data
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            elif tag == "replace":
                changes.append(
                    {
                        "type": "replace",
                        "old_start": i1 + 1,
                        "old_end": i2,
                        "new_start": j1 + 1,
                        "new_end": j2,
                        "old_lines": lines1[i1:i2],
                        "new_lines": lines2[j1:j2],
                    }
                )
            elif tag == "delete":
                changes.append(
                    {
                        "type": "delete",
                        "old_start": i1 + 1,
                        "old_end": i2,
                        "lines": lines1[i1:i2],
                    }
                )
            elif tag == "insert":
                changes.append(
                    {
                        "type": "insert",
                        "new_start": j1 + 1,
                        "new_end": j2,
                        "lines": lines2[j1:j2],
                    }
                )

        return {
            "type": "side_by_side",
            "html": html_content,
            "changes": changes,
            "stats": self.utils.calculate_change_stats(changes),
        }

    def generate_word_level_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Generate word-level diff for precise change tracking."""
        words1 = self.word_pattern.findall(text1)
        words2 = self.word_pattern.findall(text2)

        matcher = difflib.SequenceMatcher(None, words1, words2)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                changes.append({"type": "equal", "words": words1[i1:i2]})
            elif tag == "replace":
                changes.append(
                    {
                        "type": "replace",
                        "old_words": words1[i1:i2],
                        "new_words": words2[j1:j2],
                    }
                )
            elif tag == "delete":
                changes.append({"type": "delete", "words": words1[i1:i2]})
            elif tag == "insert":
                changes.append({"type": "insert", "words": words2[j1:j2]})

        return {
            "type": "word_level",
            "changes": changes,
            "stats": {
                "words_added": sum(
                    len(c.get("words", c.get("new_words", [])))
                    for c in changes
                    if c["type"] in ["insert", "replace"]
                ),
                "words_removed": sum(
                    len(c.get("words", c.get("old_words", [])))
                    for c in changes
                    if c["type"] in ["delete", "replace"]
                ),
                "words_unchanged": sum(
                    len(c["words"]) for c in changes if c["type"] == "equal"
                ),
            },
        }

    def generate_semantic_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Generate semantic diff focusing on meaningful changes."""
        # Split into sentences for semantic analysis
        sentences1 = self.sentence_pattern.split(text1)
        sentences2 = self.sentence_pattern.split(text2)

        # Clean empty sentences
        sentences1 = [s.strip() for s in sentences1 if s.strip()]
        sentences2 = [s.strip() for s in sentences2 if s.strip()]

        matcher = difflib.SequenceMatcher(None, sentences1, sentences2)
        semantic_changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            change = {
                "type": tag,
                "severity": self.utils.assess_change_severity(
                    sentences1[i1:i2] if tag in ["delete", "replace"] else [],
                    sentences2[j1:j2] if tag in ["insert", "replace"] else [],
                ),
            }

            if tag == "replace":
                change.update(
                    {
                        "old_sentences": sentences1[i1:i2],
                        "new_sentences": sentences2[j1:j2],
                        "description": self.utils.describe_change(
                            sentences1[i1:i2], sentences2[j1:j2]
                        ),
                    }
                )
            elif tag == "delete":
                change.update(
                    {
                        "sentences": sentences1[i1:i2],
                        "description": f"Removed {len(sentences1[i1:i2])} sentence(s)",
                    }
                )
            elif tag == "insert":
                change.update(
                    {
                        "sentences": sentences2[j1:j2],
                        "description": f"Added {len(sentences2[j1:j2])} sentence(s)",
                    }
                )

            semantic_changes.append(change)

        return {
            "type": "semantic",
            "changes": semantic_changes,
            "stats": {
                "major_changes": len(
                    [c for c in semantic_changes if c["severity"] == "major"]
                ),
                "minor_changes": len(
                    [c for c in semantic_changes if c["severity"] == "minor"]
                ),
                "total_changes": len(semantic_changes),
            },
        }


# EOF
