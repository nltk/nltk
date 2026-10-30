# Natural Language Toolkit: process-spawn chokepoint guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The pre-commit guard that keeps every process spawn inside
``nltk.pathsec.spawn_trusted`` (CWE-426 / CWE-427 / CWE-78): it must pass on
the library as shipped, and it must catch every spawning call form when one
is planted, so a future bare ``Popen`` cannot slip back in."""

import importlib.util
import os
import subprocess
import sys

import pytest

import nltk

REPO = os.path.dirname(os.path.dirname(os.path.abspath(nltk.__file__)))
CHECKER = os.path.join(REPO, "tools", "check_all_spawns_through_pathsec.py")


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_spawns", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_library_spawns_only_through_pathsec():
    # the real hook, run the way pre-commit runs it, over the real tree
    proc = subprocess.run(
        [sys.executable, CHECKER], cwd=REPO, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


PLANTED = {
    "subprocess.Popen(['x'])": "subprocess.Popen",
    "subprocess.run(['x'])": "subprocess.run",
    "subprocess.call(['x'])": "subprocess.call",
    "subprocess.check_call(['x'])": "subprocess.check_call",
    "subprocess.check_output(['x'])": "subprocess.check_output",
    "subprocess.getoutput('x')": "subprocess.getoutput",
    "subprocess.getstatusoutput('x')": "subprocess.getstatusoutput",
    "os.system('x')": "os.system",
    "os.popen('x')": "os.popen",
    "os.execv('/x', ['x'])": "os.execv",
    "os.execvp('x', ['x'])": "os.execvp",
    "os.spawnv(0, '/x', ['x'])": "os.spawnv",
    "os.posix_spawn('/x', ['x'], {})": "os.posix_spawn",
    "os.startfile('x')": "os.startfile",
    "shutil.which('x')": "shutil.which",
}


@pytest.mark.parametrize("call, spawner", sorted(PLANTED.items()))
def test_every_spawning_call_form_is_caught(tmp_path, call, spawner):
    checker = _load_checker()
    planted = tmp_path / "planted.py"
    planted.write_text(f"import os, shutil, subprocess\n\n{call}\n", encoding="utf-8")
    problems = checker._violations(str(planted))
    assert len(problems) == 1 and spawner in problems[0], problems


def test_a_spawn_reached_through_an_imported_name_is_caught(tmp_path):
    checker = _load_checker()
    planted = tmp_path / "planted.py"
    planted.write_text(
        "from subprocess import Popen as launch\n"
        "from os import system\n"
        "from shutil import which\n\n"
        "launch(['x'])\nsystem('x')\nwhich('x')\n",
        encoding="utf-8",
    )
    problems = checker._violations(str(planted))
    assert len(problems) == 3, problems
    assert any("subprocess.Popen" in p for p in problems)
    assert any("os.system" in p for p in problems)
    assert any("shutil.which" in p for p in problems)


def test_a_spawn_reached_through_a_module_alias_is_caught(tmp_path):
    # the adversarial review found these slipped past: the module bound under
    # another name, in a plain import or a multi-name one
    checker = _load_checker()
    planted = tmp_path / "planted.py"
    planted.write_text(
        "import subprocess as sp\n"
        "import os as o, shutil as sh\n"
        "import subprocess\n\n"
        "sp.Popen(['x'])\no.system('x')\nsh.which('x')\nsubprocess.run(['x'])\n",
        encoding="utf-8",
    )
    problems = checker._violations(str(planted))
    assert len(problems) == 4, problems
    for spawner in ("subprocess.Popen", "os.system", "shutil.which", "subprocess.run"):
        assert any(spawner in p for p in problems), spawner


SMUGGLED = {
    "from subprocess import *\nPopen(['x'])\n": "subprocess.Popen",
    "import subprocess\ngetattr(subprocess, 'Popen')(['x'])\n": "subprocess.Popen",
    "import subprocess\nlaunch = getattr(subprocess, 'run')\nlaunch(['x'])\n": (
        "subprocess.run"
    ),
    "import subprocess as sp\ngetattr(sp, 'call')(['x'])\n": "subprocess.call",
    "import importlib\nimportlib.import_module('subprocess').Popen(['x'])\n": (
        "subprocess.Popen"
    ),
    "from importlib import import_module\nm = import_module('os')\nm.system('x')\n": (
        "os.system"
    ),
    "__import__('subprocess').Popen(['x'])\n": "subprocess.Popen",
    "import importlib\nm = importlib.import_module('subprocess')\n": (
        "dynamic import of subprocess"
    ),
    "from importlib import import_module as load\nload('os.path')\n": (
        "dynamic import of os"
    ),
    "exec('import subprocess; subprocess.Popen([\"x\"])')\n": "exec of source",
    'eval(\'__import__("os").system("x")\')\n': "eval of source",
    "compile('from shutil import which', 'p', 'exec')\n": "compile of source",
    "import nltk.pathsec\nnltk.pathsec.subprocess.Popen(['x'])\n": "subprocess.Popen",
    "import subprocess\nlaunch = subprocess.Popen\nlaunch(['x'])\n": "subprocess.Popen",
    "from subprocess import Popen\nlaunch = Popen\nstart = launch\nstart(['x'])\n": (
        "subprocess.Popen"
    ),
    "import subprocess\nsp = subprocess\nsp.run(['x'])\n": "subprocess.run",
    "import asyncio\nasyncio.create_subprocess_exec('x')\n": (
        "asyncio.create_subprocess_exec"
    ),
    "import asyncio\nasyncio.create_subprocess_shell('x')\n": (
        "asyncio.create_subprocess_shell"
    ),
    "import pty\npty.spawn(['x'])\n": "pty.spawn",
    "import os\nif os.fork() == 0:\n    os.execv('/x', ['x'])\n": "os.execv",
}


@pytest.mark.parametrize("source, spawner", sorted(SMUGGLED.items()))
def test_a_smuggled_spawn_is_caught(tmp_path, source, spawner):
    # every way of reaching a spawner without spelling module.spawner that a
    # static walk can still see: star import, getattr with a literal name, a
    # module loaded by name, source run through exec/eval/compile, an
    # attribute chain ending in the module, a rebound name (to a fixpoint)
    checker = _load_checker()
    planted = tmp_path / "planted.py"
    planted.write_text(source, encoding="utf-8")
    problems = checker._violations(str(planted))
    assert problems and any(spawner in p for p in problems), (source, problems)


CLEAN = [
    "import os.path as p\np.join('a', 'b')\n",
    "import os\nflags = getattr(os, 'O_NOFOLLOW', 0)\n",
    "import importlib\nimportlib.import_module('nltk.internals')\n",
    "import importlib\nname = 'x'\nimportlib.import_module(name)\n",
    "def load(module):\n    return __import__(module)\n",
    "src = 'x'\neval(src)\n",
    "window = 'hanning'\neval('numpy.' + window + '(n)')\n",
    "eval('cos(1)')\n",
    "eval('os.path.join(a, b)')\n",
    "import subprocess\nPIPE = subprocess.PIPE\n",
    "from os import path\npath.join('a')\n",
    "class Job:\n    def run(self):\n        return self.call()\n\n"
    "    def call(self):\n        return 1\n\n\nJob().run()\n",
]


@pytest.mark.parametrize("source", CLEAN)
def test_a_reference_that_reaches_no_spawner_is_not_flagged(tmp_path, source):
    # the forms the library itself uses (a getattr for an os flag, a module
    # loaded from a variable, eval of a numpy window name) stay clean
    checker = _load_checker()
    clean = tmp_path / "clean.py"
    clean.write_text(source, encoding="utf-8")
    assert checker._violations(str(clean)) == [], source


def test_unrelated_attributes_and_the_reviewed_marker_are_not_flagged(tmp_path):
    checker = _load_checker()
    clean = tmp_path / "clean.py"
    clean.write_text(
        "import subprocess\n\n"
        "class Job:\n"
        "    def run(self):\n"
        "        return self.call()\n\n"
        "    def call(self):\n"
        "        return subprocess.PIPE\n\n"
        "Job().run()\n"
        "subprocess.Popen(['x'])  # spawn ok: test double for a sandboxed host\n",
        encoding="utf-8",
    )
    assert checker._violations(str(clean)) == []


def test_pathsec_itself_is_the_only_allowed_file():
    checker = _load_checker()
    guarded = list(checker._guarded_files())
    assert guarded, "the walk must cover the package"
    assert os.path.join("nltk", "pathsec.py") not in guarded
    assert os.path.join("nltk", "internals.py") in guarded
    assert not any(p.startswith(os.path.join("nltk", "test")) for p in guarded)
