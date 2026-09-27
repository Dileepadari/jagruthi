"""
Keeps the coverage denominator honest.

coverage.py only counts a module it has seen imported. That makes deleting a
test file *raise* the reported percentage, because the module it covered drops
out of the denominator entirely - so a floor alone does not protect anything.

Importing every file listed in .coveragerc here means each one is always
measured. Delete the tests for one and its coverage falls towards zero and the
floor catches it, which is the behaviour the floor is supposed to have.
"""

import configparser
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _scoped_files() -> list[str]:
    parser = configparser.ConfigParser()
    parser.read(REPO_ROOT / ".coveragerc")
    raw = parser.get("run", "include")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def test_coveragerc_lists_files():
    files = _scoped_files()
    assert files, ".coveragerc has no include list; the floor would measure nothing"


@pytest.mark.parametrize("relative_path", _scoped_files())
def test_every_scoped_file_exists_and_imports(relative_path):
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"{relative_path} is in .coveragerc but does not exist"
    module = relative_path.removesuffix(".py").replace("/", ".")
    importlib.import_module(module)
