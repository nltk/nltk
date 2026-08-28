# Natural Language Toolkit: exhaustive attack matrix for the pathsec tool-IO guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Exhaustive attack matrix for the three caller-facing ``nltk.pathsec`` tool-IO
guards (GHSA-8mgp-746c-j5xp umbrella; CWE-22/59/88/377/378/400):

* :func:`nltk.pathsec.validate_tool_dir` -- the directory sink that
  ``PerceptronTagger.save_to_json`` and ``Maxent_NE_Chunker.save_params`` use;
* :func:`nltk.pathsec.validate_tool_path` -- the file sink (read and write) that
  ``MaltParser`` and the Stanford JVM wrappers use for ``-i`` / ``-o``;
* :func:`nltk.pathsec.validate_model_resource` -- the ``-model`` argument that may
  be a jar-internal resource *name* or a real filesystem path.

Testing the guards directly rather than one wrapper covers every wrapper at once,
since they all funnel their caller-supplied paths through these functions. Each
hostile vector must be REFUSED (``PermissionError`` / ``ValueError``); each benign
in-root vector must SUCCEED. POSIX-only vectors (symlink / FIFO / socket /
hardlink) and Windows-only vectors (reserved device, 8.3 short name, NTFS stream,
drive-relative) are ``skipif``-guarded so the matrix is green on every platform.

Everything is staged inside a *registered* pathsec data root (the conftest
``restricted_sandbox`` / ``pathsec_sandbox`` fixtures); the out-of-root target is
a directory under the real ``$HOME`` (never a temp dir, which is itself an allowed
root on macOS).
"""

import os
import socket
import unicodedata

import pytest

from nltk.pathsec import (
    _reject_colliding_members,
    validate_model_resource,
    validate_tool_dir,
    validate_tool_path,
)

REFUSALS = (PermissionError, ValueError)

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="symlink / FIFO / socket / hardlink are POSIX vectors"
)
WINDOWS_ONLY = pytest.mark.skipif(
    os.name == "posix",
    reason="reserved device / 8.3 / NTFS-stream / drive-relative are Windows vectors",
)


def _regular_file(directory, name="good.conll"):
    path = os.path.join(str(directory), name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("1\tHello\t_\t_\t_\t_\t0\t_\t_\t_\n")
    return path


# ==========================================================================
# validate_tool_dir -- the trained-model directory sink
# ==========================================================================
class TestValidateToolDir:
    def test_benign_in_root_dir_is_allowed(self, restricted_sandbox):
        d = os.path.join(restricted_sandbox, "model_dir")
        os.makedirs(d)
        assert validate_tool_dir(d)  # returns the checked string

    def test_new_in_root_dir_name_is_allowed(self, restricted_sandbox):
        # A not-yet-created leaf is legal: the tool creates it after the check.
        assert validate_tool_dir(os.path.join(restricted_sandbox, "will_create"))

    def test_traversal_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, "..", "..", "etc"))

    def test_nul_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, "a\x00b"))

    def test_absolute_outside_is_refused(self, sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(str(sandbox), "model_dir"))

    def test_option_shaped_is_refused(self):
        with pytest.raises(REFUSALS):
            validate_tool_dir("-Xevil")

    @pytest.mark.parametrize("url", ["http://evil/x", "file:///etc/passwd"])
    def test_url_is_refused(self, url):
        with pytest.raises(REFUSALS):
            validate_tool_dir(url)

    @pytest.mark.parametrize("suffix", ["evil.", "evil "])
    def test_trailing_dot_or_space_is_refused(self, restricted_sandbox, suffix):
        # Windows silently strips a trailing '.'/' ', so the checked name differs
        # from the opened one; refused everywhere for determinism.
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, suffix))

    def test_bare_name_resolving_to_cwd_is_refused(self):
        with pytest.raises(REFUSALS):
            validate_tool_dir("some_relative_dir")

    @WINDOWS_ONLY
    @pytest.mark.parametrize("name", ["NUL", "CON", "COM1", "LPT1"])
    def test_windows_device_name_is_refused(self, restricted_sandbox, name):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, name))

    @WINDOWS_ONLY
    def test_windows_short_name_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, "PROGRA~1", "x"))


# ==========================================================================
# validate_tool_path -- the file sink a tool READS (e.g. MaltParser -i)
# ==========================================================================
class TestValidateToolPathRead:
    def test_benign_in_root_file_is_allowed(self, restricted_sandbox):
        assert validate_tool_path(_regular_file(restricted_sandbox))

    @POSIX_ONLY
    def test_leaf_symlink_to_in_root_is_refused(self, restricted_sandbox):
        # O_NOFOLLOW refuses a symlink leaf whatever it points at (CWE-59).
        target = _regular_file(restricted_sandbox)
        link = os.path.join(restricted_sandbox, "link.conll")
        os.symlink(target, link)
        with pytest.raises(REFUSALS):
            validate_tool_path(link)

    @POSIX_ONLY
    def test_leaf_symlink_to_outside_is_refused(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").close()
        link = os.path.join(str(root), "leak.conll")
        os.symlink(secret, link)
        with pytest.raises(REFUSALS):
            validate_tool_path(link)

    @POSIX_ONLY
    def test_parent_symlink_escaping_root_is_refused(self, pathsec_sandbox):
        # The leaf is benign but its PARENT is a symlink pointing OUTSIDE the root
        # (a TOCTOU-style redirect); containment resolves through it and refuses.
        root, outside = pathsec_sandbox
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").close()
        parent = os.path.join(str(root), "parent")
        os.symlink(str(outside), parent)
        with pytest.raises(REFUSALS):
            validate_tool_path(os.path.join(parent, "secret"))

    @POSIX_ONLY
    def test_fifo_is_refused(self, restricted_sandbox):
        fifo = os.path.join(restricted_sandbox, "fifo.conll")
        os.mkfifo(fifo)
        with pytest.raises(REFUSALS):
            validate_tool_path(fifo)

    @POSIX_ONLY
    def test_unix_socket_is_refused(self, restricted_sandbox):
        sockpath = os.path.join(restricted_sandbox, "sock.conll")
        sock = socket.socket(socket.AF_UNIX)
        try:
            sock.bind(sockpath)
            with pytest.raises(REFUSALS):
                validate_tool_path(sockpath)
        finally:
            sock.close()

    def test_traversal_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_path(os.path.join(restricted_sandbox, "..", "x"))

    def test_nul_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_path(os.path.join(restricted_sandbox, "a\x00b"))

    def test_absolute_outside_is_refused(self, sandbox):
        secret = os.path.join(str(sandbox), "secret")
        open(secret, "w").close()
        with pytest.raises(REFUSALS):
            validate_tool_path(secret)

    def test_option_shaped_is_refused(self):
        with pytest.raises(REFUSALS):
            validate_tool_path("-Xevil")

    def test_url_is_refused(self):
        with pytest.raises(REFUSALS):
            validate_tool_path("http://evil/x")


# ==========================================================================
# validate_tool_path(for_write=True) -- the file sink a tool WRITES (e.g. -o)
# ==========================================================================
class TestValidateToolPathWrite:
    def test_benign_new_output_in_root_is_allowed(self, restricted_sandbox):
        assert validate_tool_path(
            os.path.join(restricted_sandbox, "new.out"),
            for_write=True,
            must_exist=False,
        )

    @POSIX_ONLY
    def test_hardlink_to_outside_inode_is_refused(self, pathsec_sandbox):
        # An in-root name whose inode lives OUTSIDE the root: writing it would
        # overwrite the outside file (CWE-59). realpath() cannot see the alias, so
        # the st_nlink check refuses it.
        root, outside = pathsec_sandbox
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").close()
        hard = os.path.join(str(root), "hard.out")
        try:
            os.link(secret, hard)
        except OSError:
            pytest.skip("cross-dir hardlink not permitted here")
        with pytest.raises(REFUSALS):
            validate_tool_path(hard, for_write=True, must_exist=False)

    @POSIX_ONLY
    def test_write_through_leaf_symlink_is_refused(self, restricted_sandbox):
        real = _regular_file(restricted_sandbox, "real.out")
        link = os.path.join(restricted_sandbox, "slink.out")
        os.symlink(real, link)
        with pytest.raises(REFUSALS):
            validate_tool_path(link, for_write=True, must_exist=True)

    def test_traversal_write_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_path(
                os.path.join(restricted_sandbox, "..", "esc.out"),
                for_write=True,
                must_exist=False,
            )


# ==========================================================================
# validate_model_resource -- the -model arg (jar resource NAME or real path)
# ==========================================================================
class TestValidateModelResource:
    @pytest.mark.parametrize(
        "name",
        [
            "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
            "model.mco",
            "englishPCFG.ser.gz",
        ],
    )
    def test_bare_resource_name_is_passed_through(self, name):
        # A jar-internal resource name is NOT a filesystem path and is returned
        # unchanged so the JVM default classpath resource still resolves.
        assert validate_model_resource(name) == name

    def test_real_in_root_path_is_allowed(self, restricted_sandbox):
        path = _regular_file(restricted_sandbox, "model.mco")
        assert validate_model_resource(path) == path

    @pytest.mark.parametrize(
        "value",
        [
            "../../etc/passwd",
            "a\x00b",
            "-model",
            "http://evil/m",
            "file:///etc/passwd",
            "..\\..\\etc",
        ],
    )
    def test_malformed_or_traversing_value_is_refused(self, value):
        with pytest.raises(REFUSALS):
            validate_model_resource(value)

    def test_absolute_outside_path_is_refused(self, sandbox):
        secret = os.path.join(str(sandbox), "model.mco")
        open(secret, "w").close()
        with pytest.raises(REFUSALS):
            validate_model_resource(secret)


# ==========================================================================
# Model-file name collisions (case-fold / unicode NFC) -- resource poisoning
# ==========================================================================
class TestModelFileCollision:
    def test_casefold_collision_is_refused(self):
        with pytest.raises(ValueError):
            _reject_colliding_members(["pkg/Weights.json", "pkg/weights.json"])

    def test_unicode_nfc_collision_is_refused(self):
        nfc = unicodedata.normalize("NFC", "café.json")
        nfd = unicodedata.normalize("NFD", "café.json")
        assert nfc != nfd
        with pytest.raises(ValueError):
            _reject_colliding_members([nfc, nfd])

    def test_distinct_members_are_allowed(self):
        # Benign control: a legitimate model archive never collides.
        _reject_colliding_members(["weights.json", "tagdict.json", "classes.json"])


# ==========================================================================
# Frozen __fspath__ / hostile str subclass (the guard must not be fooled)
# ==========================================================================
class _LyingPath:
    """__fspath__ that answers a different value on each call (a real, legal
    thing for os.PathLike). The guard must resolve it EXACTLY ONCE and use the
    frozen result, or it validates one file while the tool opens another."""

    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def __fspath__(self):
        value = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return value


class _EvilStr(str):
    """A str subclass whose lookup methods lie, to smuggle a traversal past a
    naive check. ``_as_path_text`` defeats it with ``str.__str__``."""

    def __contains__(self, item):
        return False

    def startswith(self, *args, **kwargs):
        return False

    def replace(self, *args, **kwargs):
        return "clean"


class TestHostilePathObjects:
    def test_lying_fspath_traversal_is_refused(self):
        with pytest.raises(REFUSALS):
            validate_tool_path(_LyingPath(["../../etc/passwd"]))

    def test_fspath_is_frozen_to_first_value(self, restricted_sandbox, pathsec_sandbox):
        # First answer benign (in root), later answers hostile: the guard must
        # return the frozen first value, never re-read the object.
        root, outside = pathsec_sandbox
        good = _regular_file(root, "frozen.conll")
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").close()
        returned = validate_tool_path(_LyingPath([good, secret, secret]))
        assert returned == good

    def test_hostile_str_subclass_traversal_is_refused(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_dir(
                _EvilStr(os.path.join(restricted_sandbox, "..", "..", "etc"))
            )
