"""Tests for lab_gui Qt binding import failure reporting."""
import importlib
import sys
import pytest


def test_missing_qt_bindings_raise_import_error(monkeypatch):
    """Importing lab_gui without a usable Qt binding raises ImportError naming both bindings.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.delitem(sys.modules, "PyICe.lab_gui", raising=False)
    monkeypatch.setitem(sys.modules, "PySide2", None)
    monkeypatch.setitem(sys.modules, "PySide6", None)
    with pytest.raises(ImportError) as excinfo:
        importlib.import_module("PyICe.lab_gui")
    message = str(excinfo.value)
    assert "PySide2:" in message
    assert "PySide6:" in message
    assert isinstance(excinfo.value.__cause__, ImportError)
