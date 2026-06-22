# Infra-Diagnostic-Agent

Command-line AI diagnostic assistant scaffold for infrastructure and deployment troubleshooting.

## Structure

- `src/infra_diagnostic_agent/`: Python source package
- `tests/`: test cases
- `docs/`: design and architecture notes
- `data/`: local sample data, logs, and knowledge assets

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Current Stage

- Project scaffold is ready.
- CLI entrypoint is available.
- Controlled command executor is available for read-only diagnostics.
- ReAct agent loop is wired to an OpenAI-compatible LLM interface.
- Prompt history is truncated automatically to keep the loop bounded.
- Markdown knowledge-base loading and local RAG bootstrap are available.
- Local fallback embeddings allow offline demos without external APIs.

## Example

```bash
python -m infra_diagnostic_agent.cli run-command --command "Get-Date"
```

```bash
python -m infra_diagnostic_agent.cli run-agent --issue "Deployment failed with ERR_OS_DEP"
```

```bash
infra-diagnostic-agent bootstrap-kb
infra-diagnostic-agent search-docs --query "payment service auth error"
```

## Demo Notes

- `EMBEDDING_BACKEND=local` works offline and is the easiest demo mode.
- `EMBEDDING_BACKEND=openai` uses the configured OpenAI-compatible embeddings API.
- `run-agent` still requires a working chat-model API key because the ReAct loop calls the LLM.
- After `pip install -e .`, you can use the `infra-diagnostic-agent` command directly.
- Demo walkthrough: [docs/demo_script.md](/d:/AI_Agent_Project/infra-diagnostic-agent/docs/demo_script.md)
- Sample enterprise-style issues: [docs/sample_issues.md](/d:/AI_Agent_Project/infra-diagnostic-agent/docs/sample_issues.md)
