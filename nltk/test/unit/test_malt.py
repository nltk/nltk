import os
from pathlib import Path

import pytest

import nltk.parse.malt as malt
from nltk.parse.malt import MaltParser


def _minimal_malt_parser(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    model_file = model_dir / "model.mco"
    model_file.write_text("dummy model\n", encoding="utf-8")

    working_dir = tmp_path / "work"
    working_dir.mkdir()

    parser = MaltParser.__new__(MaltParser)
    parser._trained = True
    parser.model = str(model_file)
    parser.working_dir = str(working_dir)
    parser.malt_jars = ["dummy-malt.jar"]
    parser.additional_java_args = []
    return parser, model_dir


def _write_minimal_parse(cmd):
    output_path = Path(cmd[cmd.index("-o") + 1])
    output_path.write_text(
        "1\thello\t_\tNN\tNN\t_\t0\tnull\t_\t_\n",
        encoding="utf-8",
    )


def test_malt_parse_uses_subprocess_cwd_without_changing_process_cwd(
    monkeypatch, tmp_path
):
    parser, model_dir = _minimal_malt_parser(tmp_path)
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    monkeypatch.chdir(service_dir)

    def forbidden_chdir(path):
        raise AssertionError(f"os.chdir() should not be called with {path!r}")

    monkeypatch.setattr(malt.os, "chdir", forbidden_chdir)

    captured = {}

    def fake_execute(cmd, verbose=False, cwd=None):
        captured["cwd"] = cwd
        captured["process_cwd"] = os.getcwd()
        captured["input_file"] = Path(cmd[cmd.index("-i") + 1])
        captured["output_file"] = Path(cmd[cmd.index("-o") + 1])
        _write_minimal_parse(cmd)
        return 0

    parser._execute = fake_execute

    graphs = list(parser.parse_tagged_sents([[("hello", "NN")]]))

    assert len(graphs) == 1
    assert captured["cwd"] == str(model_dir)
    assert captured["process_cwd"] == str(service_dir)
    assert os.getcwd() == str(service_dir)
    assert not captured["input_file"].exists()
    assert not captured["output_file"].exists()


def test_malt_parse_cleans_temp_files_and_preserves_cwd_on_execute_exception(
    monkeypatch, tmp_path
):
    parser, model_dir = _minimal_malt_parser(tmp_path)
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    monkeypatch.chdir(service_dir)

    captured = {}

    def fake_execute(cmd, verbose=False, cwd=None):
        captured["cwd"] = cwd
        captured["process_cwd"] = os.getcwd()
        captured["input_file"] = Path(cmd[cmd.index("-i") + 1])
        captured["output_file"] = Path(cmd[cmd.index("-o") + 1])
        assert captured["input_file"].exists()
        assert captured["output_file"].exists()
        raise RuntimeError("forced parser failure")

    parser._execute = fake_execute

    with pytest.raises(RuntimeError, match="forced parser failure"):
        list(parser.parse_tagged_sents([[("hello", "NN")]]))

    assert captured["cwd"] == str(model_dir)
    assert captured["process_cwd"] == str(service_dir)
    assert os.getcwd() == str(service_dir)
    assert not captured["input_file"].exists()
    assert not captured["output_file"].exists()
