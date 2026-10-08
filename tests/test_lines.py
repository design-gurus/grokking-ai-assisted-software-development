from review_assistant.diff.lines import new_file_lines


def test_first_line_of_a_hunk_is_new_start() -> None:
    assert new_file_lines(10, [" ", "+", "-", " "])[0] == 10


def test_last_line_counts_only_lines_in_the_new_file() -> None:
    assert new_file_lines(3, [" ", " ", " ", "+"]) == [3, 4, 5, 6]


def test_removed_lines_take_no_number() -> None:
    assert new_file_lines(7, ["-", "-", "+"]) == [-1, -1, 7]


def test_all_removed_hunk() -> None:
    assert new_file_lines(25, ["-", "-", "-"]) == [-1, -1, -1]


def test_single_added_line() -> None:
    assert new_file_lines(1, ["+"]) == [1]
