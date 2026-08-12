import os
import subprocess
from unittest import mock

import pytest

import nltk.internals
from nltk.internals import UntrustedJarError, _verify_jar_sandbox, java


def test_java_call_options_do_not_mutate_global_java_options(tmp_path):
    with mock.patch.dict(os.environ, {"NLTK_ALLOW_UNSAFE_JARS": "1"}), mock.patch(
        "nltk.data.path", [str(tmp_path)]
    ), mock.patch.object(nltk.internals, "_java_bin", ["java"]), mock.patch.object(
        nltk.internals, "_java_options", ["-XmxGLOBAL"]
    ):

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
                options="-XmxLOCAL -verbose:gc",
            )

        expected = ["java", "-XmxLOCAL", "-verbose:gc", "-cp", "example.jar", "Main"]
        assert captured_cmd[0] == expected
        assert nltk.internals._java_options == ["-XmxGLOBAL"]


def test_cwe94_jar_sandbox_allows_safe_paths_string(tmp_path):
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar = models_dir / "stanford.jar"
    safe_jar.touch()
    with mock.patch("nltk.data.path", [str(data_dir)]):
        _verify_jar_sandbox(str(safe_jar))


def test_cwe94_jar_sandbox_allows_safe_paths_tuple(tmp_path):
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar1 = models_dir / "stanford1.jar"
    safe_jar1.touch()
    safe_jar2 = models_dir / "stanford2.jar"
    safe_jar2.touch()
    with mock.patch("nltk.data.path", [str(data_dir)]):
        _verify_jar_sandbox((str(safe_jar1), str(safe_jar2)))


def test_cwe94_jar_sandbox_allows_safe_paths_list(tmp_path):
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    models_dir = data_dir / "models"
    models_dir.mkdir()
    safe_jar1 = models_dir / "stanford1.jar"
    safe_jar1.touch()
    safe_jar2 = models_dir / "stanford2.jar"
    safe_jar2.touch()
    with mock.patch("nltk.data.path", [str(data_dir)]):
        _verify_jar_sandbox([str(safe_jar1), str(safe_jar2)])


def test_cwe94_jar_sandbox_blocks_unsafe_absolute_paths(tmp_path):
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    unsafe_jar = tmp_path / "evil.jar"
    unsafe_jar.touch()
    with mock.patch("nltk.data.path", [str(data_dir)]):
        with pytest.raises(UntrustedJarError, match="not in a trusted location"):
            _verify_jar_sandbox(str(unsafe_jar))


def test_cwe94_jar_sandbox_blocks_relative_paths():
    with pytest.raises(
        UntrustedJarError, match="Relative paths are strictly forbidden"
    ):
        _verify_jar_sandbox("relative/path.jar")


def test_cwe94_jar_sandbox_escape_hatch():
    with mock.patch.dict(os.environ, {"NLTK_ALLOW_UNSAFE_JARS": "1"}):
        with pytest.warns(UserWarning, match="Arbitrary JAR execution is permitted"):
            _verify_jar_sandbox("/tmp/evil.jar")


def test_cwe94_jar_sandbox_escape_hatch_must_be_exact_one():
    with mock.patch.dict(os.environ, {"NLTK_ALLOW_UNSAFE_JARS": "0"}):
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox("/tmp/evil.jar")
    with mock.patch.dict(os.environ, {"NLTK_ALLOW_UNSAFE_JARS": "false"}):
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox("/tmp/evil.jar")


def test_java_classpath_sandbox_integration(tmp_path):
    data_dir = tmp_path / "nltk_data"
    data_dir.mkdir()
    safe_jar = data_dir / "safe.jar"
    safe_jar.touch()
    with mock.patch("nltk.data.path", [str(data_dir)]), mock.patch.object(
        nltk.internals, "_java_bin", ["java"]
    ):

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


def test_java_classpath_with_relative_path_and_escape_hatch():
    with mock.patch.dict(
        os.environ, {"NLTK_ALLOW_UNSAFE_JARS": "1"}
    ), mock.patch.object(nltk.internals, "_java_bin", ["java"]):

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
    with pytest.raises(TypeError, match="cmd must be a sequence of strings"):
        java("java -cp foo.jar Main")
