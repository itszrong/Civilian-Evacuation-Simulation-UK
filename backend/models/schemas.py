"""
Pydantic schemas for London Evacuation Planning Tool.

These schemas define the data structures used throughout the application,
following the system design document requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator


class SourceTier(str, Enum):
    """Source tier enumeration for data feeds."""
    GOV_PRIMARY = "gov_primary"
    NEWS_VERIFIED = "news_verified"


class DocumentType(str, Enum):
    """Document type enumeration."""
    POLICY = "policy"
    ALERT = "alert"
    NEWS = "news"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Agent type enumeration."""
    PLANNER = "planner"
    WORKER = "worker"
    JUDGE = "judge"
    EXPLAINER = "explainer"
    FEEDS = "feeds"
    SIMULATION = "simulation"
    EMERGENCY_PLANNER = "emergency_planner"


# ===== Data Feed Models =====

class DataSource(BaseModel):
    """Data source configuration."""
    name: str
    type: str  # "api", "rss"
    base: Optional[str] = None
    url: Optional[str] = None


class SourceTierConfig(BaseModel):
    """Source tier configuration."""
    name: str
    freshness_days: int
    sources: List[DataSource]


class SourcesConfig(BaseModel):
    """Complete sources configuration."""
    tiers: List[SourceTierConfig]
    policies: Dict[str, Any]


class CanonicalDocument(BaseModel):
    """Canonical document schema."""
    doc_id: str
    url: str
    source: str
    tier: SourceTier
    published_at: datetime
    fetched_at: datetime
    title: str
    text: str
    type: DocumentType
    jurisdiction: str
    entities: List[str] = Field(default_factory=list)
    hash: str


# ===== User Intent & Scenario Models =====

class ScenarioConstraints(BaseModel):
    """Scenario constraints."""
    max_scenarios: int = Field(default=12, le=20)
    compute_budget_minutes: int = Field(default=5, le=15)
    must_protect_pois: List[str] = Field(default_factory=list)


class UserPreferences(BaseModel):
    """User preferences for optimization."""
    fairness_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    clearance_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    robustness_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    
    @field_validator('robustness_weight')
    @classmethod
    def weights_sum_to_one(cls, v, info):
        """Ensure weights sum to 1.0."""
        if info.data:
            total = v + info.data.get('fairness_weight', 0) + info.data.get('clearance_weight', 0)
            if abs(total - 1.0) > 0.01:
                raise ValueError('Weights must sum to 1.0')
        return v


class UserIntent(BaseModel):
    """User intent for evacuation planning."""
    objective: str
    city: str = Field(default="london")
    constraints: ScenarioConstraints
    hypotheses: List[str] = Field(default_factory=list)
    preferences: UserPreferences
    freshness_days: int = Field(default=7, ge=1, le=30)
    tiers: List[SourceTier] = Field(default_factory=lambda: [SourceTier.GOV_PRIMARY])


# ===== Scenario Models =====

class PolygonCordon(BaseModel):
    """Polygon cordon closure."""
    type: str = "polygon_cordon"
    area: str
    start_minute: int = Field(ge=0)
    end_minute: int = Field(ge=0)


class CapacityChange(BaseModel):
    """Capacity change specification."""
    edge_selector: str
    multiplier: float = Field(gt=0.0)


class ProtectedCorridor(BaseModel):
    """Protected corridor specification."""
    name: str
    rule: str
    multiplier: float = Field(gt=0.0)


class StagedEgress(BaseModel):
    """Staged egress specification."""
    area: str
    start_minute: int = Field(ge=0)
    release_rate: str


class ScenarioConfig(BaseModel):
    """Scenario configuration YAML schema."""
    id: str
    city: str = "london"
    seed: int = Field(default=42)
    closures: List[PolygonCordon] = Field(default_factory=list)
    capacity_changes: List[CapacityChange] = Field(default_factory=list)
    protected_corridors: List[ProtectedCorridor] = Field(default_factory=list)
    staged_egress: List[StagedEgress] = Field(default_factory=list)
    notes: str = ""


# ===== Simulation Results Models =====

class SimulationMetrics(BaseModel):
    """Simulation metrics."""
    clearance_time: float = Field(description="Time for 99% evacuation")
    max_queue: float = Field(description="Worst edge congestion")
    fairness_index: float = Field(description="1 - Gini coefficient")
    robustness: float = Field(description="Average score under random failures")


class ScenarioResult(BaseModel):
    """Scenario simulation result."""
    scenario_id: str
    metrics: SimulationMetrics
    status: TaskStatus
    retry_count: int = 0
    duration_ms: int
    error_message: Optional[str] = None


# ===== Decision Support Models =====

class Citation(BaseModel):
    """Citation for RAG answers."""
    title: str
    url: str
    published_at: datetime
    source: str
    score: float


class ExplanationResult(BaseModel):
    """Explainer agent result."""
    scenario_id: str
    answer: str
    citations: List[Citation]
    mode: str = "retrieval_only"
    abstained: bool = False


class ScenarioRanking(BaseModel):
    """Scenario ranking result."""
    scenario_id: str
    score: float
    rank: int


class JudgeResult(BaseModel):
    """Judge agent result."""
    ranking: List[ScenarioRanking]
    weights: UserPreferences
    validation_passed: bool
    best_scenario_id: str


# ===== Run Management Models =====

class RunArtifact(BaseModel):
    """Decision memo / run artifact."""
    run_id: str
    best_scenario: str
    weights: UserPreferences
    metrics: SimulationMetrics
    justification: ExplanationResult


class RunStatus(BaseModel):
    """Run status response."""
    run_id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    scenario_count: int = 0
    best_scenario_id: Optional[str] = None


# ===== API Request/Response Models =====

class RunRequest(BaseModel):
    """Request to start a new evacuation planning run."""
    intent: UserIntent
    city: str = Field(default="london", description="City for evacuation simulation (london)")


class SearchRequest(BaseModel):
    """Search request for RAG system."""
    query: str
    k: int = Field(default=8, ge=1, le=20)
    tiers: List[SourceTier] = Field(default_factory=lambda: [SourceTier.GOV_PRIMARY])
    max_age_days: int = Field(default=7, ge=1, le=30)


class SearchResult(BaseModel):
    """Search result item."""
    doc_id: str
    title: str
    url: str
    source: str
    published_at: datetime
    score: float


class SearchResponse(BaseModel):
    """Search response."""
    results: List[SearchResult]
    total_count: int
    query: str


# ===== SSE Event Models =====

class SSEEvent(BaseModel):
    """Server-Sent Event base model."""
    event: str
    data: Dict[str, Any]
    retry: Optional[int] = None


class PlannerProgressEvent(BaseModel):
    """Planner progress event."""
    status: str
    num_scenarios: Optional[int] = None
    message: Optional[str] = None


class WorkerResultEvent(BaseModel):
    """Worker result event."""
    scenario_id: str
    metrics: Optional[SimulationMetrics] = None
    status: TaskStatus
    retry_count: int = 0
    error_message: Optional[str] = None


class JudgeSummaryEvent(BaseModel):
    """Judge summary event."""
    ranking: List[ScenarioRanking]
    best_scenario_id: str


class ExplainerAnswerEvent(BaseModel):
    """Explainer answer event."""
    scenario_id: str
    answer: str
    citations: List[Citation]
    abstained: bool = False


class RunCompleteEvent(BaseModel):
    """Run complete event."""
    run_id: str
    best_scenario: str
    status: TaskStatus


# ===== Logging Models =====

class LogEvent(BaseModel):
    """Structured log event."""
    ts: datetime
    run_id: Optional[str] = None
    scenario_id: Optional[str] = None
    agent: AgentType
    step: str
    inputs_hash: str
    config_hash: str
    status: TaskStatus
    retry_count: int = 0
    duration_ms: int
    metrics: Optional[Dict[str, float]] = None
    message: Optional[str] = None


class ProvenanceRecord(BaseModel):
    """Lineage/provenance record."""
    run_id: str
    path: str
    sha256: str
    size: int
    producer_agent: AgentType
    source_url: Optional[str] = None
    parent_hash: Optional[str] = None
    created_at: datetime
