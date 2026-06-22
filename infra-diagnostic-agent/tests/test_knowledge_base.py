from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from infra_diagnostic_agent.config import knowledge_base_settings
from infra_diagnostic_agent.core.knowledge_base import load_markdown_documents
from infra_diagnostic_agent.tools.docs_search import bootstrap_doc_search, clear_doc_search, search_docs


class KnowledgeBaseTests(unittest.TestCase):
    def test_load_markdown_documents_reads_sorted_markdown_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "b.md").write_text("# B\n\nsecond", encoding="utf-8")
            (base_dir / "a.md").write_text("# A\n\nfirst", encoding="utf-8")

            documents = load_markdown_documents(base_dir)

        self.assertEqual([document.source_name for document in documents], ["a.md", "b.md"])

    def test_bootstrap_doc_search_builds_demo_index(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "incident.md").write_text(
                "# Incident\n\nPayment service error caused by auth dependency.",
                encoding="utf-8",
            )

            with patch(
                "infra_diagnostic_agent.tools.docs_search.knowledge_base_settings",
                replace(knowledge_base_settings, knowledge_base_dir=base_dir, chunk_size=200, chunk_overlap=20),
            ):
                clear_doc_search()
                message = bootstrap_doc_search(base_dir)
                result = search_docs("payment error")

        self.assertIn("Knowledge base ready", message)
        self.assertIn("incident.md", result)


if __name__ == "__main__":
    unittest.main()
