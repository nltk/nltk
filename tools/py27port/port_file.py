"""Port one Python 3 source file of the 3.10 tree to the 2.7 branch: every
mechanical pass in order. Usage: port_file.py <src> <dst>  (prints a report)"""
import re
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import py2pass  # noqa: E402

src_path, dst_path = sys.argv[1], sys.argv[2]
src = open(src_path, encoding="utf-8").read()
out, report = py2pass.run(src)
out, n = py2pass.numeric_underscores(out); report["underscores"] = n
out, n = py2pass.kwonly_decorator(out); report["kwonly"] = n

def sub(pat, rep, flags=0):
    global out
    out, k = re.subn(pat, rep, out, flags=flags)
    return k

report["rb"] = sub(r"\brb([\"'])", r"br\1")
report["chr"] = sub(r"(?<![\w.])chr\(", "_uchr(")
report["trailing_kw_comma"] = sub(r"(\*\*\w+),(\s*\n\s*\))", r"\1\2")
report["isinstance_str"] = sub(r"isinstance\(([^()]*(?:\([^()]*(?:\([^()]*\))?[^()]*\))?[^()]*), str\)", r"isinstance(\1, six.string_types)")
report["newstyle"] = sub(r"^(\s*)class (\w+):", r"\1class \2(object):", re.M)
report["pathlib"] = sub(r"^([ \t]*)from pathlib import (.+)$", lambda m: "%stry:\n%s    from pathlib import %s\n%sexcept ImportError:  # Python 2.7\n%s    from pathlib2 import %s" % (m.group(1), m.group(1), m.group(2), m.group(1), m.group(1), m.group(2)), re.M)
report["pathlib"] += sub(r"^([ \t]*)import pathlib$", lambda m: "%stry:\n%s    import pathlib\n%sexcept ImportError:  # Python 2.7\n%s    import pathlib2 as pathlib" % ((m.group(1),) * 4), re.M)
report["builtins"] = sub(r"^([ \t]*)import builtins$", r"\1from six.moves import builtins", re.M)
report["urllib"] = sub(r"^([ \t]*)import urllib\.(request|parse|error)$", r"\1from six.moves import urllib", re.M)
report["urllib"] += sub(r"^([ \t]*)from urllib\.(request|parse|error) import ", r"\1from six.moves.urllib.\2 import ", re.M)
report["http"] = sub(r"^([ \t]*)import http\.client$", r"\1from six.moves import http_client", re.M)
report["http"] += sub(r"\bhttp\.client\.", "http_client.")
report["mock"] = sub(r"^([ \t]*)from unittest import mock$", r"\1try:\n\1    from unittest import mock\n\1except ImportError:  # Python 2.7\n\1    import mock", re.M)
report["mock"] += sub(r"^([ \t]*)from unittest\.mock import (.+)$", r"\1try:\n\1    from unittest.mock import \2\n\1except ImportError:  # Python 2.7\n\1    from mock import \2", re.M)
report["reload"] = sub(r"\bimportlib\.reload\(", "six.moves.reload_module(")
report["io_open"] = sub(r"(?<![\w.])(?<!def )open\(([^()]*(?:\([^()]*\))?[^()]*encoding=[^()]*)\)", r"io.open(\1)")
report["process_time"] = sub(r"\btime\.(process_time|perf_counter)\(", r"\1(")
report["os_path_api"] = sub(r"\bos\.PathLike\b", "PathLike") + sub(r"\bos\.fspath\(", "fspath(") + sub(r"\bos\.fsdecode\(", "fsdecode(") + sub(r"\bos\.fsencode\(", "fsencode(")
report["simplens"] = sub(r"\btypes\.SimpleNamespace\b", "SimpleNamespace") + sub(r"^([ \t]*)from types import SimpleNamespace$", r"\1from nltk.compat import SimpleNamespace", re.M)
report["lru"] = sub(r"^([ \t]*)from functools import lru_cache$", r"\1try:\n\1    from functools import lru_cache\n\1except ImportError:  # Python 2.7\n\1    from backports.functools_lru_cache import lru_cache", re.M)
report["lru"] += sub(r"\bfunctools\.lru_cache\b", "lru_cache")
if "lru_cache" in out and "from functools import lru_cache" not in out and "backports.functools_lru_cache" not in out and "lru_cache(" in out:
    out = out.replace("import six\n", "import six\ntry:\n    from functools import lru_cache\nexcept ImportError:  # Python 2.7\n    from backports.functools_lru_cache import lru_cache\n", 1)
report["collections_abc"] = sub(r"^([ \t]*)from collections\.abc import (.+)$", r"\1try:\n\1    from collections.abc import \2\n\1except ImportError:  # Python 2.7\n\1    from collections import \2", re.M)
report["collections_abc"] += sub(r"\bcollections\.abc\.", "_collections_abc.")
if "_collections_abc." in out:
    out = out.replace("import six\n", "import six\ntry:\n    import collections.abc as _collections_abc\nexcept ImportError:  # Python 2.7\n    import collections as _collections_abc\n", 1)
report["str_maketrans"] = sub(r"str\.maketrans\(([^,()]+), ([^,()]+)\)", r"dict(zip(map(ord, \1), \2))")
report["subprocess_timeout"] = sub(r"\bsubprocess\.TimeoutExpired\b", "TimeoutExpired")
report["super"] = 0
# the nltk.compat names a file now uses
NAMES = ["FileNotFoundError", "PermissionError", "IsADirectoryError", "NotADirectoryError", "FileExistsError", "TimeoutError", "ChildProcessError", "ProcessLookupError", "BrokenPipeError", "ConnectionError", "InterruptedError", "SimpleNamespace", "PathLike", "fspath", "fsdecode", "fsencode", "process_time", "perf_counter", "TimeoutExpired", "load_module_from_file"]
used = [n for n in NAMES if re.search(r"(?<![\w.])%s\b" % n, out)]
used = [n for n in used if not re.search(r"^from nltk\.compat import .*\b%s\b" % n, out, re.M)]
if used:
    m = re.search(r"^from nltk\.compat import (.+)$", out, re.M)
    if m:
        out = out.replace(m.group(0), m.group(0) + ", " + ", ".join(used), 1)
    else:
        out = out.replace("import six\n", "import six\nfrom nltk.compat import %s\n" % ", ".join(used), 1)
if "_uchr(" in out and "from nltk.termsec import _uchr" not in out and not dst_path.endswith("termsec.py"):
    out = out.replace("import six\n", "import six\nfrom nltk.termsec import _uchr\n", 1)
if "io.open(" in out and not re.search(r"^import io$", out, re.M):
    out = out.replace("import six\n", "import io\nimport six\n", 1)
open(dst_path, "w", encoding="utf-8").write(out)
subprocess.run([sys.executable, __file__.rsplit("/", 1)[0] + "/reescape.py", dst_path], capture_output=True)
print("%s: %s" % (dst_path.rsplit("/", 1)[-1], ", ".join("%s=%d" % kv for kv in report.items() if kv[1])))
