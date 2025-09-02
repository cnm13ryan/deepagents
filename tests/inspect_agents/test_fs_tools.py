import asyncio

from inspect_ai.util._store import Store, init_subtask_store

from inspect_agents.tools import ls, read_file, write_file, edit_file
from inspect_agents.state import Files


def _fresh_store() -> Store:
    s = Store()
    init_subtask_store(s)
    return s


def test_ls_and_write_persistence():
    s = _fresh_store()
    ls_tool = ls()
    write_tool = write_file()

    async def _run():
        await write_tool(file_path="a.txt", content="hello")
        return await ls_tool()

    listing = asyncio.run(_run())
    assert "a.txt" in listing


def test_read_file_behaviors():
    s = _fresh_store()
    read_tool = read_file()
    write_tool = write_file()

    # not found
    async def _not_found():
        return await read_tool(file_path="missing.txt")

    assert asyncio.run(_not_found()) == "Error: File 'missing.txt' not found"

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
    assert lines == ["%6d\t%s" % (2, "line2")]

    # offset beyond length
    async def _bad_offset():
        return await read_tool(file_path="note.txt", offset=1000)

    assert (
        asyncio.run(_bad_offset())
        == "Error: Line offset 1000 exceeds file length (3 lines)"
    )

    # truncation to 2000 chars per line
    long_line = "x" * 2500
    async def _write_long():
        await write_tool(file_path="long.txt", content=long_line)
        return await read_tool(file_path="long.txt")

    long_out = asyncio.run(_write_long())
    number_tab, truncated = long_out.split("\t", 1)
    assert len(truncated) == 2000


def test_edit_file_uniqueness_and_replace_all():
    s = _fresh_store()
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
    async def _errors():
        nf = await edit_tool(
            file_path="does_not_exist.txt",
            old_string="x",
            new_string="y",
        )
        miss = await edit_tool(
            file_path="e.txt", old_string="zzz", new_string="y", replace_all=True
        )
        return nf, miss

    nf_msg, miss_msg = asyncio.run(_errors())
    assert nf_msg == "Error: File 'does_not_exist.txt' not found"
    assert miss_msg == "Error: String not found in file: 'zzz'"


def test_instance_isolation():
    s = _fresh_store()
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

    not_found = asyncio.run(_access())
    assert not_found == "Error: File 'a.txt' not found"

