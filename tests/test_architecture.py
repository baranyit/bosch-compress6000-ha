"""Static guards: core modules stay Home Assistant free and the read path never writes."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "bosch_compress6000"
CORE_MODULES = [
    "errors.py",
    "const.py",
    "crypto.py",
    "models.py",
    "protocol.py",
    "transport.py",
    "client.py",
    "http_backend.py",
    "commands.py",
    "runtime.py",
    "write_transport.py",
    "write_backend.py",
]
# protocol.py only carries the write-group metadata; it has no I/O at all.
READ_PATH_MODULES = ["transport.py", "client.py", "http_backend.py"]
WRITE_MODULES = {"commands", "write_transport", "write_backend"}
ONLY_WRITE_MODULES_MAY_POST = {"write_transport.py", "write_backend.py"}


def _tree(name: str) -> ast.Module:
    return ast.parse((PACKAGE / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("module", CORE_MODULES)
def test_core_module_has_no_home_assistant_import(module: str) -> None:
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        assert not any(n == "homeassistant" or n.startswith("homeassistant.") for n in names)


@pytest.mark.parametrize("module", READ_PATH_MODULES)
def test_read_path_never_references_write_operations(module: str) -> None:
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Attribute):
            assert "write" not in node.attr.lower() and node.attr != "post", (
                f"{module}: {node.attr}"
            )
        if isinstance(node, ast.Name):
            assert "write" not in node.id.lower(), f"{module}: {node.id}"


@pytest.mark.parametrize("module", READ_PATH_MODULES)
def test_read_path_does_not_import_the_write_modules(module: str) -> None:
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.ImportFrom):
            imported = {(node.module or "").split(".")[0]} | {a.name for a in node.names}
            assert not imported & WRITE_MODULES, f"{module} imports {imported & WRITE_MODULES}"


def test_only_the_write_layer_can_post() -> None:
    """``.post`` lives in the write transport/backend, ``.post_value`` is used by commands only."""
    allowed = {"post": ONLY_WRITE_MODULES_MAY_POST, "post_value": {"commands.py"}}
    for path in sorted(PACKAGE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in allowed:
                assert path.name in allowed[node.attr], f"{path.name}: {node.attr}"
