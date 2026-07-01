from app.database.database import get_connection


def save_message(user_id: int, role: str, message: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO memory (user_id, role, message)
        VALUES (%s, %s, %s)
        """,
        (user_id, role, message),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_history(user_id: int, limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT role, message
        FROM memory
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (user_id, limit),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return list(reversed(rows))
