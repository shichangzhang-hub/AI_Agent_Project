import unittest

from infra_diagnostic_agent.core.rag import build_index, chunk_documents
from infra_diagnostic_agent.tools.docs_search import (
    clear_doc_search,
    configure_doc_search,
    search_docs,
)


def fake_embedding(text: str) -> list[float]:
    lowered = text.lower()
    return [
        1.0 if "error" in lowered else 0.0,
        1.0 if "payment" in lowered else 0.0,
        1.0 if "network" in lowered else 0.0,
        float(len(text.split())),
    ]


class DocsSearchTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_doc_search()

    def test_search_docs_bootstraps_automatically(self) -> None:
        result = search_docs("payment error")
        self.assertIn("score=", result)
        self.assertIn("payment_auth_failure.md", result)

    def test_search_docs_returns_formatted_results(self) -> None:
        chunks = chunk_documents(
            ["Payment service error while issuing token."],
            chunk_size=80,
            overlap=10,
        )
        index = build_index(chunks, embedding_fn=fake_embedding)
        configure_doc_search(index, fake_embedding)

        result = search_docs("payment error")

        self.assertIn("score=", result)
        self.assertIn("Payment service error", result)


if __name__ == "__main__":
    unittest.main()
