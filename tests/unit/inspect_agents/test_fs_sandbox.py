import asyncio
import os
import sys
import types

import pytest

from inspect_agents.tools import read_file, write_file, edit_file


def _install_editor_stub(fs: dict[str, str]):
    # Provide a lightweight text_editor that operates on the passed dict
    mod_name = "inspect_ai.tool._tools._text_editor"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = types.ModuleType(mod_name)

    from inspect_ai.tool._tool import tool, Tool

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


def test_sandbox_mode_uses_editor_stub(monkeypatch):
    monkeypatch.setenv("INSPECT_AGENTS_FS_MODE", "sandbox")
    fs: dict[str, str] = {}
    _install_editor_stub(fs)

    r = read_file(); w = write_file(); e = edit_file()

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

    r = read_file(); w = write_file(); e = edit_file()

    async def roundtrip():
        await w(file_path="b.txt", content="alpha\nbeta\n")
        out1 = await r(file_path="b.txt", offset=1, limit=1)
        await e(file_path="b.txt", old_string="beta", new_string="BETA")
        out2 = await r(file_path="b.txt", offset=1, limit=1)
        return out1, out2

    out1, out2 = asyncio.run(roundtrip())
    assert out1.strip().endswith("beta")
    assert out2.strip().endswith("BETA")
