"""GHSA-6hwm-xvph-95vm [low] -- Uncontrolled search path when invoking the Graphviz 'dot' binary (CWE-426/CWE-427)"""

from ._base import BENIGN, STATIC, probe, read_source


@probe("GHSA-6hwm-xvph-95vm")
def _graphviz_search_path():
    """Uncontrolled search path when invoking the Graphviz 'dot' binary."""
    source = read_source("nltk.parse.dependencygraph")
    if "shutil.which" in source or "find_binary" in source:
        return STATIC, "binary resolved through an explicit lookup"
    return BENIGN, "no bare 'dot' invocation found"
