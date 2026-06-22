import unittest
from contextlib import redirect_stdout
from io import StringIO

from infra_diagnostic_agent.cli import main


class SmokeTests(unittest.TestCase):
    def test_cli_entrypoint_runs(self) -> None:
        with redirect_stdout(StringIO()):
            self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
