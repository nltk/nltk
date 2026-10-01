from nltk.util import acyclic_depth_first

from ._base import FIXED, VULNERABLE, probe


class MockNode:
    def __init__(self, name, children=None):
        self.name = name
        self._children = children or []

    def rel(self):
        return self._children


@probe("GHSA-8846-p9w9-5frf")
def test_wordnet_recursion():
    nodes = [MockNode(str(i)) for i in range(1500)]
    for i in range(1499):
        nodes[i]._children = [nodes[i + 1]]
    try:
        list(acyclic_depth_first(nodes[0], lambda x: x.rel(), depth=-1))
        return (FIXED, "Depth cap prevents recursion overflow")
    except RecursionError:
        return (VULNERABLE, "Uncontrolled recursion still possible")
    except ValueError as e:
        if "exceeds maximum allowed recursion depth" in str(e):
            return (FIXED, "Depth cap enforces limit via ValueError")
        else:
            return (VULNERABLE, f"Unexpected error: {e}")
