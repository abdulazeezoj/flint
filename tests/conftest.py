import pytest

from brupy import prefs, updatecheck


@pytest.fixture(autouse=True)
def isolated_prefs_dir(tmp_path, monkeypatch):
    """Every test gets its own `~/.brupy` stand-in so the suite never
    reads or writes the real user home directory, and no state leaks
    between tests."""
    prefs_dir = tmp_path / "_brupy_home" / ".brupy"
    monkeypatch.setattr(prefs, "PREFS_DIR", prefs_dir)
    monkeypatch.setattr(prefs, "PREFS_FILE", prefs_dir / "last.json")
    monkeypatch.setattr(updatecheck, "CACHE_FILE", prefs_dir / "update_check.json")
    # Belt-and-suspenders: check_for_update() already no-ops when
    # non-interactive (true for nearly every test here), but a handful
    # force interactive=True to exercise the wizard path — this keeps
    # *those* from ever making a real network call too.
    monkeypatch.setenv("BRUPY_NO_UPDATE_CHECK", "1")
