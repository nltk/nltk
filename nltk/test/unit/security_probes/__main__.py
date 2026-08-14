"""Print the advisory probe report: ``python -m nltk.test.unit.security_probes``."""

import sys

from . import run

sys.exit(1 if run() else 0)
