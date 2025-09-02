"""Test bootstrap for Inspect-AI dependent tests.

Adds the external submodule's `src` to `sys.path` so `inspect_ai` can be
imported without editing the submodule or requiring installation.
Also ensures the repo `src/` is importable when running tests via uv.
"""

import os
import sys
from pathlib import Path
import types


REPO_ROOT = Path(__file__).resolve().parents[2]

# Ensure local src/ is importable
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure external/inspect_ai/src is importable
INSPECT_AI_SRC = REPO_ROOT / "external" / "inspect_ai" / "src"
INSPECT_AI_PKG = INSPECT_AI_SRC / "inspect_ai"
if INSPECT_AI_SRC.exists():
    # Create a lightweight stub package to avoid heavy __init__ imports
    # Stub the minimal inspect_ai package tree to avoid heavy __init__ side effects
    if "inspect_ai" not in sys.modules:
        pkg = types.ModuleType("inspect_ai")
        pkg.__path__ = [str(INSPECT_AI_PKG)]  # type: ignore[attr-defined]
        sys.modules["inspect_ai"] = pkg
    if "inspect_ai.util" not in sys.modules:
        util_pkg = types.ModuleType("inspect_ai.util")
        util_pkg.__path__ = [str(INSPECT_AI_PKG / "util")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.util"] = util_pkg
    # Provide OutputLimitExceededError at package root for imports
    try:
        import importlib

        _util_any = importlib.import_module("inspect_ai.util._anyio")  # ensure path works
        class OutputLimitExceededError(Exception):
            def __init__(self, limit_str: str, truncated_output: str | None = None):
                self.limit_str = limit_str
                self.truncated_output = truncated_output
        setattr(sys.modules["inspect_ai.util"], "OutputLimitExceededError", OutputLimitExceededError)
        _util_conc = importlib.import_module("inspect_ai.util._concurrency")
        setattr(sys.modules["inspect_ai.util"], "concurrency", getattr(_util_conc, "concurrency"))
    except Exception:
        pass
    if "inspect_ai._util" not in sys.modules:
        underscore_util_pkg = types.ModuleType("inspect_ai._util")
        underscore_util_pkg.__path__ = [str(INSPECT_AI_PKG / "_util")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai._util"] = underscore_util_pkg
    # Minimal logger stub to avoid pulling heavy trace deps
    if "inspect_ai._util.logger" not in sys.modules:
        logger_stub = types.ModuleType("inspect_ai._util.logger")
        logger_stub.warn_once = lambda _logger, _msg: None
        sys.modules["inspect_ai._util.logger"] = logger_stub
    if "inspect_ai.log" not in sys.modules:
        log_pkg = types.ModuleType("inspect_ai.log")
        log_pkg.__path__ = [str(INSPECT_AI_PKG / "log")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.log"] = log_pkg

    # Provide a minimal inspect_ai.log._transcript to support span() + store events
    if "inspect_ai.log._transcript" not in sys.modules:
        from inspect_ai.util._store import store, store_changes, store_jsonable
        import contextlib
        from typing import Any, Callable, Iterator, Sequence, Type, TypeVar

        ET = TypeVar("ET")

        class BaseEvent:
            pass

        class StoreEvent(BaseEvent):
            def __init__(self, changes: list[dict[str, Any]]):
                self.changes = changes

        class SpanBeginEvent(BaseEvent):
            def __init__(self, id: str, parent_id: str | None, type: str, name: str):
                self.id = id
                self.parent_id = parent_id
                self.type = type
                self.name = name

        class SpanEndEvent(BaseEvent):
            def __init__(self, id: str):
                self.id = id

        class Transcript:
            def __init__(self) -> None:
                self._events: list[BaseEvent] = []

            @property
            def events(self) -> Sequence[BaseEvent]:
                return self._events

            def _event(self, event: BaseEvent) -> None:  # noqa: D401
                self._events.append(event)

            def _event_updated(self, event: BaseEvent) -> None:  # pragma: no cover
                pass

            def find_last_event(self, event_cls: Type[ET]) -> ET | None:
                for ev in reversed(self._events):
                    if isinstance(ev, event_cls):
                        return ev  # type: ignore[return-value]
                return None

        _TRANSCRIPT = Transcript()
        class ToolEvent(BaseEvent):
            def __init__(self, id: str, function: str | None = None, **kwargs):
                self.id = id
                self.function = function or ""
                self.result = ""
                self.truncated = None
                self.error = None
                self.pending = True
                self.completed = None
                self.working_time = None
                self.agent = None
                self.failed = None
                self.message_id = None
                self._cancel_fn = None
                self._cancelled = False

            def _set_cancel_fn(self, cancel_fn):  # pragma: no cover
                self._cancel_fn = cancel_fn

            def _set_result(
                self, result, truncated, error, waiting_time, agent, failed, message_id
            ):  # pragma: no cover
                self.result = result
                self.truncated = truncated
                self.error = error
                self.pending = None
                self.completed = True
                self.working_time = 0.0
                self.agent = agent
                self.failed = failed
                self.message_id = message_id

            @property
            def cancelled(self) -> bool:  # pragma: no cover
                return self._cancelled is True

        def transcript() -> Transcript:  # noqa: D401
            return _TRANSCRIPT

        def init_transcript(t: Transcript) -> None:
            global _TRANSCRIPT  # type: ignore[global-variable-not-assigned]
            _TRANSCRIPT = t

        @contextlib.contextmanager
        def track_store_changes() -> Iterator[None]:
            before = store_jsonable(store())
            yield
            after = store_jsonable(store())
            changes = store_changes(before, after)
            if changes:
                _TRANSCRIPT._event(StoreEvent(changes=changes))

        transcript_mod = types.ModuleType("inspect_ai.log._transcript")
        transcript_mod.BaseEvent = BaseEvent
        transcript_mod.StoreEvent = StoreEvent
        transcript_mod.ToolEvent = ToolEvent
        transcript_mod.SpanBeginEvent = SpanBeginEvent
        transcript_mod.SpanEndEvent = SpanEndEvent
        transcript_mod.Transcript = Transcript
        transcript_mod.transcript = transcript
        transcript_mod.init_transcript = init_transcript
        transcript_mod.track_store_changes = track_store_changes
        sys.modules["inspect_ai.log._transcript"] = transcript_mod

    # Stub inspect_ai.tool package to avoid executing its heavy __init__
    if "inspect_ai.tool" not in sys.modules:
        tool_pkg = types.ModuleType("inspect_ai.tool")
        tool_pkg.__path__ = [str(INSPECT_AI_PKG / "tool")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.tool"] = tool_pkg
        # Populate expected attributes used by other modules
        try:
            import importlib

            _tc = importlib.import_module("inspect_ai.tool._tool_call")
            setattr(tool_pkg, "ToolCall", getattr(_tc, "ToolCall"))
            setattr(tool_pkg, "ToolCallError", getattr(_tc, "ToolCallError"))
            _tool = importlib.import_module("inspect_ai.tool._tool")
            setattr(tool_pkg, "Tool", getattr(_tool, "Tool"))
            setattr(tool_pkg, "ToolError", getattr(_tool, "ToolError"))
            _tinfo = importlib.import_module("inspect_ai.tool._tool_info")
            setattr(tool_pkg, "ToolInfo", getattr(_tinfo, "ToolInfo"))
            _tchoice = importlib.import_module("inspect_ai.tool._tool_choice")
            setattr(tool_pkg, "ToolChoice", getattr(_tchoice, "ToolChoice"))
            setattr(tool_pkg, "ToolFunction", getattr(_tchoice, "ToolFunction"))
        except Exception:
            pass
    # Stub inspect_ai.agent and inspect_ai.model to enable direct submodule imports
    if "inspect_ai.agent" not in sys.modules:
        agent_pkg = types.ModuleType("inspect_ai.agent")
        agent_pkg.__path__ = [str(INSPECT_AI_PKG / "agent")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.agent"] = agent_pkg
    if "inspect_ai.model" not in sys.modules:
        model_pkg = types.ModuleType("inspect_ai.model")
        model_pkg.__path__ = [str(INSPECT_AI_PKG / "model")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.model"] = model_pkg
    if "inspect_ai.scorer" not in sys.modules:
        scorer_pkg = types.ModuleType("inspect_ai.scorer")
        scorer_pkg.__path__ = [str(INSPECT_AI_PKG / "scorer")]  # type: ignore[attr-defined]
        sys.modules["inspect_ai.scorer"] = scorer_pkg
    if "inspect_ai.scorer._score" not in sys.modules:
        score_mod = types.ModuleType("inspect_ai.scorer._score")
        async def score(_state):  # pragma: no cover
            return []
        score_mod.score = score
        sys.modules["inspect_ai.scorer._score"] = score_mod
    # Provide a minimal stub for inspect_ai.model._model to satisfy react import
    if "inspect_ai.model._model" not in sys.modules:
        model_mod = types.ModuleType("inspect_ai.model._model")
        class _Model:  # type: ignore
            pass
        def _get_model(name=None):  # pragma: no cover
            raise RuntimeError("get_model stub should not be called in tests")
        model_mod.Model = _Model
        model_mod.get_model = _get_model
        sys.modules["inspect_ai.model._model"] = model_mod

# Provide a tiny stub for shortuuid to satisfy _transcript import
if "shortuuid" not in sys.modules:
    shortuuid_stub = types.ModuleType("shortuuid")
    _counter = {"i": 0}
    def _next_uuid():  # pragma: no cover
        _counter["i"] += 1
        return f"stub-{_counter['i']}"
    shortuuid_stub.uuid = _next_uuid
    sys.modules["shortuuid"] = shortuuid_stub

# Minimal jsonschema stub for Draft7Validator to avoid dependency
if "jsonschema" not in sys.modules:
    jsonschema_stub = types.ModuleType("jsonschema")

    class Draft7Validator:  # type: ignore
        def __init__(self, schema):
            self.schema = schema

        def iter_errors(self, data):  # pragma: no cover - simple stub
            return []

    jsonschema_stub.Draft7Validator = Draft7Validator
    sys.modules["jsonschema"] = jsonschema_stub

# Minimal jsonlines stub used by trace/logging
if "jsonlines" not in sys.modules:
    jsonlines_stub = types.ModuleType("jsonlines")

    class Writer:  # type: ignore
        def __init__(self, fp=None, **kwargs):
            self.fp = fp

        def write(self, obj):  # pragma: no cover
            pass

        def close(self):  # pragma: no cover
            pass

    jsonlines_stub.Writer = Writer
    sys.modules["jsonlines"] = jsonlines_stub

# Minimal semver stub used by version checks
if "semver" not in sys.modules:
    semver_stub = types.ModuleType("semver")

    class Version:  # type: ignore
        def __init__(self, v: str):
            self.v = v

        @classmethod
        def parse(cls, v: str):  # pragma: no cover
            return cls(v)

        def compare(self, _other: str) -> int:  # pragma: no cover
            return 0

    semver_stub.Version = Version
    sys.modules["semver"] = semver_stub

# Stub approval apply to auto-approve tools without importing UI deps
if "inspect_ai.approval" not in sys.modules:
    approval_pkg = types.ModuleType("inspect_ai.approval")
    sys.modules["inspect_ai.approval"] = approval_pkg
if "inspect_ai.approval._apply" not in sys.modules:
    apply_mod = types.ModuleType("inspect_ai.approval._apply")
    async def apply_tool_approval(message, call, viewer, conversation):  # pragma: no cover
        class _Approval:
            decision = "approve"
            modified = None
            explanation = None
        return True, _Approval()
    apply_mod.apply_tool_approval = apply_tool_approval
    sys.modules["inspect_ai.approval._apply"] = apply_mod
