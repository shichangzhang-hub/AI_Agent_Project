# Architecture Notes

This folder stores design decisions, workflow diagrams, and module responsibilities.

Suggested future sections:

- log ingestion pipeline
- RAG retrieval flow
- dependency graph model
- command execution safety rules

## Implemented Building Blocks

- `tools/command_executor.py`: controlled PowerShell executor with timeout and safety policy
- `core/rag.py`: lightweight local RAG module with chunking, in-memory indexing, and cosine-similarity retrieval
- `tools/docs_search.py`: tool-facing wrapper around the local RAG index
  - lazy-loads Markdown docs from `data/knowledge_base/`
  - builds an in-memory index on startup or first search
- `core/agent_loop.py`: strict JSON ReAct loop for tool orchestration
  - uses an OpenAI-compatible chat completion call
  - trims historical observations before each prompt
- `core/embeddings.py`: local hash embedding fallback plus OpenAI-compatible embeddings backend
- `core/knowledge_base.py`: Markdown document loader for the local knowledge base
