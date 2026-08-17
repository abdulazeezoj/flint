import pytest

import brupy.naming as naming_module
from brupy.errors import BrupyUserError
from brupy.naming import validate_project_name


@pytest.mark.parametrize(
    ("raw", "expected_slug", "expected_package"),
    [
        ("my-api", "my-api", "my_api"),
        ("My Api", "my-api", "my_api"),
        ("  hello_world!!  ", "hello-world", "hello_world"),
        ("Café Time", "caf-time", "caf_time"),
        ("123abc", "123abc", "_123abc"),
        ("Already-Kebab-Case", "already-kebab-case", "already_kebab_case"),
    ],
)
def test_validate_project_name_ok(raw, expected_slug, expected_package):
    slug, package_name = validate_project_name(raw)
    assert slug == expected_slug
    assert package_name == expected_package
    assert package_name.isidentifier()


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "!!!",
        "class",  # python keyword
        "match",  # soft keyword
        "os",  # stdlib shadow
        "test",  # reserved
    ],
)
def test_validate_project_name_rejects(raw):
    with pytest.raises(BrupyUserError):
        validate_project_name(raw)


def test_validate_project_name_rejects_non_identifier_defensively(monkeypatch):
    # slugify()/package_name_from_slug() only ever produce [a-z0-9_] text
    # that's already a valid identifier, so this branch is a defensive
    # backstop rather than something reachable via real input — exercise
    # it directly by forcing package_name_from_slug to misbehave.
    monkeypatch.setattr(naming_module, "package_name_from_slug", lambda slug: "1-not-ok")

    with pytest.raises(BrupyUserError, match="cannot be turned into a valid Python package name"):
        validate_project_name("whatever")
