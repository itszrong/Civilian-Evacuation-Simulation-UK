"""
Tests for models.schemas module.
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from models.schemas import (
    # Enums
    SourceTier, DocumentType, TaskStatus, AgentType,
    # Data Feed Models
    DataSource, SourceTierConfig, SourcesConfig, CanonicalDocument,
    # User Intent & Scenario Models
    ScenarioConstraints, UserPreferences, UserIntent,
    # Scenario Models
    PolygonCordon, CapacityChange, ProtectedCorridor, StagedEgress, ScenarioConfig,
    # Simulation Results Models
    SimulationMetrics, ScenarioResult,
    # Decision Support Models
    Citation, ExplanationResult, ScenarioRanking, JudgeResult,
    # Run Management Models
    RunArtifact, RunStatus,
    # API Request/Response Models
    RunRequest, SearchRequest, SearchResult, SearchResponse,
    # SSE Event Models
    SSEEvent, PlannerProgressEvent, WorkerResultEvent, JudgeSummaryEvent,
    ExplainerAnswerEvent, RunCompleteEvent,
    # Logging Models
    LogEvent, ProvenanceRecord
)


class TestEnums:
    """Test enumeration classes."""
    
    def test_source_tier_enum(self):
        """Test SourceTier enum values."""
        assert SourceTier.GOV_PRIMARY == "gov_primary"
        assert SourceTier.NEWS_VERIFIED == "news_verified"
        
        # Test enum membership
        assert "gov_primary" in SourceTier
        assert "news_verified" in SourceTier
        assert "invalid_tier" not in SourceTier
    
    def test_document_type_enum(self):
        """Test DocumentType enum values."""
        assert DocumentType.POLICY == "policy"
        assert DocumentType.ALERT == "alert"
        assert DocumentType.NEWS == "news"
    
    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
    
    def test_agent_type_enum(self):
        """Test AgentType enum values."""
        assert AgentType.PLANNER == "planner"
        assert AgentType.WORKER == "worker"
        assert AgentType.JUDGE == "judge"
        assert AgentType.EXPLAINER == "explainer"
        assert AgentType.FEEDS == "feeds"
        assert AgentType.SIMULATION == "simulation"
        assert AgentType.EMERGENCY_PLANNER == "emergency_planner"


class TestDataFeedModels:
    """Test data feed related models."""
    
    def test_data_source_creation(self):
        """Test DataSource model creation."""
        source = DataSource(
            name="test_source",
            type="api",
            base="https://api.example.com",
            url="/v1/data"
        )
        
        assert source.name == "test_source"
        assert source.type == "api"
        assert source.base == "https://api.example.com"
        assert source.url == "/v1/data"
    
    def test_data_source_minimal(self):
        """Test DataSource with minimal required fields."""
        source = DataSource(name="minimal_source", type="rss")
        
        assert source.name == "minimal_source"
        assert source.type == "rss"
        assert source.base is None
        assert source.url is None
    
    def test_source_tier_config(self):
        """Test SourceTierConfig model."""
        sources = [
            DataSource(name="source1", type="api", url="https://api1.com"),
            DataSource(name="source2", type="rss", url="https://rss2.com")
        ]
        
        config = SourceTierConfig(
            name="test_tier",
            freshness_days=7,
            sources=sources
        )
        
        assert config.name == "test_tier"
        assert config.freshness_days == 7
        assert len(config.sources) == 2
        assert config.sources[0].name == "source1"
    
    def test_sources_config(self):
        """Test complete SourcesConfig model."""
        tier_config = SourceTierConfig(
            name="gov_primary",
            freshness_days=7,
            sources=[DataSource(name="gov_api", type="api")]
        )
        
        config = SourcesConfig(
            tiers=[tier_config],
            policies={"max_docs": 100, "min_score": 0.7}
        )
        
        assert len(config.tiers) == 1
        assert config.tiers[0].name == "gov_primary"
        assert config.policies["max_docs"] == 100
    
    def test_canonical_document(self):
        """Test CanonicalDocument model."""
        now = datetime.now()
        
        doc = CanonicalDocument(
            doc_id="doc_123",
            url="https://example.com/doc",
            source="test_source",
            tier=SourceTier.GOV_PRIMARY,
            published_at=now,
            fetched_at=now,
            title="Test Document",
            text="This is test content",
            type=DocumentType.POLICY,
            jurisdiction="UK",
            entities=["London", "Transport"],
            hash="abc123def456"
        )
        
        assert doc.doc_id == "doc_123"
        assert doc.tier == SourceTier.GOV_PRIMARY
        assert doc.type == DocumentType.POLICY
        assert len(doc.entities) == 2
        assert "London" in doc.entities


class TestUserIntentModels:
    """Test user intent and scenario constraint models."""
    
    def test_scenario_constraints_defaults(self):
        """Test ScenarioConstraints with default values."""
        constraints = ScenarioConstraints()
        
        assert constraints.max_scenarios == 12
        assert constraints.compute_budget_minutes == 5
        assert constraints.must_protect_pois == []
    
    def test_scenario_constraints_custom(self):
        """Test ScenarioConstraints with custom values."""
        constraints = ScenarioConstraints(
            max_scenarios=20,
            compute_budget_minutes=10,
            must_protect_pois=["Westminster", "Tower Bridge"]
        )
        
        assert constraints.max_scenarios == 20
        assert constraints.compute_budget_minutes == 10
        assert len(constraints.must_protect_pois) == 2
    
    def test_scenario_constraints_validation(self):
        """Test ScenarioConstraints validation."""
        # Test max_scenarios limit
        with pytest.raises(ValidationError):
            ScenarioConstraints(max_scenarios=25)  # Over limit of 20
        
        # Test compute_budget_minutes limit
        with pytest.raises(ValidationError):
            ScenarioConstraints(compute_budget_minutes=20)  # Over limit of 15
    
    def test_user_preferences_defaults(self):
        """Test UserPreferences with default values."""
        prefs = UserPreferences()
        
        assert prefs.fairness_weight == 0.35
        assert prefs.clearance_weight == 0.5
        assert prefs.robustness_weight == 0.15
        
        # Check they sum to 1.0
        total = prefs.fairness_weight + prefs.clearance_weight + prefs.robustness_weight
        assert abs(total - 1.0) < 0.01
    
    def test_user_preferences_custom_valid(self):
        """Test UserPreferences with custom valid weights."""
        prefs = UserPreferences(
            fairness_weight=0.4,
            clearance_weight=0.4,
            robustness_weight=0.2
        )
        
        assert prefs.fairness_weight == 0.4
        assert prefs.clearance_weight == 0.4
        assert prefs.robustness_weight == 0.2
    
    def test_user_preferences_weights_validation(self):
        """Test UserPreferences weight validation."""
        # Test weights that don't sum to 1.0
        with pytest.raises(ValidationError):
            UserPreferences(
                fairness_weight=0.5,
                clearance_weight=0.5,
                robustness_weight=0.2  # Total = 1.2, should fail
            )
    
    def test_user_preferences_range_validation(self):
        """Test UserPreferences range validation."""
        # Test negative weight
        with pytest.raises(ValidationError):
            UserPreferences(fairness_weight=-0.1)
        
        # Test weight over 1.0
        with pytest.raises(ValidationError):
            UserPreferences(clearance_weight=1.5)
    
    def test_user_intent_creation(self):
        """Test UserIntent model creation."""
        constraints = ScenarioConstraints(max_scenarios=10)
        preferences = UserPreferences()
        
        intent = UserIntent(
            objective="Test evacuation planning for central London",
            city="london",
            constraints=constraints,
            hypotheses=["Transport will be congested", "Emergency routes needed"],
            preferences=preferences,
            freshness_days=14,
            tiers=[SourceTier.GOV_PRIMARY, SourceTier.NEWS_VERIFIED]
        )
        
        assert intent.objective == "Test evacuation planning for central London"
        assert intent.city == "london"
        assert len(intent.hypotheses) == 2
        assert intent.freshness_days == 14
        assert len(intent.tiers) == 2
    
    def test_user_intent_defaults(self):
        """Test UserIntent with default values."""
        constraints = ScenarioConstraints()
        preferences = UserPreferences()
        
        intent = UserIntent(
            objective="Test objective",
            constraints=constraints,
            preferences=preferences
        )
        
        assert intent.city == "london"
        assert intent.hypotheses == []
        assert intent.freshness_days == 7
        assert intent.tiers == [SourceTier.GOV_PRIMARY]
    
    def test_user_intent_validation(self):
        """Test UserIntent validation."""
        constraints = ScenarioConstraints()
        preferences = UserPreferences()
        
        # Test freshness_days validation
        with pytest.raises(ValidationError):
            UserIntent(
                objective="Test",
                constraints=constraints,
                preferences=preferences,
                freshness_days=0  # Below minimum
            )
        
        with pytest.raises(ValidationError):
            UserIntent(
                objective="Test",
                constraints=constraints,
                preferences=preferences,
                freshness_days=35  # Above maximum
            )


class TestScenarioModels:
    """Test scenario configuration models."""
    
    def test_polygon_cordon(self):
        """Test PolygonCordon model."""
        cordon = PolygonCordon(
            area="Westminster",
            start_minute=0,
            end_minute=60
        )
        
        assert cordon.type == "polygon_cordon"
        assert cordon.area == "Westminster"
        assert cordon.start_minute == 0
        assert cordon.end_minute == 60
    
    def test_polygon_cordon_validation(self):
        """Test PolygonCordon validation."""
        # Test negative start_minute
        with pytest.raises(ValidationError):
            PolygonCordon(area="Test", start_minute=-1, end_minute=60)
        
        # Test negative end_minute
        with pytest.raises(ValidationError):
            PolygonCordon(area="Test", start_minute=0, end_minute=-1)
    
    def test_capacity_change(self):
        """Test CapacityChange model."""
        change = CapacityChange(
            edge_selector="tube_lines",
            multiplier=0.5
        )
        
        assert change.edge_selector == "tube_lines"
        assert change.multiplier == 0.5
    
    def test_capacity_change_validation(self):
        """Test CapacityChange validation."""
        # Test zero multiplier
        with pytest.raises(ValidationError):
            CapacityChange(edge_selector="test", multiplier=0.0)
        
        # Test negative multiplier
        with pytest.raises(ValidationError):
            CapacityChange(edge_selector="test", multiplier=-0.5)
    
    def test_protected_corridor(self):
        """Test ProtectedCorridor model."""
        corridor = ProtectedCorridor(
            name="Emergency Route 1",
            rule="emergency_services",
            multiplier=1.5
        )
        
        assert corridor.name == "Emergency Route 1"
        assert corridor.rule == "emergency_services"
        assert corridor.multiplier == 1.5
    
    def test_staged_egress(self):
        """Test StagedEgress model."""
        egress = StagedEgress(
            area="City of London",
            start_minute=10,
            release_rate="gradual"
        )
        
        assert egress.area == "City of London"
        assert egress.start_minute == 10
        assert egress.release_rate == "gradual"
    
    def test_scenario_config_complete(self):
        """Test complete ScenarioConfig model."""
        config = ScenarioConfig(
            id="test_scenario_001",
            city="london",
            seed=42,
            closures=[
                PolygonCordon(area="Westminster", start_minute=0, end_minute=60)
            ],
            capacity_changes=[
                CapacityChange(edge_selector="tube_lines", multiplier=0.5)
            ],
            protected_corridors=[
                ProtectedCorridor(name="Route 1", rule="emergency", multiplier=1.5)
            ],
            staged_egress=[
                StagedEgress(area="City", start_minute=10, release_rate="gradual")
            ],
            notes="Test scenario configuration"
        )
        
        assert config.id == "test_scenario_001"
        assert config.city == "london"
        assert config.seed == 42
        assert len(config.closures) == 1
        assert len(config.capacity_changes) == 1
        assert len(config.protected_corridors) == 1
        assert len(config.staged_egress) == 1
        assert config.notes == "Test scenario configuration"
    
    def test_scenario_config_minimal(self):
        """Test minimal ScenarioConfig model."""
        config = ScenarioConfig(id="minimal_scenario")
        
        assert config.id == "minimal_scenario"
        assert config.city == "london"
        assert config.seed == 42
        assert config.closures == []
        assert config.capacity_changes == []
        assert config.protected_corridors == []
        assert config.staged_egress == []
        assert config.notes == ""


class TestSimulationModels:
    """Test simulation result models."""
    
    def test_simulation_metrics(self):
        """Test SimulationMetrics model."""
        metrics = SimulationMetrics(
            clearance_time=1800.0,
            max_queue=150.0,
            fairness_index=0.85,
            robustness=0.75
        )
        
        assert metrics.clearance_time == 1800.0
        assert metrics.max_queue == 150.0
        assert metrics.fairness_index == 0.85
        assert metrics.robustness == 0.75
    
    def test_scenario_result(self):
        """Test ScenarioResult model."""
        metrics = SimulationMetrics(
            clearance_time=1800.0,
            max_queue=150.0,
            fairness_index=0.85,
            robustness=0.75
        )
        
        result = ScenarioResult(
            scenario_id="test_scenario_001",
            metrics=metrics,
            status=TaskStatus.COMPLETED,
            retry_count=1,
            duration_ms=5000,
            error_message=None
        )
        
        assert result.scenario_id == "test_scenario_001"
        assert result.status == TaskStatus.COMPLETED
        assert result.retry_count == 1
        assert result.duration_ms == 5000
        assert result.error_message is None
    
    def test_scenario_result_with_error(self):
        """Test ScenarioResult with error."""
        metrics = SimulationMetrics(
            clearance_time=0.0,
            max_queue=0.0,
            fairness_index=0.0,
            robustness=0.0
        )
        
        result = ScenarioResult(
            scenario_id="failed_scenario",
            metrics=metrics,
            status=TaskStatus.FAILED,
            retry_count=3,
            duration_ms=1000,
            error_message="Simulation timeout"
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.retry_count == 3
        assert result.error_message == "Simulation timeout"


class TestDecisionSupportModels:
    """Test decision support models."""
    
    def test_citation(self):
        """Test Citation model."""
        now = datetime.now()
        
        citation = Citation(
            title="Emergency Planning Guidelines",
            url="https://gov.uk/emergency-planning",
            published_at=now,
            source="gov_uk",
            score=0.95
        )
        
        assert citation.title == "Emergency Planning Guidelines"
        assert citation.url == "https://gov.uk/emergency-planning"
        assert citation.source == "gov_uk"
        assert citation.score == 0.95
    
    def test_explanation_result(self):
        """Test ExplanationResult model."""
        now = datetime.now()
        
        citations = [
            Citation(
                title="Test Doc",
                url="https://example.com",
                published_at=now,
                source="test",
                score=0.8
            )
        ]
        
        result = ExplanationResult(
            scenario_id="test_scenario",
            answer="This scenario provides optimal evacuation routes...",
            citations=citations,
            mode="retrieval_only",
            abstained=False
        )
        
        assert result.scenario_id == "test_scenario"
        assert "optimal evacuation" in result.answer
        assert len(result.citations) == 1
        assert result.mode == "retrieval_only"
        assert result.abstained is False
    
    def test_scenario_ranking(self):
        """Test ScenarioRanking model."""
        ranking = ScenarioRanking(
            scenario_id="scenario_001",
            score=0.85,
            rank=1
        )
        
        assert ranking.scenario_id == "scenario_001"
        assert ranking.score == 0.85
        assert ranking.rank == 1
    
    def test_judge_result(self):
        """Test JudgeResult model."""
        rankings = [
            ScenarioRanking(scenario_id="s1", score=0.9, rank=1),
            ScenarioRanking(scenario_id="s2", score=0.8, rank=2)
        ]
        
        weights = UserPreferences()
        
        result = JudgeResult(
            ranking=rankings,
            weights=weights,
            validation_passed=True,
            best_scenario_id="s1"
        )
        
        assert len(result.ranking) == 2
        assert result.ranking[0].rank == 1
        assert result.validation_passed is True
        assert result.best_scenario_id == "s1"


class TestAPIModels:
    """Test API request/response models."""
    
    def test_search_request(self):
        """Test SearchRequest model."""
        request = SearchRequest(
            query="emergency evacuation procedures",
            k=10,
            tiers=[SourceTier.GOV_PRIMARY],
            max_age_days=14
        )
        
        assert request.query == "emergency evacuation procedures"
        assert request.k == 10
        assert request.tiers == [SourceTier.GOV_PRIMARY]
        assert request.max_age_days == 14
    
    def test_search_request_defaults(self):
        """Test SearchRequest with defaults."""
        request = SearchRequest(query="test query")
        
        assert request.k == 8
        assert request.tiers == [SourceTier.GOV_PRIMARY]
        assert request.max_age_days == 7
    
    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Test k validation
        with pytest.raises(ValidationError):
            SearchRequest(query="test", k=0)
        
        with pytest.raises(ValidationError):
            SearchRequest(query="test", k=25)
        
        # Test max_age_days validation
        with pytest.raises(ValidationError):
            SearchRequest(query="test", max_age_days=0)
        
        with pytest.raises(ValidationError):
            SearchRequest(query="test", max_age_days=35)
    
    def test_search_result(self):
        """Test SearchResult model."""
        now = datetime.now()
        
        result = SearchResult(
            doc_id="doc_123",
            title="Test Document",
            url="https://example.com/doc",
            source="test_source",
            published_at=now,
            score=0.85
        )
        
        assert result.doc_id == "doc_123"
        assert result.title == "Test Document"
        assert result.score == 0.85
    
    def test_search_response(self):
        """Test SearchResponse model."""
        now = datetime.now()
        
        results = [
            SearchResult(
                doc_id="doc_1",
                title="Doc 1",
                url="https://example.com/1",
                source="source1",
                published_at=now,
                score=0.9
            )
        ]
        
        response = SearchResponse(
            results=results,
            total_count=1,
            query="test query"
        )
        
        assert len(response.results) == 1
        assert response.total_count == 1
        assert response.query == "test query"
    
    def test_run_request(self):
        """Test RunRequest model."""
        constraints = ScenarioConstraints()
        preferences = UserPreferences()
        intent = UserIntent(
            objective="Test",
            constraints=constraints,
            preferences=preferences
        )
        
        request = RunRequest(intent=intent, city="london")
        
        assert request.intent.objective == "Test"
        assert request.city == "london"
    
    def test_run_request_default_city(self):
        """Test RunRequest with default city."""
        constraints = ScenarioConstraints()
        preferences = UserPreferences()
        intent = UserIntent(
            objective="Test",
            constraints=constraints,
            preferences=preferences
        )
        
        request = RunRequest(intent=intent)
        
        assert request.city == "london"


class TestSSEEventModels:
    """Test Server-Sent Event models."""
    
    def test_sse_event(self):
        """Test SSEEvent model."""
        event = SSEEvent(
            event="test_event",
            data={"message": "test", "count": 5},
            retry=1000
        )
        
        assert event.event == "test_event"
        assert event.data["message"] == "test"
        assert event.retry == 1000
    
    def test_planner_progress_event(self):
        """Test PlannerProgressEvent model."""
        event = PlannerProgressEvent(
            status="generating_scenarios",
            num_scenarios=5,
            message="Generated 5 scenarios"
        )
        
        assert event.status == "generating_scenarios"
        assert event.num_scenarios == 5
        assert event.message == "Generated 5 scenarios"
    
    def test_worker_result_event(self):
        """Test WorkerResultEvent model."""
        metrics = SimulationMetrics(
            clearance_time=1800.0,
            max_queue=150.0,
            fairness_index=0.85,
            robustness=0.75
        )
        
        event = WorkerResultEvent(
            scenario_id="test_scenario",
            metrics=metrics,
            status=TaskStatus.COMPLETED,
            retry_count=0
        )
        
        assert event.scenario_id == "test_scenario"
        assert event.metrics.clearance_time == 1800.0
        assert event.status == TaskStatus.COMPLETED
        assert event.retry_count == 0


class TestLoggingModels:
    """Test logging and provenance models."""
    
    def test_log_event(self):
        """Test LogEvent model."""
        now = datetime.now()
        
        event = LogEvent(
            ts=now,
            run_id="run_123",
            scenario_id="scenario_456",
            agent=AgentType.PLANNER,
            step="generate_scenarios",
            inputs_hash="abc123",
            config_hash="def456",
            status=TaskStatus.COMPLETED,
            retry_count=0,
            duration_ms=5000,
            metrics={"scenarios_generated": 10},
            message="Successfully generated scenarios"
        )
        
        assert event.run_id == "run_123"
        assert event.scenario_id == "scenario_456"
        assert event.agent == AgentType.PLANNER
        assert event.step == "generate_scenarios"
        assert event.status == TaskStatus.COMPLETED
        assert event.duration_ms == 5000
        assert event.metrics["scenarios_generated"] == 10
    
    def test_provenance_record(self):
        """Test ProvenanceRecord model."""
        now = datetime.now()
        
        record = ProvenanceRecord(
            run_id="run_123",
            path="/storage/scenarios/scenario_001.yaml",
            sha256="abc123def456",
            size=1024,
            producer_agent=AgentType.PLANNER,
            source_url="https://api.example.com/data",
            parent_hash="parent123",
            created_at=now
        )
        
        assert record.run_id == "run_123"
        assert record.path == "/storage/scenarios/scenario_001.yaml"
        assert record.sha256 == "abc123def456"
        assert record.size == 1024
        assert record.producer_agent == AgentType.PLANNER
        assert record.source_url == "https://api.example.com/data"
        assert record.parent_hash == "parent123"


@pytest.mark.unit
class TestSchemaIntegration:
    """Integration tests for schema interactions."""
    
    def test_complete_user_workflow(self):
        """Test complete user workflow with all related schemas."""
        # Create user intent
        constraints = ScenarioConstraints(max_scenarios=5)
        preferences = UserPreferences(
            fairness_weight=0.4,
            clearance_weight=0.4,
            robustness_weight=0.2
        )
        intent = UserIntent(
            objective="Plan evacuation for Thames flood",
            constraints=constraints,
            preferences=preferences,
            hypotheses=["Transport will be disrupted"]
        )
        
        # Create run request
        request = RunRequest(intent=intent)
        
        # Create scenario config
        scenario = ScenarioConfig(
            id="flood_scenario_001",
            closures=[
                PolygonCordon(area="Thames Barrier", start_minute=0, end_minute=120)
            ]
        )
        
        # Create simulation results
        metrics = SimulationMetrics(
            clearance_time=2400.0,
            max_queue=200.0,
            fairness_index=0.8,
            robustness=0.7
        )
        
        result = ScenarioResult(
            scenario_id="flood_scenario_001",
            metrics=metrics,
            status=TaskStatus.COMPLETED,
            duration_ms=10000
        )
        
        # Verify all components work together
        assert request.intent.objective == "Plan evacuation for Thames flood"
        assert scenario.closures[0].area == "Thames Barrier"
        assert result.metrics.clearance_time == 2400.0
        assert result.status == TaskStatus.COMPLETED
    
    def test_schema_serialization(self):
        """Test that schemas can be serialized to/from JSON."""
        preferences = UserPreferences()
        
        # Test serialization
        json_data = preferences.model_dump()
        assert isinstance(json_data, dict)
        assert "fairness_weight" in json_data
        
        # Test deserialization
        reconstructed = UserPreferences(**json_data)
        assert reconstructed.fairness_weight == preferences.fairness_weight
        assert reconstructed.clearance_weight == preferences.clearance_weight
        assert reconstructed.robustness_weight == preferences.robustness_weight
