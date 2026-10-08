import review_assistant


def test_package_imports_and_has_a_version() -> None:
    assert review_assistant.__version__ == "0.1.0"
