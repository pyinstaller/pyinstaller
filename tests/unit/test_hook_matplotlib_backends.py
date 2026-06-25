import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_hook_module():
    hook_path = (
        Path(__file__).parents[2]
        / "PyInstaller"
        / "hooks"
        / "hook-matplotlib.backends.py"
    )
    spec = importlib.util.spec_from_file_location("hook_matplotlib_backends", hook_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_list_available_mpl_backends_uses_backend_registry(monkeypatch):
    hook = _load_hook_module()
    backends = ModuleType("matplotlib.backends")
    backends.backend_registry = SimpleNamespace(list_all=lambda: ["Agg", "TkAgg"])

    monkeypatch.setitem(sys.modules, "matplotlib", ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.backends", backends)

    assert hook._list_available_mpl_backends.__wrapped__() == ["Agg", "TkAgg"]


def test_list_available_mpl_backends_falls_back_to_rcsetup(monkeypatch):
    hook = _load_hook_module()
    matplotlib = ModuleType("matplotlib")
    matplotlib.rcsetup = SimpleNamespace(all_backends=["Agg", "QtAgg"])

    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib)
    monkeypatch.delitem(sys.modules, "matplotlib.backends", raising=False)

    assert hook._list_available_mpl_backends.__wrapped__() == ["Agg", "QtAgg"]
