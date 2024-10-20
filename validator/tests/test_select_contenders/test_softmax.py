import pytest
import math
from validator.query_node.src.select_contenders import _softmax

@pytest.mark.parametrize("scores, temperature, expected", [
    ([1.0, 2.0, 3.0], 2.0, [0.1863237, 0.30719589, 0.5064804]),
    ([1.0, 1.0, 1.0], 0.5, [0.33333333, 0.33333333, 0.33333333]),
    ([1.0], 1.0, [1.0]),
    ([], 1.0, []),
    ([-1.0, -2.0, -3.0], 1.0, [0.66524096, 0.24472847, 0.09003057]),
    ([1.0, 2.0, 3.0], 2.0, [0.186323, 0.307196, 0.506480]),
    ([1.0, 1.1, 1.2], 2.0, [0.3168124, 0.3330557, 0.350132]),
    ([1.0, 1.01, 1.02], 2.0, [0.33166806, 0.333331, 0.335001])
])
def test_softmax(scores, temperature, expected):
    result = _softmax(scores, temperature)
    assert all(math.isclose(r, e, rel_tol=1e-5) for r, e in zip(result, expected)), f"Expected {expected}, but got {result}"
