import asyncio

import pytest

from inspect_ai.agent._agent import AgentState, agent
from inspect_ai.model._chat_message import ChatMessageAssistant
from inspect_ai.tool._tool_call import ToolCall

from inspect_agents.config import load_and_build, load_yaml
from inspect_agents.run import run_agent


@agent
def toy_submit_model():
    async def execute(state: AgentState, tools):
        state.messages.append(
            ChatMessageAssistant(
                content="",
                tool_calls=[ToolCall(id="1", function="submit", arguments={"answer": "DONE"})],
            )
        )
        return state

    return execute


def test_minimal_yaml_builds_and_runs():
    yaml_txt = """
    supervisor:
      prompt: "You are helpful."
      attempts: 1
    approvals:
      submit:
        decision: approve
    """

    # Ensure approval stubs exist for mapping
    import sys
    import types
    if 'inspect_ai.approval' not in sys.modules:
        pkg = types.ModuleType('inspect_ai.approval')
        sys.modules['inspect_ai.approval'] = pkg
    if 'inspect_ai.approval._approval' not in sys.modules:
        mod = types.ModuleType('inspect_ai.approval._approval')
        class Approval:  # minimal stub
            def __init__(self, decision, modified=None, explanation=None):
                self.decision = decision
                self.modified = modified
                self.explanation = explanation
        sys.modules['inspect_ai.approval._approval'] = mod
        setattr(mod, 'Approval', Approval)
    if 'inspect_ai.approval._policy' not in sys.modules:
        pol = types.ModuleType('inspect_ai.approval._policy')
        class ApprovalPolicy:  # minimal stub container
            def __init__(self, approver, tools):
                self.approver = approver
                self.tools = tools
        setattr(pol, 'ApprovalPolicy', ApprovalPolicy)
        sys.modules['inspect_ai.approval._policy'] = pol

    agent_obj, tools, approvals = load_and_build(yaml_txt, model=toy_submit_model())
    result = asyncio.run(run_agent(agent_obj, "start", approval=approvals))
    assert "DONE" in (result.output.completion or "")


def test_subagent_declared_and_handoff_tool_present():
    yaml_txt = """
    supervisor:
      prompt: "You are helpful."
    subagents:
      - name: helper
        description: Replies hi
        prompt: "Say hi"
    """
    # ensure approval stubs so loader can import
    import sys
    import types
    if 'inspect_ai.approval' not in sys.modules:
        sys.modules['inspect_ai.approval']=types.ModuleType('inspect_ai.approval')
    if 'inspect_ai.approval._approval' not in sys.modules:
        mod = types.ModuleType('inspect_ai.approval._approval')
        class Approval:
            pass
        sys.modules['inspect_ai.approval._approval'] = mod
        setattr(mod, 'Approval', Approval)
    if 'inspect_ai.approval._policy' not in sys.modules:
        pol = types.ModuleType('inspect_ai.approval._policy')
        class ApprovalPolicy:  # minimal stub container
            def __init__(self, approver, tools):
                self.approver = approver
                self.tools = tools
        setattr(pol, 'ApprovalPolicy', ApprovalPolicy)
        sys.modules['inspect_ai.approval._policy'] = pol

    agent_obj, tools, approvals = load_and_build(yaml_txt, model=toy_submit_model())

    # Verify the tool list includes the handoff tool definition
    from inspect_ai.tool._tool_def import tool_defs
    defs = asyncio.run(tool_defs(tools))
    assert any(d.name == "transfer_to_helper" for d in defs)


def test_invalid_yaml_raises_clear_error():
    bad_yaml = """
    supervisor:
      attempts: 1  # missing prompt
    """
    with pytest.raises(ValueError) as e:
        load_yaml(bad_yaml)
    assert "prompt" in str(e.value)
