"""
BiasLens — SQLite Database Layer
Handles all persistence for analyses and articles.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_bias.db")


def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            total_sources INTEGER NOT NULL DEFAULT 0,
            avg_bias REAL NOT NULL DEFAULT 0.0,
            bias_spread REAL NOT NULL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            article_text TEXT NOT NULL,
            sentiment_positive REAL NOT NULL DEFAULT 0.0,
            sentiment_negative REAL NOT NULL DEFAULT 0.0,
            sentiment_neutral REAL NOT NULL DEFAULT 0.0,
            sentiment_compound REAL NOT NULL DEFAULT 0.0,
            bias_score REAL NOT NULL DEFAULT 0.0,
            bias_label TEXT NOT NULL DEFAULT 'Neutral',
            positive_keywords TEXT NOT NULL DEFAULT '[]',
            negative_keywords TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def save_analysis(topic: str, articles_data: list) -> int:
    """
    Save a complete analysis (topic + all article results).
    Returns the analysis ID.
    """
    conn = get_connection()
    cursor = conn.cursor()

    total_sources = len(articles_data)
    avg_bias = sum(a["bias_score"] for a in articles_data) / total_sources if total_sources > 0 else 0
    bias_scores = [a["bias_score"] for a in articles_data]
    bias_spread = max(bias_scores) - min(bias_scores) if len(bias_scores) > 1 else 0

    cursor.execute(
        """INSERT INTO analyses (topic, created_at, total_sources, avg_bias, bias_spread)
           VALUES (?, ?, ?, ?, ?)""",
        (topic, datetime.now().isoformat(), total_sources, round(avg_bias, 4), round(bias_spread, 4))
    )
    analysis_id = cursor.lastrowid

    for article in articles_data:
        cursor.execute(
            """INSERT INTO articles 
               (analysis_id, source_name, article_text, 
                sentiment_positive, sentiment_negative, sentiment_neutral, sentiment_compound,
                bias_score, bias_label, positive_keywords, negative_keywords)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_id,
                article["source_name"],
                article["article_text"],
                article["sentiment_positive"],
                article["sentiment_negative"],
                article["sentiment_neutral"],
                article["sentiment_compound"],
                article["bias_score"],
                article["bias_label"],
                json.dumps(article.get("positive_keywords", [])),
                json.dumps(article.get("negative_keywords", []))
            )
        )

    conn.commit()
    conn.close()
    return analysis_id


def get_all_analyses() -> list:
    """Fetch all analyses (summary only, no full text)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, topic, created_at, total_sources, avg_bias, bias_spread
        FROM analyses ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result


def get_analysis_by_id(analysis_id: int) -> dict | None:
    """Fetch a full analysis including all articles."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    analysis_row = cursor.fetchone()
    if not analysis_row:
        conn.close()
        return None

    analysis = dict(analysis_row)

    cursor.execute("SELECT * FROM articles WHERE analysis_id = ?", (analysis_id,))
    articles = []
    for row in cursor.fetchall():
        article = dict(row)
        article["positive_keywords"] = json.loads(article["positive_keywords"])
        article["negative_keywords"] = json.loads(article["negative_keywords"])
        articles.append(article)

    analysis["articles"] = articles
    conn.close()
    return analysis


def delete_analysis(analysis_id: int) -> bool:
    """Delete an analysis and its articles."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_stats() -> dict:
    """Get aggregate statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM analyses")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT AVG(avg_bias) as avg FROM analyses")
    row = cursor.fetchone()
    avg = row["avg"] if row["avg"] is not None else 0

    cursor.execute("SELECT COUNT(*) as total FROM articles")
    total_articles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as cnt FROM articles WHERE bias_label = 'Neutral'")
    neutral_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM articles WHERE bias_label != 'Neutral'")
    biased_count = cursor.fetchone()["cnt"]

    conn.close()
    return {
        "total_analyses": total,
        "total_articles": total_articles,
        "average_bias": round(avg, 4),
        "neutral_count": neutral_count,
        "biased_count": biased_count
    }
