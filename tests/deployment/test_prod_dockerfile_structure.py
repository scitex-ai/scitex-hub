"""Offline production Dockerfile structure checks, not an image-build claim."""

from pathlib import Path
import re
import unittest

DOCKERFILE = (
    Path(__file__).resolve().parents[2]
    / "deployment/docker/docker_prod/Dockerfile.prod"
)


class ProductionDockerfileStructureTests(unittest.TestCase):
    def test_from_lines_are_image_declarations_not_accidental_prose(self):
        # Arrange
        declarations = [
            line
            for line in DOCKERFILE.read_text().splitlines()
            if line.startswith("FROM ")
        ]
        grammar = re.compile(
            r"FROM(?:\s+--platform=\S+)?\s+\S+(?:\s+AS\s+[A-Za-z0-9_.-]+)?",
            re.IGNORECASE,
        )
        # Act
        malformed = [line for line in declarations if not grammar.fullmatch(line)]
        # Assert
        self.assertEqual(malformed, [])

    def test_named_stages_are_unique(self):
        # Arrange
        source = DOCKERFILE.read_text()
        names = re.findall(
            r"^FROM\s+.+\s+AS\s+(\S+)\s*$", source, re.MULTILINE | re.IGNORECASE
        )
        # Act
        duplicates = {
            name.lower()
            for name in names
            if sum(other.lower() == name.lower() for other in names) > 1
        }
        # Assert
        self.assertEqual(duplicates, set())

    def test_pinned_storage_tool_is_copied_once_to_runtime(self):
        # Arrange
        source = DOCKERFILE.read_text()
        instruction = (
            "COPY --from=storage-tools-builder /out/fclones /usr/local/bin/fclones"
        )
        # Act
        copies = source.count(instruction)
        # Assert
        self.assertEqual(copies, 1)


if __name__ == "__main__":
    unittest.main()
