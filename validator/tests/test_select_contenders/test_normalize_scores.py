import pytest
from validator.query_node.src.select_contenders import _normalize_scores_for_selection

@pytest.mark.parametrize("scores, expected", [
    ([1.0, 2.0, 3.0], [0.0, 0.5, 1.0]),
    ([1.0, 1.0, 1.0], [0.0, 0.0, 0.0]),
    ([1.0], [0.0]),
    ([], []),
    ([-1.0, -2.0, -3.0], [1.0, 0.5, 0.0])
])
def test_normalize_scores_for_selection(scores, expected):
    result = _normalize_scores_for_selection(scores)
    assert result == expected, f"Expected {expected}, but got {result}"