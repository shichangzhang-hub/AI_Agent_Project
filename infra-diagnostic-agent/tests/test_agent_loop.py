from dataclasses import replace
import unittest
from unittest.mock import patch

from infra_diagnostic_agent.config import agent_settings
from infra_diagnostic_agent.core.agent_loop import _trim_history, run_agent_loop


class AgentLoopTests(unittest.TestCase):
    def test_loop_recovers_from_invalid_json_and_finishes(self) -> None:
        llm_responses = iter(
            [
                "not-json",
                '{"action": "search_docs", "action_input": "ERR_OS_DEP"}',
                '{"final_answer": "Dependency issue confirmed from docs."}',
            ]
        )

        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=lambda _: next(llm_responses),
            ),
            patch.dict(
                "infra_diagnostic_agent.core.agent_loop.TOOL_REGISTRY",
                {"search_docs": lambda query: f"doc result for {query}"},
                clear=True,
            ),
            patch("builtins.print") as mock_print,
        ):
            result = run_agent_loop("Deployment failed with ERR_OS_DEP.")

        self.assertEqual(result, "Dependency issue confirmed from docs.")
        mock_print.assert_called_once_with("Dependency issue confirmed from docs.")

    def test_loop_invokes_command_tool_then_returns_final_answer(self) -> None:
        llm_responses = iter(
            [
                '{"action": "execute_system_command", "action_input": "Write-Output \\"ok\\""}',
                '{"final_answer": "Command output shows the host is healthy."}',
            ]
        )

        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=lambda _: next(llm_responses),
            ),
            patch.dict(
                "infra_diagnostic_agent.core.agent_loop.TOOL_REGISTRY",
                {"execute_system_command": lambda command: f"ran {command}"},
                clear=True,
            ),
            patch("builtins.print"),
        ):
            result = run_agent_loop("Need a quick host check.")

        self.assertEqual(result, "Command output shows the host is healthy.")

    def test_loop_stops_after_max_steps_without_final_answer(self) -> None:
        llm_responses = iter(
            ['{"action": "search_docs", "action_input": "retry"}'] * 5
        )

        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=lambda _: next(llm_responses),
            ),
            patch.dict(
                "infra_diagnostic_agent.core.agent_loop.TOOL_REGISTRY",
                {"search_docs": lambda query: f"doc result for {query}"},
                clear=True,
            ),
            patch("builtins.print") as mock_print,
        ):
            result = run_agent_loop("Loop forever issue.")

        self.assertIn("Agent stopped after 5 steps", result)
        mock_print.assert_called_once()

    def test_unknown_tool_does_not_crash_loop(self) -> None:
        llm_responses = iter(
            [
                '{"action": "unknown_tool", "action_input": "x"}',
                '{"final_answer": "Stopped after unsupported tool request."}',
            ]
        )

        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=lambda _: next(llm_responses),
            ),
            patch("builtins.print"),
        ):
            result = run_agent_loop("Unknown tool path.")

        self.assertEqual(result, "Stopped after unsupported tool request.")

    def test_repeated_tool_call_is_blocked_and_loop_can_finish(self) -> None:
        llm_responses = iter(
            [
                '{"action": "search_docs", "action_input": "ERR_OS_DEP"}',
                '{"action": "search_docs", "action_input": "ERR_OS_DEP"}',
                '{"final_answer": "Docs already showed the likely missing OS package dependency."}',
            ]
        )

        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=lambda _: next(llm_responses),
            ),
            patch.dict(
                "infra_diagnostic_agent.core.agent_loop.TOOL_REGISTRY",
                {"search_docs": lambda query: f"doc result for {query}"},
                clear=True,
            ),
            patch("builtins.print"),
        ):
            result = run_agent_loop("Repeated tool loop.")

        self.assertIn("likely missing OS package dependency", result)

    def test_loop_returns_clear_error_when_llm_call_fails(self) -> None:
        with (
            patch(
                "infra_diagnostic_agent.core.agent_loop.call_llm",
                side_effect=RuntimeError("OPENAI_API_KEY is not configured."),
            ),
            patch("builtins.print") as mock_print,
        ):
            result = run_agent_loop("LLM path failure.")

        self.assertIn("Agent failed to call the LLM service", result)
        mock_print.assert_called_once()

    def test_trim_history_summarizes_older_entries(self) -> None:
        synthetic_history = [f"entry {index}" for index in range(20)]

        with patch(
            "infra_diagnostic_agent.core.agent_loop.agent_settings",
            replace(agent_settings, max_history_entries=6, max_history_characters=200),
        ):
            trimmed = _trim_history(synthetic_history)

        self.assertLessEqual(len(trimmed), 6)
        self.assertTrue(trimmed[0].startswith("Earlier history summary"))


if __name__ == "__main__":
    unittest.main()
