import builtins
import importlib.util
import uuid
from pathlib import Path

import pytest


def _load_bllip_module_without_bllipparser(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "bllipparser" or name.startswith("bllipparser."):
            raise ModuleNotFoundError("No module named 'bllipparser'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    module_path = Path(__file__).resolve().parents[2] / "parse" / "bllip.py"
    module_name = f"_nltk_bllip_importerror_probe_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bllip_import_error_helper_does_not_retain_import_exception(monkeypatch):
    module = _load_bllip_module_without_bllipparser(monkeypatch)
    message = "Couldn't import bllipparser module: No module named 'bllipparser'"

    assert module._ensure_bllip_import_or_error.__defaults__ is None

    with pytest.raises(ImportError, match=message):
        module._ensure_bllip_import_or_error()
