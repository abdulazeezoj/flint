import io
import json
import time

import pytest

from brupy import __version__, updatecheck


def _fake_response(payload: dict):
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return _Resp(json.dumps(payload).encode("utf-8"))


def _allow_network(monkeypatch):
    # The autouse fixture in conftest.py sets this globally so the rest
    # of the suite never makes a real network call — these tests are
    # the deliberate exception, and mock urlopen instead of ever
    # actually reaching pypi.org. Also clear CI: GitHub Actions (and
    # most other CI providers) sets this env var for every job, which
    # would otherwise make check_for_update's own CI opt-out short-
    # circuit these tests before urlopen is ever mocked-in.
    monkeypatch.delenv("BRUPY_NO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("CI", raising=False)


def test_noninteractive_never_checks(monkeypatch):
    _allow_network(monkeypatch)
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should never be called")),
    )
    assert updatecheck.check_for_update(interactive=False) is None


def test_env_opt_out(monkeypatch):
    monkeypatch.setenv("BRUPY_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should never be called")),
    )
    assert updatecheck.check_for_update(interactive=True) is None


def test_ci_env_opt_out(monkeypatch):
    _allow_network(monkeypatch)
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should never be called")),
    )
    assert updatecheck.check_for_update(interactive=True) is None


def test_newer_version_available(monkeypatch):
    _allow_network(monkeypatch)
    major, minor, patch = updatecheck._parse_version(__version__)
    newer = f"{major}.{minor}.{patch + 1}"
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: _fake_response({"info": {"version": newer}}),
    )

    assert updatecheck.check_for_update(interactive=True) == newer


def test_already_on_latest_returns_none(monkeypatch):
    _allow_network(monkeypatch)
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: _fake_response({"info": {"version": __version__}}),
    )

    assert updatecheck.check_for_update(interactive=True) is None


def test_network_failure_is_silent(monkeypatch):
    _allow_network(monkeypatch)

    def _raise(*a, **k):
        raise updatecheck.urllib.error.URLError("offline")

    monkeypatch.setattr(updatecheck.urllib.request, "urlopen", _raise)

    assert updatecheck.check_for_update(interactive=True) is None
    assert not updatecheck.CACHE_FILE.exists()


def test_cache_avoids_refetch_within_interval(monkeypatch):
    _allow_network(monkeypatch)
    calls = []

    def _fetch(*a, **k):
        calls.append(1)
        return _fake_response({"info": {"version": "99.0.0"}})

    monkeypatch.setattr(updatecheck.urllib.request, "urlopen", _fetch)
    first = updatecheck.check_for_update(interactive=True)
    assert first == "99.0.0"
    assert len(calls) == 1

    # A second call within the cache window must reuse the cached
    # result, not hit the network again.
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should reuse cache")),
    )
    second = updatecheck.check_for_update(interactive=True)
    assert second == "99.0.0"


def test_network_failure_falls_back_to_stale_cache(monkeypatch):
    _allow_network(monkeypatch)
    updatecheck.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    updatecheck.CACHE_FILE.write_text(
        json.dumps({"latest": "99.0.0", "checked_at": 0}), encoding="utf-8"
    )

    def _raise(*a, **k):
        raise updatecheck.urllib.error.URLError("offline")

    monkeypatch.setattr(updatecheck.urllib.request, "urlopen", _raise)

    # The cache is stale (checked_at=0) so a refetch is attempted, fails,
    # and check_for_update falls back to the last known "latest" instead
    # of treating the failed refetch as "no update info at all."
    assert updatecheck.check_for_update(interactive=True) == "99.0.0"


def test_cache_write_failure_is_silent(monkeypatch, tmp_path):
    _allow_network(monkeypatch)
    monkeypatch.setattr(updatecheck, "CACHE_FILE", tmp_path / "no" / "such" / "dir" / "f.json")
    monkeypatch.setattr(
        updatecheck.Path,
        "mkdir",
        lambda *a, **k: (_ for _ in ()).throw(OSError("read-only filesystem")),
    )
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: _fake_response({"info": {"version": "99.0.0"}}),
    )

    # A failed cache write must not stop the caller from getting the
    # freshly-fetched answer for *this* invocation.
    assert updatecheck.check_for_update(interactive=True) == "99.0.0"


def test_fresh_cache_with_no_latest_value_returns_none(monkeypatch):
    # A fresh (non-stale) cache that somehow has no "latest" entry (a
    # corrupt/hand-edited file, or a schema from some future version)
    # must not be treated as "there's an update" — and since it's
    # fresh, no refetch is attempted either.
    _allow_network(monkeypatch)
    updatecheck.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    updatecheck.CACHE_FILE.write_text(
        json.dumps({"checked_at": time.time()}), encoding="utf-8"
    )
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should reuse cache, not fetch")),
    )

    assert updatecheck.check_for_update(interactive=True) is None


def test_stale_cache_triggers_refetch(monkeypatch):
    _allow_network(monkeypatch)
    updatecheck.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    updatecheck.CACHE_FILE.write_text(
        json.dumps({"latest": "0.0.1", "checked_at": 0}), encoding="utf-8"
    )
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: _fake_response({"info": {"version": "99.0.0"}}),
    )

    assert updatecheck.check_for_update(interactive=True) == "99.0.0"


def test_corrupt_cache_is_treated_as_empty(monkeypatch):
    _allow_network(monkeypatch)
    updatecheck.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    updatecheck.CACHE_FILE.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(
        updatecheck.urllib.request,
        "urlopen",
        lambda *a, **k: _fake_response({"info": {"version": "99.0.0"}}),
    )

    assert updatecheck.check_for_update(interactive=True) == "99.0.0"


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.2.3", (1, 2, 3)),
        ("1.2.3rc1", (1, 2, 3)),
        ("2.0", (2, 0, 0)),
    ],
)
def test_parse_version(version, expected):
    assert updatecheck._parse_version(version) == expected
