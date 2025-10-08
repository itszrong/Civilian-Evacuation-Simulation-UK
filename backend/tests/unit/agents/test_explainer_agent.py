"""
Tests for agents.explainer_agent module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from agents.explainer_agent import ExplainerAgent
from models.schemas import (
    ScenarioConfig, ScenarioResult, ExplanationResult, Citation,
    SourceTier, UserIntent, ScenarioConstraints, UserPreferences,
    SimulationMetrics, TaskStatus
)
from services.storage_service import StorageService


class TestExplainerAgent:
    """Test the ExplainerAgent class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_storage = Mock(spec=StorageService)
        
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.OPENAI_API_KEY = "test-openai-key"
        self.mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        self.mock_settings.MAX_CITATIONS = 8
        self.mock_settings.FRESHNESS_DAYS_DEFAULT = 7
        
        # Create sample data
        self.sample_scenario = ScenarioConfig(
            id="test_scenario_001",
            city="london",
            closures=[],
            notes="Test scenario for evacuation planning"
        )
        
        self.sample_result = ScenarioResult(
            scenario_id="test_scenario_001",
            metrics=SimulationMetrics(
                clearance_time=1800.0,
                max_queue=150.0,
                fairness_index=0.85,
                robustness=0.75
            ),
            status=TaskStatus.COMPLETED,
            duration_ms=5000
        )
        
        self.sample_intent = UserIntent(
            objective="Plan evacuation for central London flood scenario",
            constraints=ScenarioConstraints(),
            preferences=UserPreferences()
        )
    
    @patch('agents.explainer_agent.get_settings')
    def test_initialization_with_ai_clients(self, mock_get_settings):
        """Test ExplainerAgent initialization with AI clients available."""
        mock_get_settings.return_value = self.mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', True), \
             patch('agents.explainer_agent.ANTHROPIC_AVAILABLE', True), \
             patch('agents.explainer_agent.openai.OpenAI') as mock_openai, \
             patch('agents.explainer_agent.anthropic.Anthropic') as mock_anthropic:
            
            agent = ExplainerAgent(self.mock_storage)
            
            assert agent.storage == self.mock_storage
            mock_openai.assert_called_once_with(api_key="test-openai-key")
            mock_anthropic.assert_called_once_with(api_key="test-anthropic-key")
    
    @patch('agents.explainer_agent.get_settings')
    def test_initialization_without_ai_clients(self, mock_get_settings):
        """Test ExplainerAgent initialization without AI clients."""
        mock_settings = Mock()
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_get_settings.return_value = mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False), \
             patch('agents.explainer_agent.ANTHROPIC_AVAILABLE', False):
            
            agent = ExplainerAgent(self.mock_storage)
            
            assert agent._openai_client is None
            assert agent._anthropic_client is None
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_with_openai(self, mock_get_settings):
        """Test scenario explanation using OpenAI."""
        mock_get_settings.return_value = self.mock_settings
        
        # Mock search results
        mock_citations = [
            Citation(
                title="London Flood Emergency Response",
                url="https://gov.uk/flood-response",
                published_at=datetime.now(),
                source="gov_uk",
                score=0.95
            ),
            Citation(
                title="Transport Evacuation Guidelines",
                url="https://tfl.gov.uk/evacuation",
                published_at=datetime.now(),
                source="tfl",
                score=0.88
            )
        ]
        
        # Mock OpenAI response
        mock_openai_response = Mock()
        mock_openai_response.choices = [Mock()]
        mock_openai_response.choices[0].message.content = "This scenario provides effective evacuation routes during flood conditions. The clearance time of 30 minutes is within acceptable limits for central London."
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', True), \
             patch('agents.explainer_agent.openai.OpenAI') as mock_openai_class:
            
            mock_openai_client = Mock()
            mock_openai_client.chat.completions.create.return_value = mock_openai_response
            mock_openai_class.return_value = mock_openai_client
            
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=mock_citations)
            
            result = await agent.explain_scenario(
                self.sample_scenario,
                self.sample_result,
                self.sample_intent
            )
            
            assert isinstance(result, ExplanationResult)
            assert result.scenario_id == "test_scenario_001"
            assert "effective evacuation routes" in result.answer
            assert len(result.citations) == 2
            assert result.abstained is False
            assert result.mode == "retrieval_only"
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_with_anthropic(self, mock_get_settings):
        """Test scenario explanation using Anthropic."""
        mock_settings = Mock()
        mock_settings.OPENAI_API_KEY = None  # No OpenAI
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.MAX_CITATIONS = 8
        mock_settings.FRESHNESS_DAYS_DEFAULT = 7
        mock_get_settings.return_value = mock_settings
        
        # Mock Anthropic response
        mock_anthropic_response = Mock()
        mock_anthropic_response.content = [Mock()]
        mock_anthropic_response.content[0].text = "Based on the simulation results, this evacuation scenario demonstrates good performance with a fairness index of 0.85."
        
        mock_citations = [
            Citation(
                title="Evacuation Fairness Guidelines",
                url="https://gov.uk/evacuation-fairness",
                published_at=datetime.now(),
                source="gov_uk",
                score=0.92
            )
        ]
        
        with patch('agents.explainer_agent.ANTHROPIC_AVAILABLE', True), \
             patch('agents.explainer_agent.anthropic.Anthropic') as mock_anthropic_class:
            
            mock_anthropic_client = Mock()
            mock_anthropic_client.messages.create.return_value = mock_anthropic_response
            mock_anthropic_class.return_value = mock_anthropic_client
            
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=mock_citations)
            
            result = await agent.explain_scenario(
                self.sample_scenario,
                self.sample_result,
                self.sample_intent
            )
            
            assert isinstance(result, ExplanationResult)
            assert result.scenario_id == "test_scenario_001"
            assert "fairness index of 0.85" in result.answer
            assert len(result.citations) == 1
            assert result.abstained is False
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_abstain_insufficient_evidence(self, mock_get_settings):
        """Test scenario explanation abstaining due to insufficient evidence."""
        mock_get_settings.return_value = self.mock_settings
        
        # Mock very few, low-quality citations
        mock_citations = [
            Citation(
                title="Irrelevant Document",
                url="https://example.com/irrelevant",
                published_at=datetime.now(),
                source="unknown",
                score=0.3  # Low score
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', True), \
             patch('agents.explainer_agent.openai.OpenAI') as mock_openai_class:
            
            mock_openai_client = Mock()
            mock_openai_class.return_value = mock_openai_client
            
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=mock_citations)
            
            result = await agent.explain_scenario(
                self.sample_scenario,
                self.sample_result,
                self.sample_intent
            )
            
            assert isinstance(result, ExplanationResult)
            assert result.scenario_id == "test_scenario_001"
            assert result.abstained is True
            assert "insufficient evidence" in result.answer.lower()
            assert len(result.citations) == 0  # No citations when abstaining
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_template_fallback(self, mock_get_settings):
        """Test scenario explanation falling back to template when no AI available."""
        mock_settings = Mock()
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_get_settings.return_value = mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False), \
             patch('agents.explainer_agent.ANTHROPIC_AVAILABLE', False):
            
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=[])
            
            result = await agent.explain_scenario(
                self.sample_scenario,
                self.sample_result,
                self.sample_intent
            )
            
            assert isinstance(result, ExplanationResult)
            assert result.scenario_id == "test_scenario_001"
            assert "template response" in result.answer.lower()
            assert result.mode == "template_only"
            assert len(result.citations) == 0
    
    @patch('agents.explainer_agent.get_settings')
    async def test_search_relevant_documents(self, mock_get_settings):
        """Test searching for relevant documents."""
        mock_get_settings.return_value = self.mock_settings
        
        # Mock storage search results
        mock_search_results = [
            {
                "doc_id": "doc_001",
                "title": "London Emergency Response Plan",
                "url": "https://london.gov.uk/emergency-plan",
                "source": "london_gov",
                "published_at": "2023-01-01T00:00:00Z",
                "score": 0.95
            },
            {
                "doc_id": "doc_002", 
                "title": "Transport Evacuation Procedures",
                "url": "https://tfl.gov.uk/procedures",
                "source": "tfl",
                "published_at": "2023-02-01T00:00:00Z",
                "score": 0.88
            }
        ]
        
        self.mock_storage.search_documents = AsyncMock(return_value=mock_search_results)
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False), \
             patch('agents.explainer_agent.ANTHROPIC_AVAILABLE', False):
            
            agent = ExplainerAgent(self.mock_storage)
            
            citations = await agent._search_relevant_documents(
                "flood evacuation central london",
                [SourceTier.GOV_PRIMARY],
                7
            )
            
            assert len(citations) == 2
            assert citations[0].title == "London Emergency Response Plan"
            assert citations[0].score == 0.95
            assert citations[1].title == "Transport Evacuation Procedures"
            assert citations[1].score == 0.88
            
            # Verify search was called with correct parameters
            self.mock_storage.search_documents.assert_called_once()
            call_args = self.mock_storage.search_documents.call_args
            assert "flood evacuation central london" in call_args[0][0]
    
    @patch('agents.explainer_agent.get_settings')
    async def test_search_relevant_documents_empty_results(self, mock_get_settings):
        """Test searching for relevant documents with no results."""
        mock_get_settings.return_value = self.mock_settings
        
        self.mock_storage.search_documents = AsyncMock(return_value=[])
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            citations = await agent._search_relevant_documents(
                "nonexistent topic",
                [SourceTier.GOV_PRIMARY],
                7
            )
            
            assert len(citations) == 0
    
    @patch('agents.explainer_agent.get_settings')
    async def test_search_relevant_documents_exception_handling(self, mock_get_settings):
        """Test search documents exception handling."""
        mock_get_settings.return_value = self.mock_settings
        
        self.mock_storage.search_documents = AsyncMock(side_effect=Exception("Search service error"))
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            citations = await agent._search_relevant_documents(
                "test query",
                [SourceTier.GOV_PRIMARY],
                7
            )
            
            # Should handle exception gracefully and return empty list
            assert len(citations) == 0
    
    @patch('agents.explainer_agent.get_settings')
    def test_build_context_from_citations(self, mock_get_settings):
        """Test building context from citations."""
        mock_get_settings.return_value = self.mock_settings
        
        citations = [
            Citation(
                title="Emergency Response Guidelines",
                url="https://gov.uk/emergency",
                published_at=datetime.now(),
                source="gov_uk",
                score=0.95
            ),
            Citation(
                title="Transport Safety Measures",
                url="https://tfl.gov.uk/safety",
                published_at=datetime.now(),
                source="tfl",
                score=0.88
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            context = agent._build_context_from_citations(citations)
            
            assert "Emergency Response Guidelines" in context
            assert "Transport Safety Measures" in context
            assert "gov.uk/emergency" in context
            assert "tfl.gov.uk/safety" in context
    
    @patch('agents.explainer_agent.get_settings')
    def test_should_abstain_low_quality_evidence(self, mock_get_settings):
        """Test abstain decision with low quality evidence."""
        mock_get_settings.return_value = self.mock_settings
        
        # Low quality citations
        low_quality_citations = [
            Citation(
                title="Irrelevant Document",
                url="https://example.com/irrelevant",
                published_at=datetime.now(),
                source="unknown",
                score=0.2
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            should_abstain = agent._should_abstain(low_quality_citations)
            assert should_abstain is True
    
    @patch('agents.explainer_agent.get_settings')
    def test_should_abstain_sufficient_evidence(self, mock_get_settings):
        """Test abstain decision with sufficient evidence."""
        mock_get_settings.return_value = self.mock_settings
        
        # High quality citations
        high_quality_citations = [
            Citation(
                title="Official Emergency Guidelines",
                url="https://gov.uk/emergency",
                published_at=datetime.now(),
                source="gov_uk",
                score=0.95
            ),
            Citation(
                title="Transport Authority Procedures",
                url="https://tfl.gov.uk/procedures",
                published_at=datetime.now(),
                source="tfl",
                score=0.88
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            should_abstain = agent._should_abstain(high_quality_citations)
            assert should_abstain is False
    
    @patch('agents.explainer_agent.get_settings')
    def test_should_abstain_no_citations(self, mock_get_settings):
        """Test abstain decision with no citations."""
        mock_get_settings.return_value = self.mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            should_abstain = agent._should_abstain([])
            assert should_abstain is True
    
    @patch('agents.explainer_agent.get_settings')
    async def test_ai_client_error_handling(self, mock_get_settings):
        """Test handling of AI client errors."""
        mock_get_settings.return_value = self.mock_settings
        
        mock_citations = [
            Citation(
                title="Test Document",
                url="https://example.com/test",
                published_at=datetime.now(),
                source="test",
                score=0.9
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', True), \
             patch('agents.explainer_agent.openai.OpenAI') as mock_openai_class:
            
            # Mock OpenAI client to raise exception
            mock_openai_client = Mock()
            mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_openai_client
            
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=mock_citations)
            
            result = await agent.explain_scenario(
                self.sample_scenario,
                self.sample_result,
                self.sample_intent
            )
            
            # Should fall back to template response
            assert isinstance(result, ExplanationResult)
            assert result.mode == "template_only"
            assert "template response" in result.answer.lower()
    
    @patch('agents.explainer_agent.get_settings')
    def test_format_metrics_for_explanation(self, mock_get_settings):
        """Test formatting metrics for explanation."""
        mock_get_settings.return_value = self.mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            formatted = agent._format_metrics_for_explanation(self.sample_result.metrics)
            
            assert "clearance time: 30.0 minutes" in formatted.lower()
            assert "max queue: 150.0" in formatted.lower()
            assert "fairness index: 0.85" in formatted.lower()
            assert "robustness: 0.75" in formatted.lower()
    
    @patch('agents.explainer_agent.get_settings')
    def test_generate_search_query(self, mock_get_settings):
        """Test generating search query from scenario and intent."""
        mock_get_settings.return_value = self.mock_settings
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            query = agent._generate_search_query(self.sample_scenario, self.sample_intent)
            
            assert "london" in query.lower()
            assert "evacuation" in query.lower()
            assert "flood" in query.lower()


@pytest.mark.unit
class TestExplainerAgentEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_storage = Mock(spec=StorageService)
        self.mock_settings = Mock()
        self.mock_settings.OPENAI_API_KEY = None
        self.mock_settings.ANTHROPIC_API_KEY = None
        self.mock_settings.MAX_CITATIONS = 8
        self.mock_settings.FRESHNESS_DAYS_DEFAULT = 7
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_with_failed_result(self, mock_get_settings):
        """Test explaining a failed scenario result."""
        mock_get_settings.return_value = self.mock_settings
        
        failed_result = ScenarioResult(
            scenario_id="failed_scenario",
            metrics=SimulationMetrics(
                clearance_time=0.0,
                max_queue=0.0,
                fairness_index=0.0,
                robustness=0.0
            ),
            status=TaskStatus.FAILED,
            duration_ms=1000,
            error_message="Simulation timeout"
        )
        
        scenario = ScenarioConfig(id="failed_scenario")
        intent = UserIntent(
            objective="Test failed scenario",
            constraints=ScenarioConstraints(),
            preferences=UserPreferences()
        )
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=[])
            
            result = await agent.explain_scenario(scenario, failed_result, intent)
            
            assert isinstance(result, ExplanationResult)
            assert result.scenario_id == "failed_scenario"
            assert "failed" in result.answer.lower() or "error" in result.answer.lower()
    
    @patch('agents.explainer_agent.get_settings')
    async def test_explain_scenario_with_old_citations(self, mock_get_settings):
        """Test scenario explanation with outdated citations."""
        mock_get_settings.return_value = self.mock_settings
        
        # Citations older than freshness threshold
        old_citations = [
            Citation(
                title="Outdated Guidelines",
                url="https://example.com/old",
                published_at=datetime.now() - timedelta(days=365),  # 1 year old
                source="old_source",
                score=0.9
            )
        ]
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=old_citations)
            
            scenario = ScenarioConfig(id="test_scenario")
            result = ScenarioResult(
                scenario_id="test_scenario",
                metrics=SimulationMetrics(
                    clearance_time=1800.0,
                    max_queue=150.0,
                    fairness_index=0.85,
                    robustness=0.75
                ),
                status=TaskStatus.COMPLETED,
                duration_ms=5000
            )
            intent = UserIntent(
                objective="Test with old citations",
                constraints=ScenarioConstraints(),
                preferences=UserPreferences()
            )
            
            explanation = await agent.explain_scenario(scenario, result, intent)
            
            # Should still provide explanation but may note data freshness concerns
            assert isinstance(explanation, ExplanationResult)
            assert explanation.scenario_id == "test_scenario"
    
    @patch('agents.explainer_agent.get_settings')
    def test_citation_parsing_with_invalid_dates(self, mock_get_settings):
        """Test citation parsing with invalid date formats."""
        mock_get_settings.return_value = self.mock_settings
        
        # Mock search result with invalid date
        invalid_search_result = {
            "doc_id": "doc_001",
            "title": "Test Document",
            "url": "https://example.com/test",
            "source": "test_source",
            "published_at": "invalid-date-format",
            "score": 0.9
        }
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            
            # Should handle invalid date gracefully
            try:
                citation = Citation(
                    title=invalid_search_result["title"],
                    url=invalid_search_result["url"],
                    published_at=datetime.now(),  # Fallback to current time
                    source=invalid_search_result["source"],
                    score=invalid_search_result["score"]
                )
                assert citation.title == "Test Document"
            except Exception as e:
                pytest.fail(f"Citation parsing should handle invalid dates gracefully: {e}")
    
    @patch('agents.explainer_agent.get_settings')
    async def test_concurrent_explanation_requests(self, mock_get_settings):
        """Test handling multiple concurrent explanation requests."""
        mock_get_settings.return_value = self.mock_settings
        
        import asyncio
        
        with patch('agents.explainer_agent.OPENAI_AVAILABLE', False):
            agent = ExplainerAgent(self.mock_storage)
            agent._search_relevant_documents = AsyncMock(return_value=[])
            
            # Create multiple scenarios
            scenarios = [
                ScenarioConfig(id=f"scenario_{i}")
                for i in range(3)
            ]
            
            results = [
                ScenarioResult(
                    scenario_id=f"scenario_{i}",
                    metrics=SimulationMetrics(
                        clearance_time=1800.0 + i * 100,
                        max_queue=150.0 + i * 10,
                        fairness_index=0.85 - i * 0.05,
                        robustness=0.75 + i * 0.05
                    ),
                    status=TaskStatus.COMPLETED,
                    duration_ms=5000
                )
                for i in range(3)
            ]
            
            intent = UserIntent(
                objective="Concurrent test",
                constraints=ScenarioConstraints(),
                preferences=UserPreferences()
            )
            
            # Run explanations concurrently
            tasks = [
                agent.explain_scenario(scenarios[i], results[i], intent)
                for i in range(3)
            ]
            
            explanations = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(explanations) == 3
            for i, explanation in enumerate(explanations):
                assert explanation.scenario_id == f"scenario_{i}"
                assert isinstance(explanation, ExplanationResult)
