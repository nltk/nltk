import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from nltk.downloader import ErrorMessage, _unzip_iter, _validate_member


def _make_zip(file_path: Path, members: dict[str, bytes]) -> None:
    """
    Create a ZIP file at file_path, with the given arcname->content mapping.
    """
    with zipfile.ZipFile(file_path, "w") as zf:
        for arcname, content in members.items():
            zf.writestr(arcname, content)


def _run_unzip_iter(zip_path: Path, extract_root: Path, verbose: bool = False):
    """
    Convenience wrapper that runs _unzip_iter and returns the list of yielded
    messages (if any).
    """
    return list(_unzip_iter(str(zip_path), str(extract_root), verbose=verbose))


def _assert_blocked(messages, *expected_substrings):
    """Assert that *messages* contain at least one ``ErrorMessage`` whose
    text includes every string in *expected_substrings*."""
    err_msgs = [m for m in messages if isinstance(m, ErrorMessage)]
    assert err_msgs, f"Expected ErrorMessage(s) containing {expected_substrings!r}"
    combined = " ".join(str(m.message) for m in err_msgs)
    for s in expected_substrings:
        assert s in combined, f"Expected {s!r} in error output: {combined}"
    return err_msgs


class TestSecureUnzip:
    """
    Tests for the validate-then-extract strategy in ``_unzip_iter``.

    The implementation scans every member for security violations (path
    traversal, absolute paths, symlink escapes, null bytes) *before*
    extracting anything.  If any member fails validation the entire archive
    is rejected and nothing is written to disk.
    """

    def test_normal_relative_paths_are_extracted(self, tmp_path: Path) -> None:
        """
        A ZIP with only safe, relative paths should fully extract under the
        given root, and should not yield any ErrorMessage.
        """
        zip_path = tmp_path / "safe.zip"
        extract_root = tmp_path / "extract"

        members = {
            "pkg/file.txt": b"hello",
            "pkg/subdir/other.txt": b"world",
        }
        _make_zip(zip_path, members)

        messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        assert not any(isinstance(m, ErrorMessage) for m in messages)

        assert (extract_root / "pkg" / "file.txt").read_bytes() == b"hello"
        assert (extract_root / "pkg" / "subdir" / "other.txt").read_bytes() == b"world"

    def test_zip_slip_with_parent_directory_component_is_blocked(
        self, tmp_path: Path
    ) -> None:
        """
        An entry containing ``..`` that would escape the target directory
        must not be written outside the extraction root, and must cause
        _unzip_iter to yield an ErrorMessage.

        The entire archive is rejected: even safe entries must NOT be
        extracted when any member fails validation.
        """
        zip_path = tmp_path / "zip_slip_parent.zip"
        extract_root = tmp_path / "extract"

        outside_target = (extract_root / ".." / "outside.txt").resolve()

        members = {
            "pkg/good.txt": b"ok",
            "../outside.txt": b"evil",
        }
        _make_zip(zip_path, members)

        messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        _assert_blocked(messages, "Zip Slip", "blocked")
        assert not outside_target.exists()

        # Fail-fast: nothing should be extracted from a malicious archive.
        assert not (extract_root / "pkg" / "good.txt").exists()

    @pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="Absolute POSIX paths are not meaningful on Windows",
    )
    def test_zip_slip_with_absolute_posix_path_is_blocked(self, tmp_path: Path) -> None:
        """
        An entry with an absolute POSIX path (e.g. ``/tmp/evil``) must not be
        extracted as-is; it should not overwrite arbitrary filesystem paths,
        and should result in an ErrorMessage.

        The entire archive is rejected when any member fails validation.
        """
        zip_path = tmp_path / "zip_slip_abs_posix.zip"
        extract_root = tmp_path / "extract"

        absolute_target = Path("/tmp") / f"nltk_zip_slip_test_{os.getpid()}"

        try:
            members = {
                "pkg/good.txt": b"ok",
                str(absolute_target): b"evil",
            }
            _make_zip(zip_path, members)

            messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

            _assert_blocked(messages, "Zip Slip", "blocked")

            assert not absolute_target.exists()

            # Fail-fast: nothing should be extracted from a malicious archive.
            assert not (extract_root / "pkg" / "good.txt").exists()
        finally:
            if absolute_target.exists():
                try:
                    absolute_target.unlink()
                except OSError:
                    pass

    def test_entries_resolved_outside_root_are_blocked_via_symlink(
        self, tmp_path: Path
    ) -> None:
        """
        If there is a pre-existing symlink below the extraction root that
        points outside the root, writing through that symlink should not
        be allowed to escape the root.

        The entire archive is rejected when any member fails validation.
        """
        if not hasattr(os, "symlink"):
            pytest.skip("Symlinks not supported on this platform")

        zip_path = tmp_path / "zip_slip_symlink.zip"
        extract_root = tmp_path / "extract"
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        outside_target = outside_dir / "evil.txt"

        members = {
            "pkg/good.txt": b"ok",
            "dir_link/evil.txt": b"evil",
        }
        _make_zip(zip_path, members)

        extract_root.mkdir()
        try:
            os.symlink(outside_dir, extract_root / "dir_link")
        except OSError:
            pytest.skip("Symlink creation not permitted on this platform")

        messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        assert not outside_target.exists()
        _assert_blocked(messages, "Symlink escape", "blocked")

        # Fail-fast: nothing should be extracted from a malicious archive.
        assert not (extract_root / "pkg" / "good.txt").exists()

    def test_bad_zipfile_yields_errormessage(self, tmp_path: Path) -> None:
        """
        A corrupt or non-zip file should cause _unzip_iter to yield an
        ErrorMessage instead of raising an unhandled exception.
        """
        zip_path = tmp_path / "not_a_zip.txt"
        zip_path.write_bytes(b"this is not a zip archive")
        extract_root = tmp_path / "extract"

        messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        assert any(isinstance(m, ErrorMessage) for m in messages)

        if extract_root.exists():
            assert not any(extract_root.iterdir())

    def test_null_byte_in_member_name_is_blocked(self, tmp_path: Path) -> None:
        """
        A member name containing a null byte must be rejected.  Null bytes
        can cause path truncation on some platforms, so they are never
        legitimate in archive entry names.

        The entire archive is rejected when any member fails validation.

        Note: CPython's zipfile module truncates names at null bytes on
        read, so we patch ``namelist()`` to simulate a library that
        preserves them.
        """
        zip_path = tmp_path / "null_byte.zip"
        extract_root = tmp_path / "extract"

        _make_zip(zip_path, {"pkg/good.txt": b"ok", "pkg/evil.txt": b"evil"})

        poisoned_names = ["pkg/good.txt", "pkg/evil\x00.txt"]

        with patch(
            "nltk.downloader.zipfile.ZipFile.namelist",
            return_value=poisoned_names,
        ), patch(
            "nltk.downloader.zipfile.ZipFile.extract",
        ) as mock_extract:
            messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        _assert_blocked(messages, "Null byte", "blocked")
        mock_extract.assert_not_called()

        assert not (extract_root / "pkg" / "good.txt").exists()

    @pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="Absolute POSIX paths are not meaningful on Windows",
    )
    def test_multiple_violation_types_all_reported_and_nothing_extracted(
        self, tmp_path: Path
    ) -> None:
        """
        An archive that combines several different violation types (path
        traversal and absolute path) must report every violation and
        extract nothing.  This verifies that the validation scan does not
        short-circuit after the first bad entry.
        """
        zip_path = tmp_path / "multi_violation.zip"
        extract_root = tmp_path / "extract"

        absolute_target = Path("/tmp") / f"nltk_multi_viol_test_{os.getpid()}"

        try:
            members = {
                "data/a.txt": b"aaa",
                "../traversal.txt": b"evil1",
                str(absolute_target): b"evil2",
                "data/b.txt": b"bbb",
            }
            _make_zip(zip_path, members)

            messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

            err_msgs = _assert_blocked(messages, "Zip Slip")
            assert len(err_msgs) >= 2, "Expected at least two ErrorMessages"

            assert not absolute_target.exists()

            if extract_root.exists():
                assert not any(extract_root.iterdir())
        finally:
            if absolute_target.exists():
                try:
                    absolute_target.unlink()
                except OSError:
                    pass

    def test_extraction_error_does_not_delete_preexisting_root_content(
        self, tmp_path: Path
    ) -> None:
        """
        If extraction fails mid-stream, pre-existing content under the
        extraction root must be preserved.
        """
        zip_path = tmp_path / "extract_error.zip"
        extract_root = tmp_path / "extract"
        existing_file = extract_root / "already_there.txt"

        _make_zip(zip_path, {"pkg/file.txt": b"data"})
        extract_root.mkdir()
        existing_file.write_bytes(b"keep-me")

        with patch(
            "nltk.downloader.zipfile.ZipFile.extract",
            side_effect=OSError("simulated extraction failure"),
        ):
            messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        _assert_blocked(messages, "Extraction error")

        assert existing_file.read_bytes() == b"keep-me"

    def test_namelist_raises_yields_errormessage(self, tmp_path: Path) -> None:
        """
        If ``zf.namelist()`` itself raises (e.g. corrupted central directory),
        an ErrorMessage must be yielded and the zip file must be closed.
        """
        zip_path = tmp_path / "namelist_bomb.zip"
        extract_root = tmp_path / "extract"

        _make_zip(zip_path, {"pkg/file.txt": b"data"})

        with patch(
            "nltk.downloader.zipfile.ZipFile.namelist",
            side_effect=RuntimeError("corrupted central directory"),
        ):
            messages = _run_unzip_iter(zip_path, extract_root, verbose=False)

        _assert_blocked(messages, "corrupted central directory")

        if extract_root.exists():
            assert not any(extract_root.iterdir())

    def test_unzip_iter_verbose_writes_to_stdout(self, capsys, tmp_path: Path) -> None:
        """
        When verbose=True, _unzip_iter should write a status line to stdout.
        This checks that existing user-visible behaviour is preserved.
        """
        zip_path = tmp_path / "verbose.zip"
        extract_root = tmp_path / "extract"

        members = {"pkg/file.txt": b"data"}
        _make_zip(zip_path, members)

        _run_unzip_iter(zip_path, extract_root, verbose=True)
        captured = capsys.readouterr()
        assert "Unzipping" in captured.out

    def test_verbose_output_on_corrupt_zip(self, capsys, tmp_path: Path) -> None:
        """
        When verbose=True and the file is not a valid zip, the output line
        must still be terminated with a newline so the terminal is left in
        a clean state.
        """
        zip_path = tmp_path / "corrupt.txt"
        zip_path.write_bytes(b"not a zip")
        extract_root = tmp_path / "extract"

        _run_unzip_iter(zip_path, extract_root, verbose=True)
        captured = capsys.readouterr()
        assert "Unzipping" in captured.out
        assert captured.out.endswith("\n")


class TestValidateMember:
    """Direct unit tests for ``_validate_member`` path validation logic."""

    def test_safe_relative_path_passes(self, tmp_path):
        root = str(tmp_path / "root")
        assert _validate_member("pkg/file.txt", root) is None

    def test_parent_traversal_blocked(self, tmp_path):
        root = str(tmp_path / "root")
        result = _validate_member("../evil.txt", root)
        assert result is not None and "Zip Slip" in result

    def test_deeply_nested_traversal_blocked(self, tmp_path):
        root = str(tmp_path / "root")
        result = _validate_member("a/b/c/../../../../evil.txt", root)
        assert result is not None and "Zip Slip" in result

    def test_null_byte_blocked(self, tmp_path):
        root = str(tmp_path / "root")
        result = _validate_member("pkg/evil\x00.txt", root)
        assert result is not None and "Null byte" in result

    @pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="Absolute POSIX paths are not meaningful on Windows",
    )
    def test_absolute_posix_path_blocked(self, tmp_path):
        root = str(tmp_path / "root")
        result = _validate_member("/etc/passwd", root)
        assert result is not None and "Zip Slip" in result

    @pytest.mark.skipif(
        not sys.platform.startswith("win"),
        reason="Drive-letter paths are only meaningful on Windows",
    )
    def test_windows_drive_letter_blocked(self, tmp_path):
        root = str(tmp_path / "root")
        result = _validate_member("C:\\Windows\\evil.txt", root)
        assert result is not None and "Zip Slip" in result

    def test_backslash_traversal(self, tmp_path):
        """On Windows, backslash is a path separator so ``..\\evil.txt``
        is a traversal attack.  On POSIX, backslash is a literal filename
        character and the member name is harmless."""
        root = str(tmp_path / "root")
        result = _validate_member("..\\evil.txt", root)
        if sys.platform.startswith("win"):
            assert result is not None and "Zip Slip" in result
        else:
            assert result is None

    def test_normcase_is_applied_to_path_comparisons(self, tmp_path):
        """Simulate case-folding normcase (as on Windows) to verify that
        _validate_member applies it to both target and prefix paths."""
        root = str(tmp_path / "Root")
        original_normcase = os.path.normcase

        def case_folding_normcase(p):
            return original_normcase(p).lower()

        with patch(
            "nltk.downloader.os.path.normcase",
            side_effect=case_folding_normcase,
        ):
            assert _validate_member("pkg/file.txt", root) is None

            result = _validate_member("../evil.txt", root)
            assert result is not None and "Zip Slip" in result
