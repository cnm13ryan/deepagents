import asyncio

import pytest
from inspect_ai.util._store import Store, init_subtask_store

from inspect_agents.tools import ToolException, edit_file, ls, read_file, write_file


def _fresh_store() -> Store:
    s = Store()
    init_subtask_store(s)
    return s


def test_ls_and_write_persistence():
    _fresh_store()
    ls_tool = ls()
    write_tool = write_file()

    async def _run():
        await write_tool(file_path="a.txt", content="hello")
        return await ls_tool()

    listing = asyncio.run(_run())
    assert "a.txt" in listing


def test_read_file_behaviors():
    _fresh_store()
    read_tool = read_file()
    write_tool = write_file()

    # not found
    async def _not_found():
        return await read_tool(file_path="missing.txt")

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_not_found())
    assert "missing.txt" in str(exc_info.value.message)
    assert "not found" in str(exc_info.value.message)

    # empty file
    async def _write_empty():
        await write_tool(file_path="empty.txt", content="")
        return await read_tool(file_path="empty.txt")

    assert (
        asyncio.run(_write_empty())
        == "System reminder: File exists but has empty contents"
    )

    # offsets and limits
    content = "line1\nline2\nline3\n"

    async def _write_content():
        await write_tool(file_path="note.txt", content=content)
        return await read_tool(file_path="note.txt", offset=1, limit=1)

    out = asyncio.run(_write_content())
    lines = out.splitlines()
    assert lines == [f"{2:6d}\t{'line2'}"]

    # offset beyond length
    async def _bad_offset():
        return await read_tool(file_path="note.txt", offset=1000)

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_bad_offset())
    assert "offset 1000 exceeds file length" in str(exc_info.value.message)
    assert "3 lines" in str(exc_info.value.message)

    # truncation to 2000 chars per line
    long_line = "x" * 2500
    async def _write_long():
        await write_tool(file_path="long.txt", content=long_line)
        return await read_tool(file_path="long.txt")

    long_out = asyncio.run(_write_long())
    number_tab, truncated = long_out.split("\t", 1)
    assert len(truncated) == 2000


def test_edit_file_uniqueness_and_replace_all():
    _fresh_store()
    write_tool = write_file()
    read_tool = read_file()
    edit_tool = edit_file()

    async def _setup():
        await write_tool(file_path="e.txt", content="foo foo bar foo")

    asyncio.run(_setup())

    # replace first only
    async def _first_only():
        await edit_tool(
            file_path="e.txt", old_string="foo", new_string="FOO", replace_all=False
        )
        return await read_tool(file_path="e.txt")

    out1 = asyncio.run(_first_only())
    assert out1.endswith("FOO foo bar foo")

    # replace all remaining
    async def _all():
        await edit_tool(
            file_path="e.txt", old_string="foo", new_string="FOO", replace_all=True
        )
        return await read_tool(file_path="e.txt")

    out2 = asyncio.run(_all())
    assert out2.endswith("FOO FOO bar FOO")

    # not found errors
    async def _file_not_found_error():
        await edit_tool(
            file_path="does_not_exist.txt",
            old_string="x",
            new_string="y",
        )

    async def _string_not_found_error():
        await edit_tool(
            file_path="e.txt", old_string="zzz", new_string="y", replace_all=True
        )

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_file_not_found_error())
    assert "does_not_exist.txt" in str(exc_info.value.message)
    assert "not found" in str(exc_info.value.message)

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_string_not_found_error())
    assert "zzz" in str(exc_info.value.message)
    assert "not found" in str(exc_info.value.message)


def test_instance_isolation():
    _fresh_store()
    ls_tool = ls()
    write_tool = write_file()
    read_tool = read_file()

    async def _setup():
        await write_tool(file_path="a.txt", content="hello A", instance="agentA")
        return await ls_tool(instance="agentB")

    listing_b = asyncio.run(_setup())
    assert listing_b == []

    async def _access():
        return await read_tool(file_path="a.txt", instance="agentB")

    with pytest.raises(ToolException) as exc_info:
        asyncio.run(_access())
    assert "a.txt" in str(exc_info.value.message)
    assert "not found" in str(exc_info.value.message)
