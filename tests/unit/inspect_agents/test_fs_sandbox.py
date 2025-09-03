import asyncio
import sys
import types

from inspect_agents.tools import edit_file, ls, read_file, write_file


def _install_editor_stub(fs: dict[str, str]):
    # Provide a lightweight text_editor that operates on the passed dict
    mod_name = "inspect_ai.tool._tools._text_editor"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    @tool()
    def text_editor() -> Tool:  # type: ignore[return-type]
        async def execute(
            command: str,
            path: str,
            file_text: str | None = None,
            insert_line: int | None = None,
            new_str: str | None = None,
            old_str: str | None = None,
            view_range: list[int] | None = None,
        ) -> str:
            if command == "create":
                fs[path] = file_text or ""
                return "OK"
            elif command == "view":
                content = fs.get(path, "")
                if view_range is None:
                    return content
                start, end = view_range
                lines = content.splitlines()
                s = max(1, start) - 1
                e = len(lines) if end == -1 else min(len(lines), end)
                return "\n".join(lines[s:e])
            elif command == "str_replace":
                content = fs.get(path, None)
                if content is None:
                    return "ERR"
                fs[path] = content.replace(old_str or "", new_str or "")
                return "OK"
            else:
                return "UNSUPPORTED"

        return execute

    mod.text_editor = text_editor
    sys.modules[mod_name] = mod


def _install_bash_stub(fs: dict[str, str]):
    # Provide a lightweight bash_session that lists files from the passed dict
    mod_name = "inspect_ai.tool._tools._bash_session"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import Tool, tool

    class MockResult:
        def __init__(self, stdout: str):
            self.stdout = stdout

    @tool()
    def bash_session() -> Tool:  # type: ignore[return-type]
        async def execute(action: str, command: str | None = None) -> MockResult:
            # Match the tool's usage: `ls -1 {escaped_root}` where escaped_root defaults to '/repo'
            if action == "run" and command and command.startswith("ls -1"):
                # Accept bare `ls -1` (legacy) and `ls -1 /repo` (current)
                # Handle both quoted and unquoted /repo
                if command == "ls -1" or command.endswith(" /repo") or "'/repo'" in command or '"/repo"' in command:
                    file_list = list(fs.keys())
                    return MockResult("\n".join(file_list))
                # Unknown root: return empty (best-effort behavior)
                return MockResult("")
            return MockResult("")

        return execute

    mod.bash_session = bash_session
    sys.modules[mod_name] = mod


def test_sandbox_mode_uses_editor_stub(monkeypatch):
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
    fs: dict[str, str] = {}
    _install_editor_stub(fs)
    _install_bash_stub(fs)

    r = read_file()
    w = write_file()
    e = edit_file()

    async def run_all():
        await w(file_path="/repo/a.txt", content="hello")
        pre = await r(file_path="/repo/a.txt", offset=0, limit=5)
        await e(file_path="/repo/a.txt", old_string="hello", new_string="hi")
        post = await r(file_path="/repo/a.txt", offset=0, limit=5)
        return pre, post

    pre, post = asyncio.run(run_all())
    assert pre.endswith("hello")
    assert post.endswith("hi")


def test_sandbox_mode_graceful_fallback_without_editor(monkeypatch):
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
    # Ensure no editor stub present so code falls back to store mode
    sys.modules.pop("inspect_ai.tool._tools._text_editor", None)

    r = read_file()
    w = write_file()
    e = edit_file()

    async def roundtrip():
        await w(file_path="b.txt", content="alpha\nbeta\n")
        out1 = await r(file_path="b.txt", offset=1, limit=1)
        await e(file_path="b.txt", old_string="beta", new_string="BETA")
        out2 = await r(file_path="b.txt", offset=1, limit=1)
        return out1, out2

    out1, out2 = asyncio.run(roundtrip())
    assert out1.strip().endswith("beta")
    assert out2.strip().endswith("BETA")


def test_sandbox_ls_command(monkeypatch):
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
    fs: dict[str, str] = {"file1.txt": "content1", "file2.py": "print('hello')", "README.md": "# Project"}
    _install_editor_stub(fs)
    _install_bash_stub(fs)

    ls_tool = ls()

    async def test_ls():
        result = await ls_tool()
        return result

    file_list = asyncio.run(test_ls())
    assert isinstance(file_list, list)
    assert set(file_list) == {"file1.txt", "file2.py", "README.md"}
