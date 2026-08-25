"""Rebuild persisted problem-statement vectors with the configured embedding backend."""

import argparse
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from platform_core.ai.embeddings import EmbeddingProvider
from platform_core.database.connection import SessionLocal
from platform_core.database.models import ProblemStatement


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate 384-dimensional problem-statement embeddings.")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    db = SessionLocal()
    embedder = EmbeddingProvider()
    started = time.perf_counter()
    updated = 0
    try:
        rows = db.query(ProblemStatement).order_by(ProblemStatement.id).all()
        for offset in range(0, len(rows), args.batch_size):
            batch = rows[offset:offset + args.batch_size]
            texts = [ps.search_text or f"{ps.title} {ps.description}" for ps in batch]
            vectors = embedder.get_embeddings(texts)
            for problem_statement, vector in zip(batch, vectors):
                problem_statement.embedding = vector
            db.commit()
            updated += len(batch)
            print(f"Embedded {updated}/{len(rows)} problem statements", flush=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    print({"updated": updated, "backend": embedder.backend, "elapsed_ms": elapsed_ms}, flush=True)


if __name__ == "__main__":
    main()
