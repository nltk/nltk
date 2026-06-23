"""Regression test for the pathsec sandbox bypass in
``nltk.parse.dependencygraph.DependencyGraph.load`` (CWE-22; CVE-2026-12867).

``load`` opened the caller-supplied filename with the builtin ``open``, which
bypasses NLTK's centralized file-access sentinel (``nltk.pathsec``). Where an
application enables the sandbox as a boundary and feeds it an attacker-influenced
filename, that allowed arbitrary local files to be read and their parsed content
returned via the graph's node words. ``load`` must instead route through
``pathsec.open`` so the read honours the allowed data roots.
"""

import pytest

from nltk import pathsec
from nltk.parse.dependencygraph import DependencyGraph

_RECORD = "1\tleaked-word\t_\tN\tN\t_\t0\troot\t_\t_\n\n"


class TestDependencyGraphLoadSandbox:
    def test_load_enforces_pathsec_sandbox(self, tmp_path, monkeypatch):
        """Under ``ENFORCE``, an out-of-root path is rejected; in-root still loads."""
        allowed = tmp_path / "data"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.setattr(pathsec, "ENFORCE", True)
        monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {allowed.resolve()})

        out_file = outside / "secret.conll"
        out_file.write_text(_RECORD, encoding="utf-8")
        with pytest.raises((PermissionError, ValueError)):
            DependencyGraph.load(str(out_file))

        in_file = allowed / "ok.conll"
        in_file.write_text(_RECORD, encoding="utf-8")
        graphs = DependencyGraph.load(str(in_file))
        words = [n["word"] for n in graphs[0].nodes.values() if n.get("word")]
        assert words == ["leaked-word"]

    def test_load_unchanged_when_sandbox_disabled(self, tmp_path, monkeypatch):
        """With the sandbox off, behaviour is unchanged (reads any path)."""
        monkeypatch.setattr(pathsec, "ENFORCE", False)
        any_file = tmp_path / "anywhere.conll"
        any_file.write_text(_RECORD, encoding="utf-8")
        graphs = DependencyGraph.load(str(any_file))
        words = [n["word"] for n in graphs[0].nodes.values() if n.get("word")]
        assert words == ["leaked-word"]
