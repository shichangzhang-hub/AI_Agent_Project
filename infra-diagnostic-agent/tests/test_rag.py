import unittest

from infra_diagnostic_agent.core.rag import (
    RagIndex,
    build_index,
    chunk_documents,
    search,
)


def fake_embedding(text: str) -> list[float]:
    lowered = text.lower()
    return [
        1.0 if "error" in lowered else 0.0,
        1.0 if "payment" in lowered else 0.0,
        1.0 if "network" in lowered else 0.0,
        float(len(text.split())),
    ]


def zero_embedding(_: str) -> list[float]:
    return [0.0, 0.0, 0.0, 0.0]


class RagTests(unittest.TestCase):
    def test_chunk_documents_returns_overlapping_chunks(self) -> None:
        documents = ["abcdefghij"]
        chunks = chunk_documents(documents, chunk_size=4, overlap=1)

        self.assertEqual([chunk.text for chunk in chunks], ["abcd", "defg", "ghij"])
        self.assertEqual(chunks[0].source_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)

    def test_chunk_documents_skips_empty_documents(self) -> None:
        chunks = chunk_documents(["", "   ", "real text"], chunk_size=10, overlap=2)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "real text")

    def test_build_index_handles_empty_chunks(self) -> None:
        index = build_index([], embedding_fn=fake_embedding)
        self.assertEqual(index.dimension, 0)
        self.assertEqual(index.embeddings.shape, (0, 0))

    def test_search_returns_top_ranked_results(self) -> None:
        chunks = chunk_documents(
            [
                "Payment service error: token expired while charging customer.",
                "Network timeout between gateway and auth service.",
                "Markdown guide for local development environment.",
            ],
            chunk_size=120,
            overlap=20,
        )
        index = build_index(chunks, embedding_fn=fake_embedding)

        results = search("payment error", index, embedding_fn=fake_embedding, top_k=2)

        self.assertEqual(len(results), 2)
        self.assertIn("Payment service error", results[0].text)
        self.assertGreaterEqual(results[0].score, results[1].score)

    def test_search_returns_empty_for_blank_query(self) -> None:
        chunks = chunk_documents(["network issue"], chunk_size=20, overlap=5)
        index = build_index(chunks, embedding_fn=fake_embedding)
        self.assertEqual(search("   ", index, embedding_fn=fake_embedding), [])

    def test_search_returns_empty_for_zero_query_vector(self) -> None:
        chunks = chunk_documents(["payment error"], chunk_size=20, overlap=5)
        index = build_index(chunks, embedding_fn=fake_embedding)
        self.assertEqual(search("anything", index, embedding_fn=zero_embedding), [])

    def test_build_index_rejects_dimension_mismatch(self) -> None:
        chunks = chunk_documents(["alpha", "beta"], chunk_size=10, overlap=1)

        def inconsistent_embedding(text: str) -> list[float]:
            return [1.0, 2.0] if text == "alpha" else [1.0, 2.0, 3.0]

        with self.assertRaises(ValueError):
            build_index(chunks, embedding_fn=inconsistent_embedding)

    def test_search_raises_for_query_dimension_mismatch(self) -> None:
        chunks = chunk_documents(["payment error"], chunk_size=20, overlap=5)
        index = build_index(chunks, embedding_fn=fake_embedding)

        with self.assertRaises(ValueError):
            search("payment", index, embedding_fn=lambda _: [1.0, 2.0], top_k=1)

    def test_search_handles_zero_norm_documents(self) -> None:
        index = RagIndex(
            chunks=[],
            embeddings=[],
            norms=[],
            dimension=0,
        )
        self.assertEqual(search("query", index, embedding_fn=fake_embedding), [])


if __name__ == "__main__":
    unittest.main()
