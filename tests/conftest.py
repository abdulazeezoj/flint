import pytest

from conjure import prefs


@pytest.fixture(autouse=True)
def isolated_prefs_dir(tmp_path, monkeypatch):
    """Every test gets its own `~/.conjure` stand-in so the suite never
    reads or writes the real user home directory, and no state leaks
    between tests."""
    prefs_dir = tmp_path / "_conjure_home" / ".conjure"
    monkeypatch.setattr(prefs, "PREFS_DIR", prefs_dir)
    monkeypatch.setattr(prefs, "PREFS_FILE", prefs_dir / "last.json")
