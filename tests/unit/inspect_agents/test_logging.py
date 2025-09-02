import asyncio
from pathlib import Path

from inspect_agents.logging import DEFAULT_LOG_DIR, write_transcript
from inspect_agents.tools import write_file


def test_file_recorder_writes_events_and_redacts(tmp_path, monkeypatch):
    # Use a temp log dir under .inspect/logs to match default structure
    log_dir = Path(DEFAULT_LOG_DIR) / "test"
    monkeypatch.setenv("INSPECT_LOG_DIR", str(log_dir))

    # Produce a ToolEvent by calling write_file tool
    wf = write_file()
    asyncio.run(wf(file_path="/tmp/secret.txt", content="super secret"))

    # Also inject an event with arguments to verify redaction
    from inspect_ai.log._transcript import ToolEvent, transcript

    ev = ToolEvent(id="x", function="write_file")
    ev.arguments = {"file_path": "/tmp/secret.txt", "file_text": "classified", "api_key": "K"}
    transcript()._event(ev)

    # Write transcript to file
    out = write_transcript()
    assert Path(out).exists()

    # Read back and assert ToolEvent present and redacted
    lines = Path(out).read_text(encoding="utf-8").splitlines()
    assert any('"type": "ToolEvent"' in ln for ln in lines)
    redacted_line = next((ln for ln in lines if '"api_key"' in ln or '"file_text"' in ln), None)
    assert redacted_line is not None
    assert "[REDACTED]" in redacted_line

