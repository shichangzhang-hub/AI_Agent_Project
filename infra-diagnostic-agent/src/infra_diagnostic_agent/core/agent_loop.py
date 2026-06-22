"""ReAct-style agent loop for orchestrating diagnostic tools."""

from __future__ import annotations

import json
from typing import Callable

from openai import APIConnectionError, APIStatusError, OpenAI

from infra_diagnostic_agent.config import agent_settings
from infra_diagnostic_agent.tools import execute_system_command, search_docs


ToolFunction = Callable[[str], str]

MAX_AGENT_STEPS = 5
AVAILABLE_TOOLS = ("search_docs", "execute_system_command")
TOOL_REGISTRY: dict[str, ToolFunction] = {
    "search_docs": search_docs,
    "execute_system_command": execute_system_command,
}

SYSTEM_PROMPT_TEMPLATE = """
You are Infra-Diagnostic-Agent, a strict ReAct diagnostic controller.

You have exactly two tools:
1. search_docs
2. execute_system_command

You must reply with valid JSON only.
Do not wrap JSON in markdown fences.
Do not add commentary before or after the JSON.
Do not output any keys other than the allowed schema.

Allowed response schemas:
Action mode:
{{"action": "search_docs", "action_input": "query text"}}
{{"action": "execute_system_command", "action_input": "command text"}}

Completion mode:
{{"final_answer": "final diagnosis and next step"}}

Rules:
- Return exactly one JSON object.
- Use only one tool per turn.
- Do not repeat the exact same tool call after you already received its observation.
- If the issue is solved or you have enough evidence, return final_answer.
- If a previous tool observation shows an error, reason from it and either try another tool or stop.
- The available tools are: {tool_names}
- You are currently on step {step_number} of {max_steps}.
""".strip()


def call_llm(prompt: str) -> str:
    """Call the configured OpenAI-compatible model with a strict JSON prompt."""
    if not agent_settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client_kwargs: dict[str, str] = {"api_key": agent_settings.openai_api_key}
    if agent_settings.openai_base_url:
        client_kwargs["base_url"] = agent_settings.openai_base_url

    client = OpenAI(**client_kwargs)

    request_kwargs = {
        "model": agent_settings.openai_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    try:
        response = client.chat.completions.create(
            **request_kwargs,
            response_format={"type": "json_object"},
        )
    except APIStatusError as exc:
        # Some OpenAI-compatible providers do not support response_format.
        if getattr(exc, "status_code", None) == 400:
            try:
                response = client.chat.completions.create(**request_kwargs)
            except (APIConnectionError, APIStatusError) as inner_exc:
                raise RuntimeError(f"LLM request failed: {inner_exc}") from inner_exc
        else:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
    except APIConnectionError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned an empty response.")
    return content


def _build_prompt(user_issue: str, history: list[str], step_number: int, max_steps: int) -> str:
    """Build the full prompt passed to the LLM."""
    history_text = "\n".join(_trim_history(history)) if history else "(no prior actions)"
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tool_names=", ".join(AVAILABLE_TOOLS),
        step_number=step_number,
        max_steps=max_steps,
    )
    return "\n\n".join(
        [
            system_prompt,
            f"User issue:\n{user_issue}",
            f"Interaction history:\n{history_text}",
        ]
    )


def _summarize_entries(entries: list[str], max_summary_characters: int = 600) -> str:
    """Summarize older history entries into a compact single line."""
    cleaned = [" ".join(entry.split()) for entry in entries if entry.strip()]
    if not cleaned:
        return "Earlier history summary: (empty)"

    preview = " | ".join(cleaned[-3:])
    if len(preview) > max_summary_characters:
        preview = preview[: max_summary_characters - 3].rstrip() + "..."
    return f"Earlier history summary ({len(entries)} entries): {preview}"


def _trim_history(history: list[str]) -> list[str]:
    """Bound history size so the prompt stays small and recent evidence is preserved."""
    if not history:
        return []

    max_entries = max(2, agent_settings.max_history_entries)
    max_characters = max(200, agent_settings.max_history_characters)
    truncated_history = list(history)

    if len(truncated_history) > max_entries:
        keep_recent = max_entries - 1
        older_entries = truncated_history[:-keep_recent]
        recent_entries = truncated_history[-keep_recent:]
        truncated_history = [_summarize_entries(older_entries), *recent_entries]

    while len("\n".join(truncated_history)) > max_characters and len(truncated_history) > 2:
        if truncated_history[0].startswith("Earlier history summary"):
            truncated_history.pop(1)
        else:
            truncated_history = [_summarize_entries(truncated_history[:-1]), truncated_history[-1]]

    if len("\n".join(truncated_history)) > max_characters:
        summary = truncated_history[0]
        if len(summary) > max_characters:
            truncated_history[0] = summary[: max_characters - 3].rstrip() + "..."

    return truncated_history


def _parse_llm_response(raw_response: str) -> dict[str, str]:
    """Validate the strict JSON contract returned by the LLM."""
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object.")

    payload_keys = set(payload.keys())
    if payload_keys == {"final_answer"}:
        final_answer = payload["final_answer"]
        if not isinstance(final_answer, str) or not final_answer.strip():
            raise ValueError("final_answer must be a non-empty string.")
        return {"final_answer": final_answer}

    if payload_keys == {"action", "action_input"}:
        action = payload["action"]
        action_input = payload["action_input"]
        if not isinstance(action, str) or not action.strip():
            raise ValueError("action must be a non-empty string.")
        if not isinstance(action_input, str):
            raise ValueError("action_input must be a string.")
        return {"action": action, "action_input": action_input}

    raise ValueError("LLM response does not match an allowed schema.")


def run_agent_loop(user_issue: str) -> str:
    """Run a bounded ReAct-style loop until final_answer or max steps is reached."""
    history: list[str] = []
    executed_actions: set[tuple[str, str]] = set()

    for step_index in range(1, MAX_AGENT_STEPS + 1):
        prompt = _build_prompt(
            user_issue=user_issue,
            history=history,
            step_number=step_index,
            max_steps=MAX_AGENT_STEPS,
        )
        try:
            llm_output = call_llm(prompt)
        except Exception as exc:
            failure_answer = f"Agent failed to call the LLM service: {exc}"
            print(failure_answer)
            return failure_answer
        history.append(f"LLM output: {llm_output}")

        try:
            parsed = _parse_llm_response(llm_output)
        except ValueError as exc:
            history.append(
                "Observation: Invalid LLM response. "
                f"{exc}. Return exactly one allowed JSON object."
            )
            continue

        if "final_answer" in parsed:
            final_answer = parsed["final_answer"]
            print(final_answer)
            return final_answer

        action_name = parsed["action"]
        action_input = parsed["action_input"]
        action_signature = (action_name, action_input.strip())
        tool = TOOL_REGISTRY.get(action_name)

        if tool is None:
            history.append(
                "Observation: Unknown tool requested. "
                f"Requested={action_name}. Allowed tools={', '.join(AVAILABLE_TOOLS)}."
            )
            continue

        if action_signature in executed_actions:
            history.append(
                "Observation: Repeated tool call blocked. "
                "You already executed this exact action and received evidence. "
                "Use the previous observation to produce final_answer or choose a different tool."
            )
            continue

        history.append(f"Action: {action_name}")
        history.append(f"Action input: {action_input}")

        try:
            observation = tool(action_input)
        except Exception as exc:  # pragma: no cover - defensive boundary
            observation = f"Tool execution raised an exception: {exc}"

        executed_actions.add(action_signature)
        history.append(f"Observation: {observation}")

    fallback_answer = (
        "Agent stopped after 5 steps without a final diagnosis. "
        "Review the latest observations and continue manually."
    )
    print(fallback_answer)
    return fallback_answer
