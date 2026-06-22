"""Controlled local command execution for diagnostic workflows."""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
from typing import Final

from infra_diagnostic_agent.config import execution_settings


READ_ONLY_COMMAND_PATTERNS: Final[tuple[str, ...]] = (
    r"^Get-[A-Za-z0-9_-]+(?:\s|$)",
    r"^Select-String(?:\s|$)",
    r"^Test-Path(?:\s|$)",
    r"^Resolve-Path(?:\s|$)",
    r"^Write-Output(?:\s|$)",
    r"^git\s+(status|diff|log|branch)\b",
    r"^python\s+--version$",
    r"^pip\s+(show|list)\b",
    r"^node\s+--version$",
    r"^npm\s+list\b",
    r"^where(?:\.exe)?\s+.+",
    r"^ipconfig(?:\s|$)",
    r"^ping\s+.+",
    r"^nslookup\s+.+",
    r"^tracert\s+.+",
)

DANGEROUS_COMMAND_PATTERNS: Final[tuple[str, ...]] = (
    r"\bRemove-Item\b",
    r"\bSet-Content\b",
    r"\bAdd-Content\b",
    r"\bMove-Item\b",
    r"\bCopy-Item\b",
    r"\bRename-Item\b",
    r"\bNew-Item\b",
    r"\bStart-Process\b",
    r"\bStop-Process\b",
    r"\bRestart-Computer\b",
    r"\bStop-Computer\b",
    r"\bInvoke-Expression\b",
    r"\bdel\b",
    r"\brd\b",
    r"\brmdir\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\btaskkill\b",
    r"\bgit\s+reset\b",
    r"\bgit\s+clean\b",
    r"\bnpm\s+(install|uninstall|update)\b",
    r"\bpip\s+(install|uninstall)\b",
)


@dataclass(frozen=True)
class CommandExecutionResult:
    """Structured result returned by the internal executor."""

    success: bool
    status: str
    command: str
    stdout: str
    stderr: str
    returncode: int | None


def _normalize_command(command: str) -> str:
    """Collapse extra whitespace so policy checks are predictable."""
    return " ".join(command.strip().split())


def _is_command_allowed(command: str) -> tuple[bool, str | None]:
    """Validate that the command fits the current read-only policy."""
    normalized = _normalize_command(command)
    if not normalized:
        return False, "命令不能为空。"

    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return False, "命令已被安全策略拦截：检测到潜在破坏性写操作。"

    for pattern in READ_ONLY_COMMAND_PATTERNS:
        if re.match(pattern, normalized, flags=re.IGNORECASE):
            return True, None

    return (
        False,
        "命令未通过安全策略。当前阶段仅允许只读诊断类命令，避免 Agent 直接执行写操作。",
    )


def _format_result(result: CommandExecutionResult) -> str:
    """Format the structured result into an Agent-friendly string."""
    status_title = "执行成功" if result.success else "执行失败"
    stdout_text = result.stdout.strip() or "(无)"
    stderr_text = result.stderr.strip() or "(无)"
    returncode_text = str(result.returncode) if result.returncode is not None else "(无)"

    return "\n".join(
        [
            status_title,
            f"状态: {result.status}",
            f"命令: {result.command}",
            f"返回码: {returncode_text}",
            "标准输出:",
            stdout_text,
            "标准错误:",
            stderr_text,
        ]
    )


def _run_command(command: str, timeout_seconds: int) -> CommandExecutionResult:
    """Execute a validated PowerShell command with timeout and output capture.

    The public function returns a formatted string because that is convenient
    for an LLM tool call. Internally we keep a structured result so later
    stages can reuse the data without reparsing text.
    """
    is_allowed, rejection_reason = _is_command_allowed(command)
    if not is_allowed:
        return CommandExecutionResult(
            success=False,
            status="blocked",
            command=command,
            stdout="",
            stderr=rejection_reason or "命令被拦截。",
            returncode=None,
        )

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.stdout.strip() if exc.stdout else ""
        stderr_text = exc.stderr.strip() if exc.stderr else ""
        timeout_message = (
            f"命令执行超过 {timeout_seconds} 秒，已被强制终止。"
            if not stderr_text
            else f"{stderr_text}\n命令执行超过 {timeout_seconds} 秒，已被强制终止。"
        )
        return CommandExecutionResult(
            success=False,
            status="timeout",
            command=command,
            stdout=stdout_text,
            stderr=timeout_message,
            returncode=None,
        )
    except OSError as exc:
        return CommandExecutionResult(
            success=False,
            status="executor_error",
            command=command,
            stdout="",
            stderr=f"本地执行器启动失败: {exc}",
            returncode=None,
        )

    success = completed.returncode == 0
    return CommandExecutionResult(
        success=success,
        status="completed" if success else "non_zero_exit",
        command=command,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def execute_system_command(command: str) -> str:
    """Execute a local diagnostic command and return a formatted summary.

    Notes:
    - Uses ``subprocess.run`` to invoke PowerShell.
    - Enforces a default timeout to avoid hanging commands.
    - Captures both stdout and stderr for later Agent reasoning.
    - Applies a read-only command policy so this stage stays safe by default.
    """
    result = _run_command(command, timeout_seconds=execution_settings.default_timeout_seconds)
    return _format_result(result)
