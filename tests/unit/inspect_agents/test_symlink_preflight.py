import asyncio
import sys
import types

import pytest

from inspect_agents.tools import ToolException, edit_file, read_file, write_file


def _install_editor_stub():
    """Install a minimal in-process text_editor stub.

    We only need the module to exist so sandbox paths activate; the symlink
    check should fail before the editor is invoked in these tests.
    """
    mod_name = "inspect_ai.tool._tools._text_editor"
    sys.modules.pop(mod_name, None)

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    @tool()
    def text_editor() -> Tool:  # type: ignore[return-type]
        async def execute(**_: object) -> str:
            return "OK"

        return execute

    mod.text_editor = text_editor
    sys.modules[mod_name] = mod


def _install_bash_stub(symlink_paths: set[str]):
    """Install a bash_session stub that flags certain paths as symlinks.

    - `test -L <path>` → "SYMLINK" if path in `symlink_paths`, else "OK".
    - `wc -c <path>` → "0" (minimal valid output for size preflights).
    - Other commands → empty stdout.
    """
    mod_name = "inspect_ai.tool._tools._bash_session"
    sys.modules.pop(mod_name, None)

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    class MockResult:
        def __init__(self, stdout: str):
            self.stdout = stdout

    @tool()
    def bash_session() -> Tool:  # type: ignore[return-type]
        async def execute(action: str, command: str | None = None) -> MockResult:
            if action != "run" or not command:
                return MockResult("")

            cmd = command.strip()
            if cmd.startswith("test -L "):
                path = cmd[len("test -L ") :].split()[0]
                return MockResult("SYMLINK" if path in symlink_paths else "OK")
            if cmd.startswith("wc -c "):
                return MockResult("0")
            return MockResult("")

        return execute

    mod.bash_session = bash_session
    sys.modules[mod_name] = mod


@pytest.mark.parametrize("op", ["read", "write", "edit"])  # type: ignore[misc]
def test_sandbox_symlink_denied(monkeypatch, op: str):
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")

    # Install stubs for sandbox preflight
    _install_editor_stub()
    bad = "/repo/bad_link"
    _install_bash_stub({bad})

    r = read_file()
    w = write_file()
    e = edit_file()

    async def run_case():
        if op == "read":
            await r(file_path=bad, offset=0, limit=10)
        elif op == "write":
            await w(file_path=bad, content="data")
        else:
            await e(file_path=bad, old_string="x", new_string="y")

    with pytest.raises(Exception) as exc:
        asyncio.run(run_case())
    assert "symbolic link" in str(exc.value)
