"""GHSA-9ffx-rrgx-mhgx [medium] -- ARFF label injection in Weka classifier"""

from nltk.classify.weka import ARFF_Formatter

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-9ffx-rrgx-mhgx")
def _arff_label_injection():
    """ARFF injection via class labels, feature values, and feature names.

    Each surface is fed a payload that tries to close its context and inject a
    fresh @ATTRIBUTE/@DATA directive (with LF and CRLF variants); none may
    surface as a live ARFF line in the generated file.
    """
    lf = "safe}\n@ATTRIBUTE injected NUMERIC\n@DATA\n0,owned\n%"
    crlf = "x\r\n@ATTRIBUTE crinjected NUMERIC\r\n@DATA"

    def build(featuresets):
        return ARFF_Formatter.from_train(featuresets).format(featuresets)

    checks = [
        ("label", build([({"f": "benign"}, "legit"), ({"f": "p"}, lf)])),
        ("value", build([({"f": "benign"}, "legit"), ({"f": lf}, "legit")])),
        ("attr-name", build([({lf: "benign"}, "legit")])),
        ("crlf-label", build([({"f": "benign"}, "legit"), ({"f": "p"}, crlf)])),
    ]
    # A real injection surfaces one of these payload directives at a line start;
    # the legitimate output never does (the only @DATA is the single real header).
    live = ("@attribute injected", "@attribute crinjected", "0,owned")
    for surface, arff in checks:
        if arff.count("\n@DATA") > 1:
            return VULNERABLE, f"ARFF injection via {surface} added a second @DATA"
        for raw in arff.splitlines():
            line = raw.strip().lower()
            if any(line.startswith(m) for m in live):
                return (
                    VULNERABLE,
                    f"ARFF injection via {surface} produced a live directive",
                )
    return FIXED, "ARFF labels, values, and attribute names sanitized"
