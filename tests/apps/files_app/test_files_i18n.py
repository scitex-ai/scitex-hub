"""Files app names read naturally in Japanese."""

import subprocess
import sys
from pathlib import Path

import pytest
from django.utils import translation
from django.utils.translation import gettext, pgettext

_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(name="compiled_catalogs", scope="module")
def _compiled_catalogs():
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    translation.trans_real._translations.clear()
    yield
    translation.trans_real._translations.clear()


def test_files_tile_name_is_japanese(compiled_catalogs):
    # Arrange
    label = "Files"
    # Act
    with translation.override("ja"):
        rendered = pgettext("app name", label)
    # Assert
    assert rendered == "ファイル"


def test_downloads_folder_is_shown_in_japanese(compiled_catalogs):
    # Arrange
    folder = "Downloads"
    # Act
    with translation.override("ja"):
        rendered = gettext(folder)
    # Assert
    assert rendered == "ダウンロード"
