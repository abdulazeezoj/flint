import pytest

from flint import prefs


@pytest.fixture(autouse=True)
def isolated_prefs_dir(tmp_path, monkeypatch):
    """Every test gets its own `~/.flint` stand-in so the suite never
    reads or writes the real user home directory, and no state leaks
    between tests."""
    prefs_dir = tmp_path / "_flint_home" / ".flint"
    monkeypatch.setattr(prefs, "PREFS_DIR", prefs_dir)
    monkeypatch.setattr(prefs, "PREFS_FILE", prefs_dir / "last.json")
