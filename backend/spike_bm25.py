import os
from pathlib import Path
from rank_bm25 import BM25Okapi

def main():
    corpus_dir = Path(__file__).parent / "corpus"
    if not corpus_dir.exists():
        print(f"Directory not found: {corpus_dir}")
        return

    documents = []
    filenames = []
    
    for file_path in corpus_dir.glob("*.md"):
        with open(file_path, "r", encoding="utf-8") as f:
            documents.append(f.read())
            filenames.append(file_path.name)

    if not documents:
        print("No markdown files found in corpus.")
        return

    # Basic tokenization (lowercase, split by space)
    tokenized_corpus = [doc.lower().split() for doc in documents]

    bm25 = BM25Okapi(tokenized_corpus)

    query = "mental health parity denial appeal medical necessity"
    tokenized_query = query.lower().split()

    doc_scores = bm25.get_scores(tokenized_query)
    
    # Pair scores with filenames and sort descending
    results = sorted(zip(filenames, doc_scores), key=lambda x: x[1], reverse=True)
    
    hits = [r for r in results if r[1] > 0]
    
    print(f"Query: '{query}'")
    print(f"Total documents scanned: {len(documents)}")
    print(f"Number of hits (>0 score): {len(hits)}")
    for name, score in results:
        print(f"  - {name}: {score:.4f}")

    # DoD check: BM25 returns >=3 hits on a sample query.
    # Note: Our seed has 4 docs. Depending on tokens, we might hit 3+.
    if len(hits) >= 3:
        print("\nSUCCESS: DoD met (>=3 hits returned for query).")
    else:
        print("\nWARNING: DoD not met (fewer than 3 hits). Try a broader query or adding more docs.")

if __name__ == "__main__":
    main()
