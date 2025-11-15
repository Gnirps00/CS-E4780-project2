# 実行コマンド:uv run python test_exemplar_store.py
#!/usr/bin/env python3
from exemplar_store import ExemplarStore
def test_exemplar_store():
    store = ExemplarStore()
    test_questions = [
        "How many scholars won prizes in Chemistry?",
        "Which Japanese scholars won prizes?",
        "Show me scholars affiliated with Harvard"
    ]
    for question in test_questions:
        similar = store.get_similar_exemplars(question, k=5)
        print(f"\nQuestion: {question}")
        for ex in similar:
            print(f"  - Similar ({ex['similarity']:.3f}): {ex['question']}")
if __name__ == "__main__":
    test_exemplar_store()