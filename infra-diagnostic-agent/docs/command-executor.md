# Command Executor

## Goal

This stage implements a controlled local command executor for future Agent tool calls.

## Current Policy

- Default shell: PowerShell
- Default timeout: 10 seconds
- Captures `stdout`, `stderr`, and exit code
- Blocks destructive or write-oriented commands
- Allows read-only diagnostic commands only

## Why This Shape

For an infrastructure diagnosis assistant, command execution is necessary but also the highest-risk capability. A controlled executor is safer than letting the model run arbitrary shell strings from day one.

## Next Step

Wire this executor into a higher-level tool layer that accepts structured requests from the Agent instead of raw user text.
