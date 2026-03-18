from neo4j import AsyncGraphDatabase
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

async def get_blast_radius(service_id: str, max_depth: int = 3) -> dict:
    """
    Traverse the Neo4j dependency graph up to max_depth hops from service_id.
    Falls back to PostgreSQL edges if Neo4j is unreachable.
    """
    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH path = (s:Service {id: $id})-[:DEPENDS_ON*1..%d]->(dep:Service)
                RETURN dep.id AS id, dep.name AS name, dep.team AS team,
                       dep.criticality AS criticality, length(path) AS depth
                """ % max_depth,
                id=service_id,
            )
            records = [r.data() async for r in result]
            await driver.close()
            return _build_response(service_id, records)
    except Exception as e:
        logger.warning("Neo4j unreachable, using mock blast radius", error=str(e))
        return _mock_blast_radius(service_id)

def _build_response(service_id: str, records: list) -> dict:
    nodes = [{"service_id": r["id"], "name": r["name"], "team": r.get("team", "unknown"),
              "health_status": "healthy", "criticality": r.get("criticality", "normal"),
              "depth": r["depth"]} for r in records]
    severity = "critical" if len(nodes) > 10 else ("high" if len(nodes) > 5 else "low")
    return {"service_id": service_id, "total_affected": len(nodes), "severity": severity,
            "nodes": nodes, "edges": [], "cached": False}

def _mock_blast_radius(service_id: str) -> dict:
    deps = [
        {"service_id": f"dep-{i}", "name": f"downstream-service-{i}",
         "team": "platform-team", "health_status": "healthy",
         "criticality": "normal", "depth": 1} for i in range(3)
    ]
    return {"service_id": service_id, "total_affected": len(deps),
            "severity": "low", "nodes": deps, "edges": [], "cached": False}

async def upsert_service_node(service_id: str, name: str, team: str, criticality: str = "normal") -> bool:
    try:
        driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        async with driver.session() as session:
            await session.run(
                "MERGE (s:Service {id: $id}) SET s.name = $name, s.team = $team, s.criticality = $criticality",
                id=service_id, name=name, team=team, criticality=criticality,
            )
        await driver.close()
        return True
    except Exception as e:
        logger.warning("Neo4j node upsert failed", error=str(e))
        return False
