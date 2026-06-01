import os
import sys
import time
from pathlib import Path

os.environ.setdefault("KGQA_USE_EMBEDDINGS", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph_rag.lightweight_vector_index import LightweightVectorIndex


def main() -> None:
    started = time.perf_counter()
    index = LightweightVectorIndex()
    index.load()
    results = index.search("70岁老人有高血压，推荐什么保险？", top_k=3)
    elapsed = time.perf_counter() - started

    print("=== Embedding index check ===")
    print(f"records      : {len(index.records)}")
    print(f"model        : {index.embedding_model_name}")
    print(f"device       : {index.embedding_device}")
    print(f"cache        : {index.embedding_cache}")
    print(f"use_bge      : {index.use_embeddings and index._semantic_vectors is not None}")
    print(f"elapsed_sec  : {elapsed:.2f}")
    print("top_results  :")
    for item in results:
        print(f"- {item.get('label')} | {item.get('name')} | {item.get('type')} | score={item.get('score')}")


if __name__ == "__main__":
    main()
