"""CLI entrypoint for Infra-Diagnostic-Agent."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from infra_diagnostic_agent.core import run_agent_loop
from infra_diagnostic_agent.tools import bootstrap_doc_search, search_docs
from infra_diagnostic_agent.tools.command_executor import execute_system_command


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="infra-diagnostic-agent",
        description="CLI scaffold for the Infra-Diagnostic-Agent project.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    run_command_parser = subparsers.add_parser(
        "run-command",
        help="Run a controlled local diagnostic command.",
    )
    run_command_parser.add_argument(
        "--command",
        required=True,
        help="PowerShell command to execute.",
    )

    run_agent_parser = subparsers.add_parser(
        "run-agent",
        help="Run the bounded ReAct agent loop for a diagnostic issue.",
    )
    run_agent_parser.add_argument(
        "--issue",
        required=True,
        help="User issue or error description for the Agent.",
    )

    search_docs_parser = subparsers.add_parser(
        "search-docs",
        help="Search the local Markdown knowledge base.",
    )
    search_docs_parser.add_argument(
        "--query",
        required=True,
        help="Diagnostic query or error text to search for.",
    )

    subparsers.add_parser(
        "bootstrap-kb",
        help="Load Markdown knowledge-base files and build the in-memory RAG index.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "run-command":
        print(execute_system_command(args.command))
        return 0

    if args.subcommand == "run-agent":
        print(bootstrap_doc_search())
        run_agent_loop(args.issue)
        return 0

    if args.subcommand == "search-docs":
        print(bootstrap_doc_search())
        print(search_docs(args.query))
        return 0

    if args.subcommand == "bootstrap-kb":
        print(bootstrap_doc_search())
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
