import hashlib
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from pgvector.psycopg2 import register_vector

from app.database.database import get_connection

KB_DIR = Path(__file__).parent
EMBEDDING_DIM = 384

embedding_model = TextEmbedding()


def chunk_text(text: str, max_chars: int = 1000):
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) <= max_chars:
            current += paragraph + "\n\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            current = paragraph + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks


def embed_text(text: str):
    embedding = list(embedding_model.embed([text]))[0]
    return np.array(embedding, dtype=np.float32)


def fallback_search(query: str, limit: int = 3):
    results = []
    query_words = query.lower().split()

    for file_path in KB_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        score = sum(1 for word in query_words if word in content.lower())

        if score > 0:
            results.append({
                "source": file_path.name,
                "content": content,
                "distance": 1.0 / score,
            })

    return sorted(results, key=lambda x: x["distance"])[:limit]


def init_vector_database():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()

        register_vector(conn)

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT UNIQUE NOT NULL,
            embedding VECTOR({EMBEDDING_DIM}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        cur.close()
        conn.close()

    except Exception as error:
        print(f"Vector database disabled, fallback search active: {error}")


def ingest_knowledge_base():
    try:
        conn = get_connection()
        register_vector(conn)
        cur = conn.cursor()

        for file_path in KB_DIR.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            chunks = chunk_text(content)

            for chunk in chunks:
                content_hash = hashlib.sha256(
                    f"{file_path.name}:{chunk}".encode("utf-8")
                ).hexdigest()

                vector = embed_text(chunk)

                cur.execute(
                    """
                    INSERT INTO knowledge_chunks (source, content, content_hash, embedding)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (content_hash) DO NOTHING
                    """,
                    (file_path.name, chunk, content_hash, vector),
                )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as error:
        print(f"Vector ingest skipped, fallback search active: {error}")


def search_similar_chunks(query: str, limit: int = 3):
    try:
        conn = get_connection()
        register_vector(conn)
        cur = conn.cursor()

        query_vector = embed_text(query)

        cur.execute(
            """
            SELECT source, content, embedding <=> %s AS distance
            FROM knowledge_chunks
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (query_vector, query_vector, limit),
        )

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return rows

    except Exception as error:
        print(f"Vector search failed, using fallback: {error}")
        return fallback_search(query, limit)
