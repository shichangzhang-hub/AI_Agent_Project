import unittest

from infra_diagnostic_agent.tools.command_executor import _run_command, execute_system_command


class CommandExecutorTests(unittest.TestCase):
    def test_execute_system_command_returns_success_text(self) -> None:
        result = execute_system_command('Write-Output "hello"')
        self.assertIn("执行成功", result)
        self.assertIn("hello", result)

    def test_dangerous_command_is_blocked(self) -> None:
        result = execute_system_command("Remove-Item demo.txt")
        self.assertIn("执行失败", result)
        self.assertIn("安全策略", result)

    def test_timeout_is_reported(self) -> None:
        result = _run_command("ping 127.0.0.1 -n 6", timeout_seconds=1)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "timeout")


if __name__ == "__main__":
    unittest.main()
