"""GHSA-9ffx-rrgx-mhgx [medium] -- ARFF label injection in Weka classifier"""

from nltk.classify.weka import ARFF_Formatter

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-9ffx-rrgx-mhgx")
def _arff_label_injection():
    malicious = "safe}\n@ATTRIBUTE injected NUMERIC\n@DATA\n0,owned\n%"
    featuresets = [
        ({"f": "benign"}, "legit"),
        ({"f": "payload"}, malicious),
    ]
    formatter = ARFF_Formatter.from_train(featuresets)
    arff = formatter.format(featuresets)

    if "@ATTRIBUTE injected NUMERIC" in arff and "@DATA\n0,owned" in arff:
        return VULNERABLE, "ARFF injection succeeded"
    else:
        return FIXED, "ARFF labels sanitized"
