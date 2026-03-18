from pydantic import BaseModel

class DependencyNode(BaseModel):
    service_id: str
    name: str
    team: str
    health_status: str
    criticality: str = "normal"
    depth: int = 0

class DependencyEdgeSchema(BaseModel):
    source: str
    target: str
    protocol: str
    critical: bool

class BlastRadiusResponse(BaseModel):
    service_id: str
    total_affected: int
    severity: str
    nodes: list[DependencyNode]
    edges: list[DependencyEdgeSchema]
    cached: bool = False

class DependencyCreate(BaseModel):
    source_service_id: str
    target_service_id: str
    protocol: str = "http"
    weight: float = 1.0
    critical: bool = False
