"""Coach: a chat agent with a small tool loop, like Stock Advisor's Ask AI.

Each step the model replies with one JSON object — either `{"action": "tool", ...}`
(the backend runs the tool and shows the model the result) or `{"action": "answer", ...}`.
This works the same on every provider, including small local models.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.agents.llm_json import extract_json_object
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.core.app_exceptions import AgentResponseParseError, InterviewPrepError
from app.schemas.agent_output_schemas import GeneratedCoachStep

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 4
MAX_HISTORY_MESSAGES = 12


@dataclass
class ToolStep:
    tool: str
    arguments: dict
    result: str


@dataclass
class CoachOutcome:
    answer: str
    tools_used: list[str] = field(default_factory=list)


def parse_coach_step(raw: str) -> GeneratedCoachStep:
    """Anything that isn't a valid JSON step is treated as a plain-text answer."""
    try:
        payload = extract_json_object(raw)
        return GeneratedCoachStep.model_validate(payload)
    except (AgentResponseParseError, ValueError):
        return GeneratedCoachStep(action="answer", answer=raw.strip())


def run_coach_turn(
    provider: BaseLlmProvider,
    model_name: str | None,
    build_prompt: Callable[[list[ToolStep], bool], str],
    run_tool: Callable[[str, dict], str],
    status_text: Callable[[str], str],
) -> CoachOutcome:
    steps: list[ToolStep] = []
    schema = GeneratedCoachStep.model_json_schema()
    for attempt in range(MAX_TOOL_CALLS + 1):
        must_answer = attempt == MAX_TOOL_CALLS
        step = parse_coach_step(provider.generate_text(build_prompt(steps, must_answer), model_name, json_schema=schema))
        if step.action != "tool" or must_answer or not step.tool:
            answer = step.answer.strip() or "Sorry, I couldn't put an answer together. Could you rephrase that?"
            return CoachOutcome(answer=answer, tools_used=[status_text(s.tool) for s in steps])
        try:
            result = run_tool(step.tool, step.arguments)
        except InterviewPrepError as exc:
            logger.info("Coach tool %s failed: %s", step.tool, exc.message)
            result = f"ERROR: {exc.message}"
        steps.append(ToolStep(tool=step.tool, arguments=step.arguments, result=result))
    raise AssertionError("unreachable")  # the last attempt always answers
