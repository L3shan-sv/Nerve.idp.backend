from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger

logger = get_logger(__name__)

async def full_text_search(db: AsyncSession, query: str, service_id: str | None = None, limit: int = 20) -> list[dict]:
    """PostgreSQL full-text search over tech docs content."""
    try:
        base_q = """
            SELECT id, service_id, title, slug, doc_type, is_stale,
                   ts_rank(to_tsvector('english', content_md), plainto_tsquery('english', :query)) AS score,
                   LEFT(content_md, 300) AS excerpt
            FROM tech_docs
            WHERE to_tsvector('english', content_md) @@ plainto_tsquery('english', :query)
        """
        params: dict = {"query": query, "limit": limit}
        if service_id:
            base_q += " AND service_id = :service_id"
            params["service_id"] = service_id
        base_q += " ORDER BY score DESC LIMIT :limit"

        result = await db.execute(text(base_q), params)
        rows = result.fetchall()
        return [
            {"doc_id": str(r.id), "service_id": r.service_id, "title": r.title,
             "slug": r.slug, "doc_type": r.doc_type, "excerpt": r.excerpt or "",
             "score": float(r.score), "is_stale": r.is_stale}
            for r in rows
        ]
    except Exception as e:
        logger.warning("FTS search failed", error=str(e))
        return []

def compute_freshness(last_committed_at, content_md: str) -> tuple[int, bool]:
    """Return (days_since_commit, is_stale). Stale threshold = 90 days."""
    from datetime import datetime, UTC
    if not last_committed_at:
        return 999, True
    delta = (datetime.now(UTC) - last_committed_at).days
    return delta, delta > 90
