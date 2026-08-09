import os
import subprocess
from unittest import mock

import pytest

import nltk.internals
from nltk.internals import UntrustedJarError, _verify_jar_sandbox, java


def test_java_call_options_do_not_mutate_global_java_options(monkeypatch, tmp_path):
    """Test that local options do not mutate global _java_options."""
    monkeypatch.setenv("NLTK_ALLOW_UNSAFE_JARS", "1")
    monkeypatch.setattr("nltk.data.path", [str(tmp_path)])

    # Patch the global options via module attribute – we'll check it later
    monkeypatch.setattr("nltk.internals._java_options", ["-XmxGLOBAL"])

    captured_cmd = []

    def fake_popen(cmd, *args, **kwargs):
        captured_cmd.append(cmd)
        dummy = mock.MagicMock()
        dummy.returncode = 0
        dummy.communicate.return_value = ("", "")
        return dummy

    with mock.patch.object(subprocess, "Popen", side_effect=fake_popen):
        java(
            ["Main"],
            classpath="example.jar",
            stdout="pipe",
            stderr="pipe",
            options="-XmxLOCAL -Dexample=true",
        )

    expected = ["java", "-XmxLOCAL", "-Dexample=true", "-cp", "example.jar", "Main"]
    assert captured_cmd[0] == expected

    # Access the patched value via the module to ensure it wasn't mutated
    assert nltk.internals._java_options == ["-XmxGLOBAL"]


def test_cwe94_jar_sandbox_allows_safe_paths_string(monkeypatch, tmp_path):
    """Verify that a string absolute path inside nltk_data is permitted."""
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar = models_dir / "stanford.jar"
    safe_jar.touch()
    monkeypatch.setattr("nltk.data.path", [str(data_dir)])

    _verify_jar_sandbox(str(safe_jar))  # string input


def test_cwe94_jar_sandbox_allows_safe_paths_tuple(monkeypatch, tmp_path):
    """Verify that a tuple of absolute paths inside nltk_data is permitted."""
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar1 = models_dir / "stanford1.jar"
    safe_jar1.touch()
    safe_jar2 = models_dir / "stanford2.jar"
    safe_jar2.touch()
    monkeypatch.setattr("nltk.data.path", [str(data_dir)])

    _verify_jar_sandbox((str(safe_jar1), str(safe_jar2)))  # tuple input


def test_cwe94_jar_sandbox_blocks_unsafe_absolute_paths(monkeypatch, tmp_path):
    """Verify that absolute paths outside nltk_data are blocked."""
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    monkeypatch.setattr("nltk.data.path", [str(data_dir)])

    unsafe_jar = tmp_path / "evil.jar"
    unsafe_jar.touch()

    with pytest.raises(UntrustedJarError, match="not in a trusted location"):
        _verify_jar_sandbox(str(unsafe_jar))


def test_cwe94_jar_sandbox_blocks_relative_paths():
    """Verify that relative paths are rejected."""
    with pytest.raises(
        UntrustedJarError, match="Relative paths are strictly forbidden"
    ):
        _verify_jar_sandbox("relative/path.jar")


def test_cwe94_jar_sandbox_escape_hatch(monkeypatch):
    """Verify that NLTK_ALLOW_UNSAFE_JARS=1 bypasses the check."""
    monkeypatch.setenv("NLTK_ALLOW_UNSAFE_JARS", "1")
    with pytest.warns(UserWarning, match="Arbitrary JAR execution is permitted"):
        _verify_jar_sandbox("/tmp/evil.jar")  # Should not raise


def test_cwe94_jar_sandbox_escape_hatch_must_be_exact_one():
    """Verify that values other than '1' do NOT bypass the sandbox."""
    os.environ["NLTK_ALLOW_UNSAFE_JARS"] = "0"
    with pytest.raises(UntrustedJarError):
        _verify_jar_sandbox("/tmp/evil.jar")
    os.environ["NLTK_ALLOW_UNSAFE_JARS"] = "false"
    with pytest.raises(UntrustedJarError):
        _verify_jar_sandbox("/tmp/evil.jar")
    # Clean up
    os.environ.pop("NLTK_ALLOW_UNSAFE_JARS", None)


def test_java_classpath_sandbox_integration(monkeypatch, tmp_path):
    """Integration test: java() calls the sandbox and builds the command correctly."""
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    safe_jar = data_dir / "safe.jar"
    safe_jar.touch()
    monkeypatch.setattr("nltk.data.path", [str(data_dir)])

    captured_cmd = []

    def fake_popen(cmd, *args, **kwargs):
        captured_cmd.append(cmd)
        dummy = mock.MagicMock()
        dummy.returncode = 0
        dummy.communicate.return_value = ("", "")
        return dummy

    with mock.patch.object(subprocess, "Popen", side_effect=fake_popen):
        java(["Main"], classpath=str(safe_jar))

    expected = ["java", "-cp", str(safe_jar), "Main"]
    assert captured_cmd[0] == expected


def test_java_classpath_with_relative_path_and_escape_hatch(monkeypatch):
    """When escape hatch is set, relative paths are passed through unchanged."""
    monkeypatch.setenv("NLTK_ALLOW_UNSAFE_JARS", "1")
    captured_cmd = []

    def fake_popen(cmd, *args, **kwargs):
        captured_cmd.append(cmd)
        dummy = mock.MagicMock()
        dummy.returncode = 0
        dummy.communicate.return_value = ("", "")
        return dummy

    with mock.patch.object(subprocess, "Popen", side_effect=fake_popen):
        java(["Main"], classpath="relative.jar")

    expected = ["java", "-cp", "relative.jar", "Main"]
    assert captured_cmd[0] == expected


def test_java_command_string_raises_type_error():
    """Ensure that passing a string as cmd raises TypeError."""
    with pytest.raises(TypeError, match="cmd must be a sequence of strings"):
        java("java -cp foo.jar Main")


def test_cwe94_jar_sandbox_allows_safe_paths_list(monkeypatch, tmp_path):
    """Verify that a list of absolute paths inside nltk_data is permitted."""
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar1 = models_dir / "stanford1.jar"
    safe_jar1.touch()
    safe_jar2 = models_dir / "stanford2.jar"
    safe_jar2.touch()
    monkeypatch.setattr("nltk.data.path", [str(data_dir)])

    _verify_jar_sandbox([str(safe_jar1), str(safe_jar2)])  # list input
