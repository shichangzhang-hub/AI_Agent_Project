import unittest

from infra_diagnostic_agent.core.embeddings import local_hash_embedding


class EmbeddingTests(unittest.TestCase):
    def test_local_hash_embedding_is_deterministic(self) -> None:
        first = local_hash_embedding("payment service error")
        second = local_hash_embedding("payment service error")
        self.assertEqual(first, second)

    def test_local_hash_embedding_respects_dimensions(self) -> None:
        vector = local_hash_embedding("network timeout", dimensions=32)
        self.assertEqual(len(vector), 32)
        self.assertGreater(sum(abs(value) for value in vector), 0.0)


if __name__ == "__main__":
    unittest.main()
