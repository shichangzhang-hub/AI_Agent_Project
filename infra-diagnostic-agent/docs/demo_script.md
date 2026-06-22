# Demo Script

This script is designed for a 4-6 minute live demo of `Infra-Diagnostic-Agent`.

## Goal

Show three things clearly:

1. The project can load an internal Markdown knowledge base.
2. The project can retrieve relevant troubleshooting documents for a noisy issue.
3. The Agent can orchestrate retrieval plus safe command execution and produce a diagnosis.

## Setup

Run these commands first:

```bash
cd infra-diagnostic-agent
.venv\Scripts\activate
pip install -e .
infra-diagnostic-agent bootstrap-kb
```

Expected outcome:

- The CLI reports that the knowledge base is ready.
- It prints the number of loaded documents and generated chunks.

## Demo Flow

### Step 1: Explain the project in one sentence

Suggested narration:

`This project is a lightweight AI diagnostic assistant for infrastructure incidents. It can read local troubleshooting docs, run safe diagnostic commands, and iteratively reason toward a fix instead of only chatting.`

### Step 2: Show direct document retrieval

Command:

```bash
infra-diagnostic-agent search-docs --query "ERR_OS_DEP missing package"
```

Suggested narration:

`This is the retrieval layer. I am not using a heavyweight vector database here. Instead, I built a local RAG pipeline with chunking, embeddings, and cosine similarity retrieval, so the assistant can surface the most relevant internal incident note quickly.`

What to point out:

- The top result should be `err_os_dep.md`.
- The retrieved chunk already contains a likely root cause and a safe remediation pattern.

### Step 3: Show the full Agent loop

Command:

```bash
infra-diagnostic-agent run-agent --issue "Deployment failed with ERR_OS_DEP after the new image rollout. The container exits before health checks pass."
```

Suggested narration:

`This is the Agent layer. The model runs inside a bounded ReAct loop. It can choose between internal doc retrieval and a controlled system command executor. The loop is capped at five steps, invalid JSON is rejected, and repeated tool calls are blocked so it does not spin forever.`

What to point out:

- The Agent first consults documentation.
- It may run a safe read-only command.
- It eventually returns a diagnosis rather than raw tool output.

### Step 4: Highlight the safety boundary

Command:

```bash
infra-diagnostic-agent run-command --command "Remove-Item test.txt"
```

Suggested narration:

`The assistant is intentionally not allowed to run arbitrary destructive commands. This tool layer is restricted to read-only diagnostics for demo safety and for a cleaner enterprise permission boundary.`

Expected outcome:

- The command should be blocked by policy.

## Closing Summary

Suggested narration:

`The interesting part of this project is not just calling an LLM. The real value is the orchestration: local knowledge retrieval, safe system inspection, and bounded reasoning. If I continue this project, the next step is adding dependency graph reasoning so the assistant can infer multi-hop root causes across services.`
