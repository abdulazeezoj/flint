import pytest

from flint.errors import FlintUserError
from flint.naming import validate_project_name


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
    with pytest.raises(FlintUserError):
        validate_project_name(raw)
