from hypothesis import given
from hypothesis import strategies as st

from review_assistant.context.packer import estimate_tokens, pack
from review_assistant.models import FileDiff


def file(path: str, size: int) -> FileDiff:
    return FileDiff(path=path, patch="x" * size)


def test_files_that_fit_are_kept_in_order() -> None:
    files = [file("a", 400), file("b", 400), file("c", 400)]
    result = pack(files, 8192, 1024)
    assert [f.path for f in result.files] == ["a", "b", "c"]
    assert result.dropped == []


def test_the_first_file_that_does_not_fit_ends_the_pack() -> None:
    files = [file("a", 16000), file("b", 16000), file("c", 400)]
    result = pack(files, 8192, 1024)
    assert [f.path for f in result.files] == ["a"]
    assert result.dropped == ["b", "c"]


def test_tokens_are_the_sum_of_the_kept_files() -> None:
    files = [file("a", 400), file("b", 800)]
    result = pack(files, 8192, 1024)
    expected = sum(estimate_tokens(f.patch) + estimate_tokens(f.neighbors) for f in files)
    assert result.tokens == expected


@given(st.lists(st.integers(min_value=0, max_value=3000), max_size=12))
def test_kept_plus_dropped_is_the_input_in_order(sizes: list[int]) -> None:
    files = [file(f"f{i}", size) for i, size in enumerate(sizes)]
    result = pack(files, 8192, 1024)
    assert [f.path for f in result.files] + result.dropped == [f.path for f in files]
