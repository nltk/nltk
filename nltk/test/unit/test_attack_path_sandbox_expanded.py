# Natural Language Toolkit: expanded path-traversal / sandbox-escape attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded attack matrix for the ``nltk.pathsec`` filesystem sandbox
(GHSA-8mgp-746c-j5xp umbrella, #3753; CWE-22 / CWE-59 / CWE-377 / CWE-378 /
CWE-400 / CWE-409).

This file adds the path-escape vectors that the existing suites
(``test_pathsec.py``, ``test_pathsec_io_attack_matrix.py``,
``test_path_traversal_security.py``, ``test_corpus_reader_traversal.py``,
``test_downloader_package_traversal.py``, the zip suites, ...) do NOT yet cover.
It deliberately avoids duplicating them; each case here is net-new:

* redundant-segment / lookalike shapes that must NOT collapse into a traversal
  (``....//``, unicode dot lookalikes U+2024/U+2025/U+FF0E, a trailing ``foo/..``,
  a single payload interleaving forward and back slashes);
* the reserved-device names ``CONIN$`` / ``CONOUT$`` and the ``\\\\?\\``
  extended-length / ``\\\\?\\UNC\\`` Windows spellings;
* a block special file (``S_IFBLK``) at the non-regular-file guard;
* a world-writable ANCESTOR and the staging-directory REUSE guard;
* a single over-expanding zip member reaching the per-member read/open cutoff
  (the aggregate and gzip bombs are covered elsewhere, this one is not);
* benign controls the guards must still ACCEPT (a unicode filename read/write
  round trip, a name merely *starting* like a device, the lookalike shapes as
  literal in-root names).

Every hostile vector must be REFUSED (``PermissionError`` / ``ValueError``); every
benign in-root vector must SUCCEED, and no attack may read or write outside the
data root (asserted against a sentinel). POSIX-only vectors (symlink / block
device / mode bits / staging reuse) are ``skipif``-guarded; the Windows string
rules are proved cross-platform by driving the pure ``_reject_bad_name_syntax``
predicate under a faked ``os.name`` (the same technique
``test_zip_member_platform_rules.py`` uses for ``os.path.altsep``), and also run
for real on a Windows runner.

Outside targets are staged under the real ``$HOME`` (never a temp dir, which is
itself an allowed root on macOS) via the conftest ``sandbox`` / ``pathsec_sandbox``
fixtures.
"""

import os
import stat
import tempfile
import zipfile

import pytest

import nltk.data
from nltk import pathsec
from nltk.pathsec import (
    _reject_aliased_or_special,
    _reject_bad_name_syntax,
    is_private_dir,
    validate_model_resource,
    validate_tool_dir,
    validate_tool_path,
)

REFUSALS = (PermissionError, ValueError)

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="symlink / block device / mode bits / staging reuse are POSIX vectors",
)
WINDOWS_ONLY = pytest.mark.skipif(
    os.name == "posix",
    reason="reserved device / extended-length paths are Windows vectors",
)


def _resolve(path):
    return os.path.realpath(str(path))


def _under(path, root):
    """True if *path* resolves to *root* or strictly inside it."""
    root_r = _resolve(root)
    target = _resolve(path)
    return target == root_r or target.startswith(root_r + os.sep)


# ==========================================================================
# 1. Redundant-segment / dot-lookalike shapes must NOT collapse to a traversal
# ==========================================================================
# ``....//`` and the unicode dot lookalikes are NOT ``..``: a filter that strips
# ``../`` in a single pass would turn ``....//`` into ``../``, and a normalizer
# that folded U+2024/U+FF0E to ``.`` would turn ``\u2024\u2024`` into ``..``.
# NLTK does neither; it splits on the real separator and compares whole
# components, so at the tool layer these stay LITERAL in-root names (accepted,
# proven to resolve inside the root, never above it); at the data-resource layer
# they are refused or not-found. Both outcomes prove the shape never becomes an
# escape.

# (id, literal spelling of the leaf/prefix that must stay in-root). These are
# distinct unicode characters (not ASCII dots), so they are ordinary literal
# names on every platform. The ASCII "....//" spelling is posix-only (a name of
# all dots is degenerate on Windows, where trailing dots are stripped), so it is
# covered by test_dotdotdotdot_stays_literal_in_root_on_posix below instead.
_LOOKALIKE_COMPONENTS = [
    ("one-dot-leader U+2024", "\u2024\u2024/sub"),
    ("two-dot-leader U+2025", "\u2025/sub"),
    ("fullwidth-full-stop U+FF0E", "\uff0e\uff0e/sub"),
]


class TestLookalikesStayLiteralInRoot:
    @pytest.mark.parametrize(
        "spelling",
        [s for _, s in _LOOKALIKE_COMPONENTS],
        ids=[i for i, _ in _LOOKALIKE_COMPONENTS],
    )
    def test_tool_dir_keeps_lookalike_inside_root(self, restricted_sandbox, spelling):
        # Accepted as a literal name, and (the security property) its resolved
        # location is INSIDE the root, i.e. it did not collapse into ``../``.
        candidate = os.path.join(restricted_sandbox, spelling)
        returned = validate_tool_dir(candidate)
        assert _under(
            returned, restricted_sandbox
        ), f"lookalike {spelling!r} escaped the root: {_resolve(returned)!r}"

    @pytest.mark.parametrize(
        "spelling",
        [s for _, s in _LOOKALIKE_COMPONENTS],
        ids=[i for i, _ in _LOOKALIKE_COMPONENTS],
    )
    def test_model_resource_keeps_lookalike_inside_root(
        self, restricted_sandbox, spelling
    ):
        # A real file at the lookalike name is bounded to the root, not escaped.
        directory = os.path.join(restricted_sandbox, spelling)
        os.makedirs(directory, exist_ok=True)
        target = os.path.join(directory, "model.bin")
        open(target, "w").close()
        returned = validate_model_resource(target)
        assert _under(returned, restricted_sandbox)

    @POSIX_ONLY
    def test_dotdotdotdot_stays_literal_in_root_on_posix(self, restricted_sandbox):
        # On posix "...." is an ordinary four-dot directory name, so "....//sub"
        # is a literal path kept inside the root, not a "../" traversal. On
        # Windows a name of all dots is degenerate (trailing dots are stripped)
        # so the guard may refuse it there; the data-layer refusal is pinned by
        # test_dotdotdotdot_slash_is_refused_at_the_data_layer below.
        candidate = os.path.join(restricted_sandbox, "....//sub")
        assert _under(validate_tool_dir(candidate), restricted_sandbox)
        directory = os.path.join(restricted_sandbox, "....//sub")
        os.makedirs(directory, exist_ok=True)
        target = os.path.join(directory, "model.bin")
        open(target, "w").close()
        assert _under(validate_model_resource(target), restricted_sandbox)


class TestTraversalShapesRefused:
    """Shapes that ARE a traversal (or an out-of-namespace escape) and must be
    refused by the tool guards; net-new spellings not in the existing matrix."""

    def test_trailing_dotdot_is_refused(self, restricted_sandbox):
        # ``<root>/sub/..``: a trailing ``..`` component climbs back to <root>,
        # the ``..`` component check refuses it regardless of where it lands.
        with pytest.raises(REFUSALS):
            validate_tool_path(
                os.path.join(restricted_sandbox, "sub", ".."),
                must_exist=False,
            )

    def test_mixed_forward_and_back_slash_traversal_is_refused(
        self, restricted_sandbox
    ):
        # A single payload interleaving ``/`` and ``\\``: the ``..`` check folds
        # ``\\`` to ``/`` first, so the backslash-hidden ``..`` is still caught.
        with pytest.raises(REFUSALS):
            validate_tool_path(
                restricted_sandbox + "/..\\..\\etc/passwd",
                must_exist=False,
            )

    def test_dotdotdotdot_slash_is_refused_at_the_data_layer(self, monkeypatch):
        # The data-resource layer (url2pathname pipeline) is stricter than the
        # tool layer: ``....//`` is refused outright there. Pin it so a future
        # single-pass ``../``-stripping normalizer that turned it into ``../``
        # would surface here.
        import nltk.data as D

        with pytest.raises((ValueError, LookupError)):
            D.find("....//secret.txt")


# ==========================================================================
# 2. No crafted / lookalike name reads a sentinel above an isolated data root
# ==========================================================================


def test_no_lookalike_payload_reads_a_sentinel_outside_the_root():
    """End-to-end no-leak property for the lookalike shapes: plant a secret above
    an isolated data root and confirm no ``....//`` / unicode-dot spelling reads
    it, whether it is refused, collapsed, or kept as an in-root literal."""
    base = tempfile.mkdtemp(prefix=".nltk_look_", dir=os.path.expanduser("~"))
    try:
        dataroot = os.path.join(base, "nltk_data")
        os.makedirs(dataroot)
        with open(os.path.join(base, "secret.txt"), "w") as handle:
            handle.write("TOP-SECRET-LOOKALIKE")

        payloads = [
            "....//secret.txt",
            "....//....//secret.txt",
            "\u2024\u2024/secret.txt",
            "\u2025/secret.txt",
            "\uff0e\uff0e/secret.txt",
            "..\u2044secret.txt",  # U+2044 FRACTION SLASH, not a separator
        ]
        saved = list(nltk.data.path)
        nltk.data.path.insert(0, dataroot)
        try:
            for payload in payloads:
                try:
                    pointer = nltk.data.find(payload)
                    content = pointer.open().read()
                except Exception:
                    # Any refusal / not-found / decode error means no readable
                    # file resolved; no leak.
                    continue
                if isinstance(content, bytes):
                    content = content.decode("latin-1", "replace")
                assert "TOP-SECRET" not in content, f"lookalike leak via {payload!r}"
        finally:
            nltk.data.path[:] = saved
    finally:
        import shutil

        shutil.rmtree(base, ignore_errors=True)


# ==========================================================================
# 3. Windows reserved-device and extended-length spellings
# ==========================================================================
# The string rules live in the pure ``_reject_bad_name_syntax`` predicate, so they
# can be proved on any platform by faking ``os.name`` (the predicate does no
# filesystem I/O). The WINDOWS_ONLY variants additionally exercise the real
# end-to-end guard on a Windows runner.


def _syntax_verdict(value, faked_os_name):
    """Run the pure name-syntax predicate under a faked ``os.name``.

    Returns True if REFUSED, False if accepted. Restores ``os.name`` always.
    """
    saved = pathsec.os.name
    pathsec.os.name = faked_os_name
    try:
        _reject_bad_name_syntax(value, "NLTK tool", error=PermissionError)
        return False
    except REFUSALS:
        return True
    finally:
        pathsec.os.name = saved


class TestWindowsDeviceAndExtendedNames:
    @pytest.mark.parametrize("device", ["CONIN$", "CONOUT$"])
    def test_conin_conout_are_refused_under_windows_rules(self, device):
        # Present in pathsec._WINDOWS_DEVICE_NAMES but never exercised before.
        assert _syntax_verdict(f"sub/{device}", "nt") is True
        assert _syntax_verdict(f"sub/{device}.txt", "nt") is True

    @pytest.mark.parametrize("device", ["CONIN$", "CONOUT$"])
    def test_conin_conout_are_ordinary_names_on_posix(self, device):
        # Teeth / over-block control: on POSIX these are legal filenames, so the
        # guard must NOT refuse them (refusing everywhere would break real data).
        assert _syntax_verdict(f"sub/{device}", "posix") is False

    @pytest.mark.parametrize(
        "spelling",
        ["\\\\?\\C:\\Windows\\win.ini", "\\\\?\\UNC\\server\\share\\x", "//?/C:/x"],
        ids=["ext-len-drive", "ext-len-unc", "ext-len-forward"],
    )
    def test_extended_length_paths_are_refused_on_every_platform(self, spelling):
        # ``\\?\`` and ``//?/`` begin with a UNC-shaped double separator, so they
        # are refused under BOTH platform rule sets (not merely Windows).
        assert _syntax_verdict(spelling, "nt") is True
        assert _syntax_verdict(spelling, "posix") is True

    def test_benign_name_starting_like_a_device_is_accepted(self):
        # ``CONtext`` merely starts like ``CON``; it is a real name, accepted on
        # both platforms (the device check is on the whole stem, not a prefix).
        assert _syntax_verdict("sub/CONtext.bin", "nt") is False
        assert _syntax_verdict("sub/CONtext.bin", "posix") is False

    def test_benign_windows_drive_absolute_passes_syntax(self):
        # Over-block control: a full drive-qualified Windows path is a legal
        # spelling (containment, not syntax, decides it), so syntax must accept it.
        assert _syntax_verdict("C:\\models\\english.bin", "nt") is False

    @WINDOWS_ONLY
    @pytest.mark.parametrize("device", ["CONIN$", "CONOUT$"])
    def test_conin_conout_are_refused_end_to_end_on_windows(
        self, restricted_sandbox, device
    ):
        with pytest.raises(REFUSALS):
            validate_tool_dir(os.path.join(restricted_sandbox, device))

    @WINDOWS_ONLY
    def test_extended_length_is_refused_end_to_end_on_windows(self):
        with pytest.raises(REFUSALS):
            validate_tool_path("\\\\?\\C:\\Windows\\win.ini")


# ==========================================================================
# 4. A block special file (S_IFBLK) at the non-regular-file guard
# ==========================================================================


def _find_block_device():
    """An existing block-special file under /dev, or None."""
    candidates = [
        "/dev/disk0",  # macOS
        "/dev/sda",
        "/dev/vda",
        "/dev/loop0",
        "/dev/nvme0n1",
    ]
    for candidate in candidates:
        try:
            if stat.S_ISBLK(os.stat(candidate).st_mode):
                return candidate
        except OSError:
            continue
    try:
        for name in os.listdir("/dev"):
            path = os.path.join("/dev", name)
            try:
                if stat.S_ISBLK(os.lstat(path).st_mode):
                    return path
            except OSError:
                continue
    except OSError:
        pass
    return None


@POSIX_ONLY
class TestBlockDeviceRefused:
    def test_block_device_is_not_a_regular_file_or_directory(self):
        # Only char devices (/dev/null) were exercised before. A block device
        # must hit the same non-regular-file refusal (reading it could block or
        # stream unbounded data, CWE-400).
        device = _find_block_device()
        if device is None:
            pytest.skip("no block device available on this host")
        with pytest.raises(PermissionError):
            _reject_aliased_or_special(device, "NLTK tool")

    def test_a_regular_file_passes_the_same_guard(self, restricted_sandbox):
        # Over-block control: the guard must accept an ordinary file.
        target = os.path.join(restricted_sandbox, "plain.bin")
        open(target, "w").close()
        _reject_aliased_or_special(target, "NLTK tool")  # must not raise


# ==========================================================================
# 5. World-writable ANCESTOR and the staging-directory REUSE guard
# ==========================================================================


@POSIX_ONLY
class TestWorldWritableAncestorAndStagingReuse:
    def test_is_private_dir_rejects_group_and_world_writable(self, restricted_sandbox):
        # The primitive behind "do not reuse a squattable directory". Existing
        # tests cover the system-temp path; here it is a data-root subdir.
        world = os.path.join(restricted_sandbox, "world")
        os.makedirs(world)
        os.chmod(world, 0o777)
        assert is_private_dir(world) is False
        group = os.path.join(restricted_sandbox, "group")
        os.makedirs(group)
        os.chmod(group, 0o770)
        assert is_private_dir(group) is False
        private = os.path.join(restricted_sandbox, "private")
        os.makedirs(private)
        os.chmod(private, 0o700)
        assert is_private_dir(private) is True  # teeth: 0700 is trusted

    def test_staging_reuse_discards_a_dir_that_became_world_writable(
        self, restricted_sandbox
    ):
        # A cached staging dir that has since turned world-writable is a squat
        # target (CWE-377/378); the re-check must discard it. This is the
        # "world-writable ancestor reuse" scenario.
        staging = os.path.join(restricted_sandbox, "staging")
        os.makedirs(staging, mode=0o700)
        assert nltk.data._staging_dir_is_still_safe(staging) is True
        os.chmod(staging, 0o777)
        assert nltk.data._staging_dir_is_still_safe(staging) is False

    def test_staging_reuse_discards_a_symlink_swapped_in_its_place(
        self, restricted_sandbox
    ):
        # os.path.isdir would FOLLOW a swapped symlink; the lstat-based re-check
        # must reject it so later scratch files do not land where the link points.
        staging = os.path.join(restricted_sandbox, "swap")
        os.makedirs(staging, mode=0o700)
        real = os.path.join(restricted_sandbox, "elsewhere")
        os.makedirs(real)
        os.rmdir(staging)
        os.symlink(real, staging)
        assert nltk.data._staging_dir_is_still_safe(staging) is False

    def test_benign_write_under_a_world_writable_ancestor_stays_in_root(
        self, pathsec_sandbox
    ):
        # A world-writable ANCESTOR does not by itself statically escape the root
        # (the runtime defense is the O_NOFOLLOW open, exercised elsewhere): a
        # benign write beneath it must still land INSIDE the root and never leak
        # to the outside sentinel.
        root, outside = pathsec_sandbox
        sentinel = outside / "SENTINEL"
        sentinel.write_text("UNCHANGED")
        ancestor = root / "wwanc"
        ancestor.mkdir()
        os.chmod(ancestor, 0o777)
        target = ancestor / "child" / "model.json"
        target.parent.mkdir()
        with pathsec.open(str(target), "w", required_root=str(root)) as handle:
            handle.write("PAYLOAD")
        assert _under(str(target), str(root))
        assert target.read_text() == "PAYLOAD"
        assert sentinel.read_text() == "UNCHANGED", "write leaked outside the root"


# ==========================================================================
# 6. A single over-expanding zip member reaches the per-member read/open cutoff
# ==========================================================================
# The aggregate (`_check_zip_total_size`), central-directory (`_check_zip_member_count`)
# and gzip bombs are covered elsewhere. A SINGLE-member archive skips the
# aggregate guard at construction, so it isolates the per-member read/open cutoff
# on ``pathsec.ZipFile.read`` / ``.open``; the path no in-scope test exercised.


def _single_member_bomb(root, name="bomb.zip"):
    archive = os.path.join(str(root), name)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("bomb.bin", b"\0" * (64 * 1024 * 1024))
    return archive


class TestSingleZipMemberBomb:
    def test_single_member_bomb_construction_passes_but_read_is_refused(
        self, restricted_sandbox
    ):
        archive = _single_member_bomb(restricted_sandbox)
        # A single file member skips the aggregate total-size guard, so the
        # ZipFile constructs fine; the refusal must come from the per-member read.
        with pathsec.ZipFile(archive) as handle, pytest.raises(REFUSALS):
            handle.read("bomb.bin")

    def test_single_member_bomb_open_stream_is_refused(self, restricted_sandbox):
        archive = _single_member_bomb(restricted_sandbox, "bomb2.zip")
        with pathsec.ZipFile(archive) as handle, pytest.raises(REFUSALS):
            with handle.open("bomb.bin") as stream:
                stream.read()

    def test_benign_member_still_reads(self, restricted_sandbox):
        # Over-block control: a small member reads through both entry points.
        archive = os.path.join(restricted_sandbox, "good.zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            handle.writestr("hello.txt", b"hello world")
        with pathsec.ZipFile(archive) as handle:
            assert handle.read("hello.txt") == b"hello world"
            with handle.open("hello.txt") as stream:
                assert stream.read() == b"hello world"

    def test_teeth_raising_the_ratio_lets_the_bomb_through(
        self, restricted_sandbox, monkeypatch
    ):
        # Prove the refusal is the ratio guard and nothing incidental: raise
        # MAX_UNZIP_RATIO above the member's expansion and the same read now
        # succeeds (the escape reaches the sink when the guard is relaxed).
        archive = _single_member_bomb(restricted_sandbox, "teeth.zip")
        monkeypatch.setattr(nltk.data, "MAX_UNZIP_RATIO", 10_000_000)
        with pathsec.ZipFile(archive) as handle:
            data = handle.read("bomb.bin")
        assert len(data) == 64 * 1024 * 1024


# ==========================================================================
# 7. Benign controls the guards must still ACCEPT
# ==========================================================================


class TestBenignUnicodeInRoot:
    def test_unicode_filename_read_write_roundtrip(self, restricted_sandbox):
        # A unicode filename inside the root must read and write through the
        # hardened opener and the tool guard (unicode only appeared in the
        # refused collision tests before, never as an accepted name).
        target = os.path.join(restricted_sandbox, "café_模型_naïve.bin")
        with pathsec.open(target, "w", required_root=restricted_sandbox) as handle:
            handle.write("ok")
        assert (
            pathsec.open(target, "r", required_root=restricted_sandbox).read() == "ok"
        )
        assert validate_tool_path(target) == target

    def test_unicode_directory_is_accepted_by_the_dir_guard(self, restricted_sandbox):
        directory = os.path.join(restricted_sandbox, "corpus_ελληνικά")
        os.makedirs(directory)
        assert validate_tool_dir(directory)

    def test_encoded_literal_stays_a_bare_resource_name(self):
        # A percent-encoded name is NOT decoded by the tool layer, so it is
        # handed back as a literal jar-resource name (never a separator).
        assert validate_model_resource("%2e%2e%2fmodel.bin") == "%2e%2e%2fmodel.bin"


# ==========================================================================
# 8. ENFORCE on/off teeth for a containment refusal (net-new spelling)
# ==========================================================================


class TestEnforceTeeth:
    def test_outside_unicode_file_refused_under_enforce_reached_when_off(
        self, sandbox, monkeypatch
    ):
        # An out-of-root regular file with a unicode name: under ENFORCE the tool
        # guard refuses it; with ENFORCE off the containment check no longer
        # raises (the guard has teeth; the refusal is real, not incidental).
        outside_file = os.path.join(str(sandbox), "naïve_secret.bin")
        open(outside_file, "w").close()
        with pytest.raises(REFUSALS):
            validate_tool_path(outside_file)
        # Turn enforcement off and confirm the same call no longer refuses.
        monkeypatch.setattr(pathsec, "ENFORCE", False)
        monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
        monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
        # validate_tool_path returns the checked string (no raise) under ENFORCE off.
        assert validate_tool_path(outside_file) == outside_file
