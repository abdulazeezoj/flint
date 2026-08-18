import ast
import json
import tomllib
from pathlib import Path

import pytest

import brupy.generator as generator_module
from brupy.errors import BrupyError, BrupyUserError
from brupy.generator import (
    Answers,
    get_framework,
    get_skill,
    get_template,
    list_frameworks,
    list_templates,
    render,
    when_matches,
)


def make_answers(**overrides) -> Answers:
    defaults = dict(
        project_name="My Api",
        slug="my-api",
        package_name="my_api",
        framework="fastapi",
        template="hello-world",
        git_init=False,
        install=False,
        docker=False,
    )
    defaults.update(overrides)
    return Answers(**defaults)


def _assert_all_python_files_parse(target: Path) -> None:
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assert_valid_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


class TestWhenMatches:
    def test_empty_when_always_matches(self):
        assert when_matches({}, {}) is True
        assert when_matches({}, {"anything": "x"}) is True

    def test_single_key_match(self):
        assert when_matches({"worker": ["none"]}, {"worker": "none"}) is True
        assert when_matches({"worker": ["none"]}, {"worker": "celery"}) is False

    def test_multiple_keys_require_all(self):
        when = {"orm": ["sqlmodel"], "migrations": [True]}
        assert when_matches(when, {"orm": "sqlmodel", "migrations": True}) is True
        assert when_matches(when, {"orm": "sqlmodel", "migrations": False}) is False
        assert when_matches(when, {"orm": "sqlalchemy", "migrations": True}) is False

    def test_missing_key_does_not_match(self):
        assert when_matches({"worker": ["none"]}, {}) is False


def test_list_frameworks_includes_fastapi():
    frameworks = list_frameworks()
    ids = {f.id for f in frameworks}
    assert "fastapi" in ids


def test_get_framework_unknown_raises():
    with pytest.raises(BrupyUserError):
        get_framework("does-not-exist")


def test_list_templates_includes_hello_world_and_rest_api():
    templates = list_templates("fastapi")
    ids = {t.id for t in templates}
    assert {"hello-world", "rest-api"} <= ids


def test_get_template_unknown_raises():
    with pytest.raises(BrupyUserError):
        get_template("fastapi", "does-not-exist")


def test_get_template_full_id_and_docker_support():
    template = get_template("fastapi", "hello-world")
    assert template.full_id == "fastapi/hello-world"
    assert template.supports_docker is True


def test_hello_world_declares_config_option():
    template = get_template("fastapi", "hello-world")
    assert [o.key for o in template.options] == ["config"]
    assert template.options[0].type == "confirm"
    assert template.options[0].default is False


def test_rest_api_declares_expected_options_and_layers():
    template = get_template("fastapi", "rest-api")
    option_keys = [o.key for o in template.options]
    assert option_keys == ["database", "orm", "migrations", "worker", "broker", "redis"]

    layer_dirs = {layer.dir for layer in template.layers}
    assert layer_dirs == {
        "docker",
        "db-sqlmodel",
        "db-sqlalchemy",
        "migrations-sqlmodel",
        "migrations-sqlalchemy",
        "worker-taskiq",
        "worker-celery",
        "redis",
    }


def test_render_creates_expected_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    # Project files proper — a subset check, not exact equality, since
    # hello-world also always pulls in the fastapi/pytest skills (see
    # TestSkillsMechanism and test_render_includes_expected_skills below
    # for dedicated coverage of *that* file set).
    expected = {
        Path("pyproject.toml"),
        Path("README.md"),
        Path("AGENTS.md"),
        Path(".gitignore"),
        Path("src/my_api/__init__.py"),
        Path("src/my_api/main.py"),
        Path("tests/test_main.py"),
    }
    assert expected <= set(created)
    for rel_path in expected:
        assert (target / rel_path).is_file()


def test_render_includes_expected_skills(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    skill_paths = {p for p in created if p.parts[:2] == (".agents", "skills")}
    assert skill_paths == {
        Path(".agents/skills/README.md"),
        Path(".agents/skills/fastapi/SKILL.md"),
        Path(".agents/skills/fastapi/guides/add-an-endpoint.md"),
        Path(".agents/skills/fastapi/guides/testing.md"),
        Path(".agents/skills/fastapi/references/gotchas.md"),
        Path(".agents/skills/fastapi/references/routing-and-dependencies.md"),
        Path(".agents/skills/pytest/SKILL.md"),
        Path(".agents/skills/pytest/guides/parametrize.md"),
        Path(".agents/skills/pytest/guides/writing-a-good-test.md"),
        Path(".agents/skills/pytest/references/database-isolation.md"),
        Path(".agents/skills/pytest/references/gotchas.md"),
    }
    # pydantic-settings is only pulled in when config=true (make_answers()
    # defaults to no options at all, i.e. config unset/false).
    assert not (target / ".agents/skills/pydantic-settings").exists()


def test_render_writes_claude_md_pointing_at_agents_md(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    assert Path("CLAUDE.md") in created
    assert (target / "CLAUDE.md").read_text(encoding="utf-8") == "@AGENTS.md\n"


def test_render_symlinks_claude_skills_to_agents_skills(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    assert Path(".claude/skills/fastapi") in created
    assert Path(".claude/skills/pytest") in created
    link = target / ".claude/skills/fastapi"
    assert link.is_symlink()
    assert link.resolve() == (target / ".agents/skills/fastapi").resolve()


def test_render_force_leaves_unrelated_claude_skills_content_alone(tmp_path: Path):
    # Regression test: render(..., force=True) regenerating into an
    # existing project directory must not silently delete real content
    # a user happens to have at .claude/skills/<id> for an id that also
    # matches one of this template's skills.
    target = tmp_path / "my-api"
    real_dir = target / ".claude" / "skills" / "fastapi"
    real_dir.mkdir(parents=True)
    (real_dir / "my_real_notes.md").write_text("not brupy's to delete")

    render("fastapi", "hello-world", target, make_answers(), force=True)

    assert (real_dir / "my_real_notes.md").read_text() == "not brupy's to delete"


def test_render_skips_claude_skill_symlinks_it_cannot_create(tmp_path: Path, monkeypatch):
    # Mirrors prefs.py's best-effort philosophy: a platform that refuses
    # symlink creation without elevated privileges (Windows without
    # Developer Mode, some restricted filesystems) must not break
    # generation — it just doesn't get the .claude/skills/ mirror, and the
    # real .agents/skills/ catalog is unaffected either way.
    monkeypatch.setattr(
        generator_module.os,
        "symlink",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no symlink permission")),
    )
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers())

    assert not any(p.parts[:2] == (".claude", "skills") for p in created)
    assert (target / ".agents/skills/fastapi/SKILL.md").is_file()


def test_write_claude_skill_symlink_default_leaves_existing_content_alone(tmp_path: Path):
    # Per-project generation (_write_claude_skill_symlinks) calls this
    # without replace_existing, and relies on the resulting OSError to
    # skip the symlink rather than clobber whatever's already there —
    # render(..., force=True) only overwrites files it's actually
    # rendering, never arbitrary pre-existing content under
    # .claude/skills/. Regression test: this used to unconditionally
    # rmtree a real directory before creating the symlink.
    claude_skills_dir = tmp_path / ".claude" / "skills"
    real_dir = claude_skills_dir / "fastapi"
    real_dir.mkdir(parents=True)
    (real_dir / "my_real_notes.md").write_text("not brupy's to delete")

    with pytest.raises(OSError):
        generator_module.write_claude_skill_symlink(claude_skills_dir, "fastapi")

    assert (real_dir / "my_real_notes.md").read_text() == "not brupy's to delete"


def test_write_claude_skill_symlink_replace_existing_replaces_real_directory(tmp_path: Path):
    # write_claude_skill_symlink is shared with skillinstall.install() —
    # with replace_existing=True (what skillinstall.install() passes,
    # after its own explicit --force/exists checks), it must replace
    # whatever's already at link_path, including a real directory left
    # over from something else, not just a stale symlink.
    claude_skills_dir = tmp_path / ".claude" / "skills"
    stale_dir = claude_skills_dir / "fastapi"
    stale_dir.mkdir(parents=True)
    (stale_dir / "leftover.md").write_text("stale")

    generator_module.write_claude_skill_symlink(
        claude_skills_dir, "fastapi", replace_existing=True
    )

    link = claude_skills_dir / "fastapi"
    assert link.is_symlink()
    assert link.resolve() == (tmp_path / ".agents" / "skills" / "fastapi").resolve()


def test_render_with_docker_adds_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers(docker=True))

    assert Path("Dockerfile") in created
    assert Path(".dockerignore") in created
    dockerfile = (target / "Dockerfile").read_text()
    assert "src/my_api/main.py" in dockerfile

    readme = (target / "README.md").read_text()
    assert "docker build -t my-api ." in readme


def test_render_without_docker_omits_dockerfile(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render("fastapi", "hello-world", target, make_answers(docker=False))

    assert Path("Dockerfile") not in created
    assert not (target / "Dockerfile").exists()
    assert "docker build" not in (target / "README.md").read_text()


def test_render_substitutes_package_name(tmp_path: Path):
    target = tmp_path / "my-api"
    render("fastapi", "hello-world", target, make_answers())

    main_py = (target / "src/my_api/main.py").read_text()
    assert 'FastAPI(title="My Api")' in main_py

    test_py = (target / "tests/test_main.py").read_text()
    assert "from my_api.main import app" in test_py

    readme = (target / "README.md").read_text()
    assert "My Api" in readme
    assert "src/my_api/main.py" in readme

    agents_md = (target / "AGENTS.md").read_text()
    assert "my_api" in agents_md


def test_render_hello_world_with_config_option(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "fastapi", "hello-world", target, make_answers(options={"config": True})
    )

    assert Path("src/my_api/core/config.py") in created
    assert Path(".env") in created
    assert Path(".env.example") in created
    assert (target / ".env").read_text() == (target / ".env.example").read_text()
    main_py = (target / "src/my_api/main.py").read_text()
    assert "from my_api.core.config import settings" in main_py
    _assert_all_python_files_parse(target)


def test_render_hello_world_without_config_option_omits_config_files(tmp_path: Path):
    target = tmp_path / "my-api"
    created = render(
        "fastapi", "hello-world", target, make_answers(options={"config": False})
    )

    assert Path("src/my_api/core/config.py") not in created
    assert Path(".env") not in created
    assert Path(".env.example") not in created


def test_render_refuses_nonempty_directory_without_force(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    with pytest.raises(BrupyUserError):
        render("fastapi", "hello-world", target, make_answers())


def test_render_force_overwrites_nonempty_directory(tmp_path: Path):
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "existing.txt").write_text("hello")

    created = render("fastapi", "hello-world", target, make_answers(), force=True)
    assert (target / "pyproject.toml").is_file()
    assert len(created) == 21  # 7 project files + 11 fastapi/pytest skill files + CLAUDE.md + 2 .claude/skills symlinks


def test_render_disabled_template_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    _write_meta(tmp_path / "widget" / "basic", "basic", enabled=False)

    with pytest.raises(BrupyUserError):
        render(
            "widget",
            "basic",
            tmp_path / "out",
            make_answers(framework="widget", template="basic"),
        )


def test_render_disabled_framework_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget", enabled=False)
    _write_meta(tmp_path / "widget" / "basic", "basic")

    with pytest.raises(BrupyUserError):
        render(
            "widget",
            "basic",
            tmp_path / "x",
            make_answers(framework="widget", template="basic"),
        )


def test_render_rolls_back_on_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "my-api"

    original_render_content = generator_module._render_content
    calls = {"count": 0}

    def flaky_render_content(source_path, context):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("boom")
        return original_render_content(source_path, context)

    monkeypatch.setattr(generator_module, "_render_content", flaky_render_content)

    with pytest.raises(BrupyError):
        render("fastapi", "hello-world", target, make_answers())

    assert not target.exists()


def test_render_unknown_template_raises(tmp_path: Path):
    with pytest.raises(BrupyUserError):
        render("fastapi", "does-not-exist", tmp_path / "x", make_answers())


def test_render_propagates_brupy_error_without_wrapping_but_still_rolls_back(
    tmp_path: Path, monkeypatch
):
    # A BrupyError raised mid-render (e.g. surfaced from a future layer
    # hook) should pass through unchanged rather than being wrapped in
    # the generic "Failed to generate project" message — but generation
    # is still all-or-nothing, so the partial directory must be rolled
    # back just like for any other exception.
    target = tmp_path / "my-api"

    def raise_user_error(layer_root, target_dir, context):
        raise BrupyUserError("deliberate")

    monkeypatch.setattr(generator_module, "_render_layer", raise_user_error)

    with pytest.raises(BrupyUserError, match="deliberate"):
        render("fastapi", "hello-world", target, make_answers())

    assert not target.exists()


def test_render_content_copies_non_jinja_files_verbatim(tmp_path: Path):
    source = tmp_path / "static.txt"
    source.write_text("{{ not_rendered }}", encoding="utf-8")

    result = generator_module._render_content(source, {"not_rendered": "should not appear"})

    assert result == "{{ not_rendered }}"


def _write_meta(directory: Path, id_: str, enabled: bool = True) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "template.json").write_text(
        json.dumps({"id": id_, "label": id_.title(), "description": "d", "enabled": enabled})
    )


def test_list_frameworks_skips_entries_without_template_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    (tmp_path / "stray.txt").write_text("not a framework")

    frameworks = generator_module.list_frameworks()
    assert [f.id for f in frameworks] == ["widget"]


def test_list_templates_skips_subdirs_without_template_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    _write_meta(tmp_path / "widget", "widget")
    _write_meta(tmp_path / "widget" / "basic", "basic")
    (tmp_path / "widget" / "docs").mkdir()  # a dir with no template.json

    templates = generator_module.list_templates("widget")
    assert [t.id for t in templates] == ["basic"]


def test_render_does_not_delete_preexisting_directory_on_failure(tmp_path: Path, monkeypatch):
    # created_before=True (the target dir existed before this render call,
    # e.g. a --force run) must never be cleaned up on failure — only
    # directories brupy itself created get rolled back.
    target = tmp_path / "my-api"
    target.mkdir()
    (target / "keepme.txt").write_text("do not delete")

    def raise_error(layer_root, target_dir, context):
        raise BrupyUserError("deliberate")

    monkeypatch.setattr(generator_module, "_render_layer", raise_error)

    with pytest.raises(BrupyUserError):
        render("fastapi", "hello-world", target, make_answers(), force=True)

    assert target.exists()
    assert (target / "keepme.txt").read_text() == "do not delete"


# --- rest-api: the options/layers engine exercised through a real template ---


def make_rest_api_answers(**option_overrides) -> Answers:
    options = dict(
        database="sqlite", orm="sqlmodel", migrations=True, worker="none", redis=False
    )
    options.update(option_overrides)
    return make_answers(template="rest-api", options=options)


def test_rest_api_in_memory_default(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(database="none", orm="none", migrations=False)
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/routes/items.py") in created
    assert Path("src/my_api/core/db.py") not in created
    assert Path("alembic.ini") not in created
    routes = (target / "src/my_api/routes/items.py").read_text()
    assert "_items" in routes  # the in-memory store
    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_rest_api_sqlite_sqlmodel_with_migrations(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers()  # sqlite + sqlmodel + migrations=True
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/core/db.py") in created
    assert Path("src/my_api/models.py") in created
    assert Path("alembic.ini") in created
    assert Path("alembic/env.py") in created
    assert Path("alembic/script.py.mako") in created
    assert Path("alembic/versions/.gitkeep") in created

    routes = (target / "src/my_api/routes/items.py").read_text()
    assert "get_session" in routes
    assert "sqlmodel" in (target / "src/my_api/core/db.py").read_text()

    env_py = (target / "alembic/env.py").read_text()
    assert "SQLModel.metadata" in env_py

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "sqlmodel>=0.0.22" in config["project"]["dependencies"]
    assert "alembic>=1.14.0" in config["project"]["dependencies"]


def test_rest_api_postgres_sqlalchemy_no_migrations(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(database="postgres", orm="sqlalchemy", migrations=False)
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/core/db.py") in created
    assert Path("alembic.ini") not in created

    session_py = (target / "src/my_api/core/db.py").read_text()
    assert "sqlalchemy" in session_py.lower()
    env_file = (target / ".env").read_text()
    assert "postgresql+asyncpg://" in env_file
    assert (target / ".env.example").read_text() == env_file

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "asyncpg>=0.30.0" in config["project"]["dependencies"]
    assert "sqlalchemy>=2.0.36" in config["project"]["dependencies"]
    assert not any("alembic" in dep for dep in config["project"]["dependencies"])


def test_rest_api_worker_taskiq_implies_redis(tmp_path: Path):
    # Whether a worker choice *implies* redis (skip_value resolution) is a
    # prompts.py concern (see test_prompts.py) — render() just applies
    # whatever options dict it's given, which here already has redis=True
    # to simulate what prompts.prompt_template_options would have resolved.
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="none", orm="none", migrations=False, worker="taskiq", redis=True
    )
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/worker.py") in created
    assert Path("src/my_api/tasks/example.py") in created
    assert Path("src/my_api/core/redis.py") in created

    main_py = (target / "src/my_api/main.py").read_text()
    assert "lifespan" in main_py
    assert "/tasks/add" in main_py
    _assert_all_python_files_parse(target)


def test_rest_api_worker_celery(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(database="none", orm="none", migrations=False, worker="celery")
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/worker.py") in created
    worker_py = (target / "src/my_api/worker.py").read_text()
    assert "Celery(" in worker_py
    main_py = (target / "src/my_api/main.py").read_text()
    assert "add.delay" in main_py
    _assert_all_python_files_parse(target)


def test_rest_api_redis_standalone_toggle(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="none", orm="none", migrations=False, worker="none", redis=True
    )
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/core/redis.py") in created
    assert Path("src/my_api/worker.py") not in created


def test_rest_api_all_features_combined(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="postgres",
        orm="sqlalchemy",
        migrations=True,
        worker="celery",
        broker="redis",
        redis=True,
    )
    created = render("fastapi", "rest-api", target, answers, force=True)

    for expected in [
        "src/my_api/core/db.py",
        "src/my_api/models.py",
        "alembic.ini",
        "src/my_api/worker.py",
        "src/my_api/tasks/example.py",
        "src/my_api/core/redis.py",
    ]:
        assert Path(expected) in created, expected

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_rest_api_worker_taskiq_rabbitmq_broker(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="none",
        orm="none",
        migrations=False,
        worker="taskiq",
        broker="rabbitmq",
        redis=False,
    )
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/worker.py") in created
    assert Path("src/my_api/core/redis.py") not in created  # not implied by rabbitmq

    worker_py = (target / "src/my_api/worker.py").read_text()
    assert "AioPikaBroker" in worker_py
    assert "taskiq_redis" not in worker_py

    env_file = (target / ".env").read_text()
    assert "RABBITMQ_URL=amqp://" in env_file
    assert "REDIS_URL" not in env_file

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "taskiq-aio-pika>=0.5.0" in config["project"]["dependencies"]
    assert not any(dep.startswith("taskiq-redis") for dep in config["project"]["dependencies"])


def test_rest_api_worker_celery_rabbitmq_broker(tmp_path: Path):
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="none",
        orm="none",
        migrations=False,
        worker="celery",
        broker="rabbitmq",
        redis=False,
    )
    created = render("fastapi", "rest-api", target, answers)

    worker_py = (target / "src/my_api/worker.py").read_text()
    assert 'broker=settings.rabbitmq_url, backend="rpc://"' in worker_py

    env_file = (target / ".env").read_text()
    assert "RABBITMQ_URL=amqp://" in env_file
    assert "REDIS_URL" not in env_file
    _assert_all_python_files_parse(target)


def test_rest_api_rabbitmq_broker_with_redis_caching_still_independent(tmp_path: Path):
    # broker=rabbitmq and redis=True (caching) aren't mutually exclusive —
    # this is exactly the decoupling the `broker` option exists for.
    target = tmp_path / "api"
    answers = make_rest_api_answers(
        database="none",
        orm="none",
        migrations=False,
        worker="taskiq",
        broker="rabbitmq",
        redis=True,
    )
    created = render("fastapi", "rest-api", target, answers)

    assert Path("src/my_api/core/redis.py") in created
    env_file = (target / ".env").read_text()
    assert "RABBITMQ_URL=amqp://" in env_file
    assert "REDIS_URL=redis://" in env_file


def _skill_ids(created: list[Path]) -> set[str]:
    # .agents/skills/README.md is the generated index, not a skill id.
    return {
        p.parts[2]
        for p in created
        if p.parts[:2] == (".agents", "skills") and len(p.parts) > 3
    }


class TestFastapiRestApiSkills:
    def test_sqlmodel_with_migrations(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers()  # sqlite + sqlmodel + migrations=True
        created = render("fastapi", "rest-api", target, answers)

        assert _skill_ids(created) == {
            "fastapi",
            "pydantic-settings",
            "pytest",
            "sqlmodel",
            "alembic",
        }
        assert Path(".agents/skills/README.md") in created

    def test_sqlalchemy_no_migrations(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="postgres", orm="sqlalchemy", migrations=False)
        created = render("fastapi", "rest-api", target, answers)

        assert _skill_ids(created) == {"fastapi", "pydantic-settings", "pytest", "sqlalchemy"}

    def test_no_database_no_worker_no_redis(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(database="none", orm="none", migrations=False)
        created = render("fastapi", "rest-api", target, answers)

        assert _skill_ids(created) == {"fastapi", "pydantic-settings", "pytest"}

    def test_taskiq_worker_implies_redis_skill(self, tmp_path: Path):
        # redis=True here simulates what prompts.prompt_template_options
        # would already have resolved via skip_value (see
        # test_rest_api_worker_taskiq_implies_redis above) — render() just
        # applies whatever options dict it's given.
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none", orm="none", migrations=False, worker="taskiq", redis=True,
        )
        created = render("fastapi", "rest-api", target, answers)

        assert _skill_ids(created) == {
            "fastapi", "pydantic-settings", "pytest", "taskiq", "redis",
        }

    def test_celery_worker_rabbitmq_broker_no_redis(self, tmp_path: Path):
        target = tmp_path / "api"
        answers = make_rest_api_answers(
            database="none", orm="none", migrations=False,
            worker="celery", broker="rabbitmq", redis=False,
        )
        created = render("fastapi", "rest-api", target, answers)

        assert _skill_ids(created) == {"fastapi", "pydantic-settings", "pytest", "celery"}


def make_full_stack_answers(**option_overrides) -> Answers:
    options = dict(
        database="sqlite", orm="sqlmodel", migrations=True, worker="none", redis=False,
        css="vanilla",
    )
    options.update(option_overrides)
    return make_answers(template="full-stack", options=options)


def test_full_stack_in_memory_default(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(database="none", orm="none", migrations=False)
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/routes/todos.py") in created
    assert Path("src/my_api/templates/index.html") in created
    assert Path("src/my_api/templates/base.html") in created
    assert Path("src/my_api/templates/partials/todo_item.html") in created
    assert Path("src/my_api/static/css/style.css") in created
    assert Path("src/my_api/core/db.py") not in created
    assert Path("alembic.ini") not in created
    routes = (target / "src/my_api/routes/todos.py").read_text()
    assert "_todos" in routes  # the in-memory store
    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_full_stack_sqlite_sqlmodel_with_migrations(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers()  # sqlite + sqlmodel + migrations=True
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/core/db.py") in created
    assert Path("src/my_api/models.py") in created
    assert Path("alembic.ini") in created
    assert Path("alembic/env.py") in created

    routes = (target / "src/my_api/routes/todos.py").read_text()
    assert "get_session" in routes
    models_py = (target / "src/my_api/models.py").read_text()
    assert "class Todo" in models_py

    env_py = (target / "alembic/env.py").read_text()
    assert "Todo" in env_py
    assert "Item" not in env_py

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "sqlmodel>=0.0.22" in config["project"]["dependencies"]


def test_full_stack_postgres_sqlalchemy_no_migrations(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(database="postgres", orm="sqlalchemy", migrations=False)
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/core/db.py") in created
    assert Path("alembic.ini") not in created

    models_py = (target / "src/my_api/models.py").read_text()
    assert "class Todo(Base)" in models_py
    env_file = (target / ".env").read_text()
    assert "postgresql+asyncpg://" in env_file

    _assert_all_python_files_parse(target)
    config = _assert_valid_toml(target / "pyproject.toml")
    assert "asyncpg>=0.30.0" in config["project"]["dependencies"]
    assert not any("alembic" in dep for dep in config["project"]["dependencies"])


def test_full_stack_worker_taskiq_implies_redis(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(
        database="none", orm="none", migrations=False, worker="taskiq", redis=True
    )
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/worker.py") in created
    assert Path("src/my_api/tasks/example.py") in created
    assert Path("src/my_api/core/redis.py") in created

    main_py = (target / "src/my_api/main.py").read_text()
    assert "lifespan" in main_py
    assert "/tasks/add" in main_py
    assert "StaticFiles" in main_py
    _assert_all_python_files_parse(target)


def test_full_stack_worker_celery(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(
        database="none", orm="none", migrations=False, worker="celery"
    )
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/worker.py") in created
    worker_py = (target / "src/my_api/worker.py").read_text()
    assert "Celery(" in worker_py
    main_py = (target / "src/my_api/main.py").read_text()
    assert "add.delay" in main_py
    _assert_all_python_files_parse(target)


def test_full_stack_all_features_combined(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(
        database="postgres",
        orm="sqlalchemy",
        migrations=True,
        worker="celery",
        broker="redis",
        redis=True,
    )
    created = render("fastapi", "full-stack", target, answers, force=True)

    for expected in [
        "src/my_api/core/db.py",
        "src/my_api/models.py",
        "alembic.ini",
        "src/my_api/worker.py",
        "src/my_api/tasks/example.py",
        "src/my_api/core/redis.py",
        "src/my_api/templates/index.html",
        "src/my_api/static/css/style.css",
    ]:
        assert Path(expected) in created, expected

    _assert_all_python_files_parse(target)
    _assert_valid_toml(target / "pyproject.toml")


def test_full_stack_no_leftover_jinja_in_runtime_templates(tmp_path: Path):
    # The templates/ and static/ files carry the *generated app's own*
    # runtime Jinja2 syntax ({% block %}, {{ todo.title }}) and must NOT
    # be rendered by brupy's own generator — they have no .jinja suffix
    # specifically so they're copied verbatim (see fastapi/full-stack's
    # README.md gotcha #1). This asserts that syntax survives untouched.
    target = tmp_path / "app"
    answers = make_full_stack_answers()
    render("fastapi", "full-stack", target, answers)

    index_html = (target / "src/my_api/templates/index.html").read_text()
    assert "{% for todo in todos %}" in index_html
    assert "{% include" in index_html

    todo_item_html = (target / "src/my_api/templates/partials/todo_item.html").read_text()
    assert "{{ todo.title }}" in todo_item_html
    assert "{{ todo.id }}" in todo_item_html

    # Everything else must be fully resolved — no leftover brupy-level
    # or app-level Jinja outside templates/. .agents/skills/ is exempt:
    # the jinja2/htmx skills legitimately document literal {{ }}/{% %}
    # syntax as prose (escaped via {% raw %} at generation time), which
    # isn't the same thing as unrendered brupy-level Jinja leaking out.
    for path in target.rglob("*"):
        if path.is_dir() or "templates" in path.parts or ".agents/skills" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "{{" not in text, path
        assert "{%" not in text, path


def test_full_stack_css_vanilla_is_default(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers()  # css="vanilla" by default
    created = render("fastapi", "full-stack", target, answers)

    assert Path("src/my_api/static/css/style.css") in created
    assert Path("src/my_api/static/css/input.css") not in created
    config = _assert_valid_toml(target / "pyproject.toml")
    assert not any("pytailwindcss" in dep for dep in config["project"]["dependencies"])


def test_full_stack_css_tailwind(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(css="tailwind")
    created = render("fastapi", "full-stack", target, answers)

    # input.css (source, tracked) ships; style.css (build output) does not —
    # it's produced by the Tailwind CLI, not by brupy (see README.md's
    # "no .jinja suffix" gotcha and the Styling section it points to).
    assert Path("src/my_api/static/css/input.css") in created
    assert Path("src/my_api/static/css/style.css") not in created

    input_css = (target / "src/my_api/static/css/input.css").read_text()
    assert '@import "tailwindcss"' in input_css
    assert '@plugin "daisyui"' in input_css

    index_html = (target / "src/my_api/templates/index.html").read_text()
    assert "btn-primary" in index_html  # daisyUI component classes, not vanilla CSS

    config = _assert_valid_toml(target / "pyproject.toml")
    assert not any("pytailwindcss" in dep for dep in config["project"]["dependencies"])

    package_json = json.loads((target / "package.json").read_text())
    assert "tailwindcss" in package_json["devDependencies"]
    assert "daisyui" in package_json["devDependencies"]

    assert Path("dev.py") in created
    dev_py = (target / "dev.py").read_text()
    assert "fastapi" in dev_py
    assert "bun" in dev_py

    gitignore = (target / ".gitignore").read_text()
    assert "static/css/style.css" in gitignore
    assert "node_modules/" in gitignore

    _assert_all_python_files_parse(target)


def test_full_stack_css_tailwind_docker_build_step(tmp_path: Path):
    target = tmp_path / "app"
    answers = make_full_stack_answers(css="tailwind").model_copy(update={"docker": True})
    created = render("fastapi", "full-stack", target, answers, force=True)

    assert Path("Dockerfile") in created
    dockerfile = (target / "Dockerfile").read_text()
    assert "FROM oven/bun:1 AS css-builder" in dockerfile
    assert "bun run build:css" in dockerfile
    assert "COPY --from=css-builder" in dockerfile


class TestFastapiFullStackSkills:
    def test_sqlmodel_with_migrations(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers()  # sqlite + sqlmodel + migrations=True
        created = render("fastapi", "full-stack", target, answers)

        assert _skill_ids(created) == {
            "fastapi",
            "pydantic-settings",
            "pytest",
            "jinja2",
            "htmx",
            "sqlmodel",
            "alembic",
        }

    def test_no_database_no_worker_no_redis(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(database="none", orm="none", migrations=False)
        created = render("fastapi", "full-stack", target, answers)

        assert _skill_ids(created) == {"fastapi", "pydantic-settings", "pytest", "jinja2", "htmx"}

    def test_css_tailwind_adds_tailwind_skill(self, tmp_path: Path):
        target = tmp_path / "app"
        answers = make_full_stack_answers(
            database="none", orm="none", migrations=False, css="tailwind"
        )
        created = render("fastapi", "full-stack", target, answers)

        assert _skill_ids(created) == {
            "fastapi",
            "pydantic-settings",
            "pytest",
            "jinja2",
            "htmx",
            "tailwind",
        }


def test_render_skips_declared_layer_with_missing_directory(tmp_path: Path, monkeypatch):
    # A layer can be declared in template.json with a `when` that matches
    # but have no directory on disk (e.g. a template-authoring slip) —
    # render() skips it rather than failing generation over an unshipped
    # extra.
    monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
    framework_dir = tmp_path / "widget"
    _write_meta(framework_dir, "widget")
    template_dir = framework_dir / "basic"
    (template_dir / "files").mkdir(parents=True)
    (template_dir / "files" / "README.md").write_text("hello")
    (template_dir / "template.json").write_text(
        json.dumps(
            {
                "id": "basic",
                "label": "Basic",
                "description": "d",
                "enabled": True,
                "layers": [{"dir": "docker", "when": {"docker": [True]}}],
            }
        )
    )

    target = tmp_path / "out"
    created = render(
        "widget", "basic", target, make_answers(framework="widget", template="basic", docker=True)
    )

    # AGENTS.md was never generated by this fixture template (only
    # README.md), so CLAUDE.md — a one-line pointer at AGENTS.md — must
    # not be written either; a dangling @AGENTS.md import would be worse
    # than no CLAUDE.md at all.
    assert created == [Path("README.md")]


def _write_skill(skills_root: Path, skill_id: str, label: str = "Widget Skill") -> None:
    skill_dir = skills_root / skill_id
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(
        json.dumps({"id": skill_id, "label": label, "description": f"About {skill_id}."})
    )
    content_dir = skill_dir / "content"
    (content_dir / "references").mkdir(parents=True)
    (content_dir / "guides").mkdir(parents=True)
    (content_dir / "SKILL.md.jinja").write_text(
        f"---\nname: {skill_id}\n---\n\n# {label}\n\nFor `{{{{ package_name }}}}`.\n"
    )
    (content_dir / "references" / "api.md.jinja").write_text("Reference for {{ package_name }}.")
    (content_dir / "guides" / "howto.md.jinja").write_text("Guide for {{ package_name }}.")


class TestSkillsMechanism:
    def test_get_skill_returns_metadata(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(generator_module, "SKILLS_DIR", tmp_path)
        _write_skill(tmp_path, "widget")

        skill = get_skill("widget")

        assert skill.id == "widget"
        assert skill.label == "Widget Skill"
        assert skill.description == "About widget."
        assert skill.path == tmp_path / "widget"

    def test_get_skill_unknown_raises_brupy_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(generator_module, "SKILLS_DIR", tmp_path)

        with pytest.raises(BrupyError, match="Unknown skill 'ghost'"):
            get_skill("ghost")

    def test_template_json_skills_key_parses_into_skill_refs(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path)
        framework_dir = tmp_path / "widget"
        _write_meta(framework_dir, "widget")
        template_dir = framework_dir / "basic"
        (template_dir / "files").mkdir(parents=True)
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "id": "basic",
                    "label": "Basic",
                    "description": "d",
                    "enabled": True,
                    "skills": [
                        {"id": "widget"},
                        {"id": "gizmo", "when": {"database": ["postgres"]}},
                    ],
                }
            )
        )

        template = list_templates("widget")[0]

        assert [s.id for s in template.skills] == ["widget", "gizmo"]
        assert template.skills[1].when == {"database": ["postgres"]}

    def test_render_writes_matched_skill_under_agents_skills(self, tmp_path: Path, monkeypatch):
        skills_root = tmp_path / "skills"
        monkeypatch.setattr(generator_module, "SKILLS_DIR", skills_root)
        _write_skill(skills_root, "widget", label="Widget Skill")

        monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path / "templates")
        framework_dir = tmp_path / "templates" / "acme"
        _write_meta(framework_dir, "acme")
        template_dir = framework_dir / "basic"
        (template_dir / "files").mkdir(parents=True)
        (template_dir / "files" / "README.md").write_text("hello")
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "id": "basic",
                    "label": "Basic",
                    "description": "d",
                    "enabled": True,
                    "skills": [{"id": "widget"}],
                }
            )
        )

        target = tmp_path / "out"
        created = render(
            "acme", "basic", target, make_answers(framework="acme", template="basic")
        )

        skill_md = target / ".agents" / "skills" / "widget" / "SKILL.md"
        assert skill_md.is_file()
        assert "For `my_api`." in skill_md.read_text()
        assert Path(".agents/skills/widget/SKILL.md") in created
        assert Path(".agents/skills/widget/references/api.md") in created
        assert Path(".agents/skills/widget/guides/howto.md") in created

        # skill.json is maintainer metadata (mirrors template.json) — it
        # must never be copied into the generated project.
        assert not (target / ".agents" / "skills" / "widget" / "skill.json").exists()

    def test_render_writes_generated_skills_index(self, tmp_path: Path, monkeypatch):
        skills_root = tmp_path / "skills"
        monkeypatch.setattr(generator_module, "SKILLS_DIR", skills_root)
        _write_skill(skills_root, "widget", label="Widget Skill")
        _write_skill(skills_root, "gizmo", label="Gizmo Skill")

        monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path / "templates")
        framework_dir = tmp_path / "templates" / "acme"
        _write_meta(framework_dir, "acme")
        template_dir = framework_dir / "basic"
        (template_dir / "files").mkdir(parents=True)
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "id": "basic",
                    "label": "Basic",
                    "description": "d",
                    "enabled": True,
                    "skills": [{"id": "widget"}, {"id": "gizmo"}],
                }
            )
        )

        target = tmp_path / "out"
        created = render(
            "acme", "basic", target, make_answers(framework="acme", template="basic")
        )

        index_path = Path(".agents/skills/README.md")
        assert index_path in created
        index_text = (target / index_path).read_text()
        assert "[Widget Skill](./widget/SKILL.md)" in index_text
        assert "[Gizmo Skill](./gizmo/SKILL.md)" in index_text
        assert "About widget." in index_text

    def test_render_skips_skill_whose_when_does_not_match(self, tmp_path: Path, monkeypatch):
        skills_root = tmp_path / "skills"
        monkeypatch.setattr(generator_module, "SKILLS_DIR", skills_root)
        _write_skill(skills_root, "widget")

        monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path / "templates")
        framework_dir = tmp_path / "templates" / "acme"
        _write_meta(framework_dir, "acme")
        template_dir = framework_dir / "basic"
        (template_dir / "files").mkdir(parents=True)
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "id": "basic",
                    "label": "Basic",
                    "description": "d",
                    "enabled": True,
                    "skills": [{"id": "widget", "when": {"database": ["postgres"]}}],
                }
            )
        )

        target = tmp_path / "out"
        created = render(
            "acme",
            "basic",
            target,
            make_answers(framework="acme", template="basic"),
        )

        assert not (target / ".agents").exists()
        assert Path(".agents/skills/README.md") not in created

    def test_render_raises_when_template_references_unknown_skill(
        self, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(generator_module, "SKILLS_DIR", tmp_path / "skills")
        (tmp_path / "skills").mkdir()

        monkeypatch.setattr(generator_module, "TEMPLATES_DIR", tmp_path / "templates")
        framework_dir = tmp_path / "templates" / "acme"
        _write_meta(framework_dir, "acme")
        template_dir = framework_dir / "basic"
        (template_dir / "files").mkdir(parents=True)
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "id": "basic",
                    "label": "Basic",
                    "description": "d",
                    "enabled": True,
                    "skills": [{"id": "ghost"}],
                }
            )
        )

        with pytest.raises(BrupyError, match="Unknown skill 'ghost'"):
            render(
                "acme",
                "basic",
                tmp_path / "out",
                make_answers(framework="acme", template="basic"),
            )

    def test_real_fastapi_skill_renders_without_leftover_jinja(self, tmp_path: Path):
        # The hand-authored fastapi skill, rendered through the real
        # fastapi/rest-api template — catches unbalanced `{% %}`/`{{ }}`
        # in the shipped skill content the same way the template-content
        # tests below catch it for template files.
        target = tmp_path / "my-api"
        created = render(
            "fastapi",
            "rest-api",
            target,
            make_answers(
                framework="fastapi",
                template="rest-api",
                options={
                    "database": "sqlite",
                    "orm": "sqlmodel",
                    "migrations": True,
                    "worker": "none",
                    "broker": "none",
                    "redis": False,
                },
            ),
        )

        skill_paths = [p for p in created if p.parts[:2] == (".agents", "skills")]
        assert Path(".agents/skills/fastapi/SKILL.md") in skill_paths
        assert Path(".agents/skills/README.md") in skill_paths
        for rel in skill_paths:
            text = (target / rel).read_text()
            assert "{%" not in text
            assert "{{" not in text
        skill_md_text = (target / ".agents/skills/fastapi/SKILL.md").read_text()
        assert "my_api" in skill_md_text
