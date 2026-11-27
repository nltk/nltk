from nltk.parse.dependencygraph import DependencyGraph

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-rh8m-wqhc-qmrf")
def probe_ghsa_rh8m_wqhc_qmrf():
    """Verify DependencyGraph tree traversal rejects deeply chained or cyclic

    dependency structures gracefully (GHSA-rh8m-wqhc-qmrf).
    """
    chain_length = 1500
    conll_lines = ["word1\tN\t0\tROOT"] + [
        f"word{i}\tN\t{i - 1}\tdep" for i in range(2, chain_length + 1)
    ]
    conll_data = "\n".join(conll_lines)
    graph = DependencyGraph(conll_data)

    try:
        graph.tree()
        return FIXED, "Tree traversal completed within operational bounds"
    except ValueError as e:
        return FIXED, f"Recursion depth limit safely caught by parser: {e}"
    except RecursionError as e:
        return VULNERABLE, f"Unhandled RecursionError during graph traversal: {e}"
    except Exception as e:
        return VULNERABLE, f"Unexpected exception: {type(e).__name__}: {e}"
