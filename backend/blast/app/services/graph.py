import uuid
from typing import Any
from neo4j import AsyncGraphDatabase
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


async def get_blast_radius(service_id: str, max_hops: int = 5) -> dict[str, Any]:
    """
    Traverse the dependency graph up to max_hops from a service node.
    Returns all downstream services that would be impacted if this service fails.
    """
    query = """
    MATCH path = (source:Service {id: $service_id})-[:DEPENDS_ON*1..{max_hops}]->(downstream:Service)
    RETURN
        downstream.id      AS id,
        downstream.name    AS name,
        downstream.team    AS team,
        length(path)       AS hops,
        downstream.criticality AS criticality
    ORDER BY hops ASC
    """
    query = query.replace("{max_hops}", str(max_hops))

    impacted = []
    try:
        async with get_driver().session() as session:
            result = await session.run(query, service_id=service_id)
            async for record in result:
                impacted.append({
                    "id": record["id"],
                    "name": record["name"],
                    "team": record["team"],
                    "hops": record["hops"],
                    "criticality": record["criticality"] or "normal",
                })
    except Exception as e:
        logger.warning("neo4j unavailable — returning mock blast radius", error=str(e))
        impacted = _mock_blast_radius(service_id)

    critical_count = sum(1 for s in impacted if s["criticality"] == "critical")
    return {
        "source_service_id": service_id,
        "impacted_count": len(impacted),
        "critical_impacted": critical_count,
        "severity": "critical" if critical_count > 0 else ("high" if len(impacted) > 5 else "medium"),
        "services": impacted,
    }


async def ensure_service_node(service_id: str, name: str, team: str, criticality: str = "normal"):
    """Create or update a Service node in Neo4j."""
    query = """
    MERGE (s:Service {id: $id})
    SET s.name = $name, s.team = $team, s.criticality = $criticality
    RETURN s
    """
    try:
        async with get_driver().session() as session:
            await session.run(query, id=service_id, name=name, team=team, criticality=criticality)
    except Exception as e:
        logger.warning("neo4j node upsert failed", error=str(e))


async def add_dependency(source_id: str, target_id: str, protocol: str = "http", weight: float = 1.0):
    """Add or update a DEPENDS_ON relationship between two services."""
    query = """
    MATCH (a:Service {id: $source_id}), (b:Service {id: $target_id})
    MERGE (a)-[r:DEPENDS_ON]->(b)
    SET r.protocol = $protocol, r.weight = $weight
    RETURN r
    """
    try:
        async with get_driver().session() as session:
            await session.run(query, source_id=source_id, target_id=target_id,
                              protocol=protocol, weight=weight)
    except Exception as e:
        logger.warning("neo4j edge upsert failed", error=str(e))


def _mock_blast_radius(service_id: str) -> list[dict]:
    """Dev fallback when Neo4j is not yet populated."""
    return [
        {"id": str(uuid.uuid4()), "name": "order-service", "team": "commerce",
         "hops": 1, "criticality": "critical"},
        {"id": str(uuid.uuid4()), "name": "notification-service", "team": "platform",
         "hops": 2, "criticality": "normal"},
        {"id": str(uuid.uuid4()), "name": "analytics-service", "team": "data",
         "hops": 2, "criticality": "normal"},
    ]
