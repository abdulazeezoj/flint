"""Unit tests for prefs.py — ~/.flint/last.json persistence.

The `isolated_prefs_dir` autouse fixture (tests/conftest.py) points
`prefs.PREFS_DIR`/`prefs.PREFS_FILE` at a per-test tmp path, so nothing
here touches the real user home directory.
"""

from __future__ import annotations

from flint import prefs


def test_load_prefs_missing_file_returns_empty():
    assert prefs.load_prefs() == {}


def test_save_then_load_round_trips():
    prefs.save_prefs({"last_framework": "fastapi"})
    assert prefs.load_prefs() == {"last_framework": "fastapi"}


def test_load_prefs_corrupt_json_returns_empty():
    prefs.PREFS_DIR.mkdir(parents=True, exist_ok=True)
    prefs.PREFS_FILE.write_text("not json", encoding="utf-8")
    assert prefs.load_prefs() == {}


def test_load_prefs_non_object_json_returns_empty():
    prefs.PREFS_DIR.mkdir(parents=True, exist_ok=True)
    prefs.PREFS_FILE.write_text("[1, 2, 3]", encoding="utf-8")
    assert prefs.load_prefs() == {}


class _UnwritableDir:
    def mkdir(self, *args, **kwargs):
        raise OSError("read-only filesystem")


def test_save_prefs_unwritable_dir_does_not_raise(monkeypatch):
    monkeypatch.setattr(prefs, "PREFS_DIR", _UnwritableDir())
    prefs.save_prefs({"last_framework": "fastapi"})  # must not raise
    assert not prefs.PREFS_FILE.exists()


def test_get_last_framework_absent():
    assert prefs.get_last_framework({}) is None


def test_get_last_framework_wrong_type_ignored():
    assert prefs.get_last_framework({"last_framework": 123}) is None


def test_get_last_framework_present():
    assert prefs.get_last_framework({"last_framework": "fastapi"}) == "fastapi"


def test_get_last_template_absent():
    assert prefs.get_last_template({}, "fastapi") is None


def test_get_last_template_wrong_container_type_ignored():
    assert prefs.get_last_template({"last_templates": "oops"}, "fastapi") is None


def test_get_last_template_wrong_value_type_ignored():
    assert prefs.get_last_template({"last_templates": {"fastapi": 5}}, "fastapi") is None


def test_get_last_template_present():
    prefs_data = {"last_templates": {"fastapi": "rest-api"}}
    assert prefs.get_last_template(prefs_data, "fastapi") == "rest-api"


def test_get_last_template_different_framework_not_found():
    prefs_data = {"last_templates": {"fastapi": "rest-api"}}
    assert prefs.get_last_template(prefs_data, "flask") is None


def test_get_template_prefs_absent_returns_defaults():
    assert prefs.get_template_prefs({}, "fastapi/rest-api") == {
        "options": {},
        "docker": None,
        "compose": None,
        "git_init": None,
        "install": None,
    }


def test_get_template_prefs_wrong_container_type_ignored():
    result = prefs.get_template_prefs({"templates": "oops"}, "fastapi/rest-api")
    assert result == {
        "options": {},
        "docker": None,
        "compose": None,
        "git_init": None,
        "install": None,
    }


def test_get_template_prefs_wrong_entry_type_ignored():
    result = prefs.get_template_prefs(
        {"templates": {"fastapi/rest-api": "oops"}}, "fastapi/rest-api"
    )
    assert result == {
        "options": {},
        "docker": None,
        "compose": None,
        "git_init": None,
        "install": None,
    }


def test_get_template_prefs_present():
    prefs_data = {
        "templates": {
            "fastapi/rest-api": {
                "options": {"database": "postgres"},
                "docker": True,
                "compose": True,
                "git_init": False,
                "install": True,
            }
        }
    }
    assert prefs.get_template_prefs(prefs_data, "fastapi/rest-api") == {
        "options": {"database": "postgres"},
        "docker": True,
        "compose": True,
        "git_init": False,
        "install": True,
    }


def test_get_template_prefs_non_bool_flags_ignored():
    prefs_data = {
        "templates": {
            "fastapi/rest-api": {
                "options": {},
                "docker": "yes",
                "compose": 1,
                "git_init": 1,
                "install": None,
            }
        }
    }
    assert prefs.get_template_prefs(prefs_data, "fastapi/rest-api") == {
        "options": {},
        "docker": None,
        "compose": None,
        "git_init": None,
        "install": None,
    }


def test_get_template_prefs_non_dict_options_ignored():
    prefs_data = {"templates": {"fastapi/rest-api": {"options": "oops"}}}
    result = prefs.get_template_prefs(prefs_data, "fastapi/rest-api")
    assert result["options"] == {}


def test_record_run_from_empty():
    updated = prefs.record_run(
        {},
        framework_id="fastapi",
        template_id="rest-api",
        full_id="fastapi/rest-api",
        options={"database": "postgres"},
        docker=True,
        compose=True,
        git_init=False,
        install=True,
    )
    assert updated == {
        "last_framework": "fastapi",
        "last_templates": {"fastapi": "rest-api"},
        "templates": {
            "fastapi/rest-api": {
                "options": {"database": "postgres"},
                "docker": True,
                "compose": True,
                "git_init": False,
                "install": True,
            }
        },
    }


def test_record_run_preserves_other_frameworks_and_templates():
    existing = {
        "last_framework": "fastapi",
        "last_templates": {"fastapi": "hello-world"},
        "templates": {
            "fastapi/hello-world": {
                "options": {"config": True},
                "docker": False,
                "compose": False,
                "git_init": True,
                "install": True,
            }
        },
    }
    updated = prefs.record_run(
        existing,
        framework_id="fastapi",
        template_id="rest-api",
        full_id="fastapi/rest-api",
        options={"database": "sqlite"},
        docker=False,
        compose=False,
        git_init=True,
        install=True,
    )
    assert updated["last_templates"] == {"fastapi": "rest-api"}
    assert updated["templates"]["fastapi/hello-world"] == existing["templates"][
        "fastapi/hello-world"
    ]
    assert updated["templates"]["fastapi/rest-api"]["options"] == {"database": "sqlite"}


def test_record_run_does_not_mutate_input():
    existing = {"last_templates": {"fastapi": "hello-world"}, "templates": {}}
    prefs.record_run(
        existing,
        framework_id="fastapi",
        template_id="rest-api",
        full_id="fastapi/rest-api",
        options={},
        docker=False,
        compose=False,
        git_init=True,
        install=True,
    )
    assert existing["last_templates"] == {"fastapi": "hello-world"}
    assert existing["templates"] == {}
