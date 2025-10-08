"""
Explainer Agent for London Evacuation Planning Tool.

This agent provides RAG-based explanations for evacuation scenarios with citations
from allow-listed sources, implementing abstain functionality when evidence is insufficient.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

from models.schemas import (
    ScenarioConfig, ScenarioResult, ExplanationResult, Citation, 
    SourceTier, UserIntent
)
from services.storage_service import StorageService
from core.config import get_settings

logger = structlog.get_logger(__name__)


class ExplainerAgent:
    """Agent responsible for generating RAG-based explanations with citations."""

    def __init__(self, storage_service: StorageService):
        self.settings = get_settings()
        self.storage = storage_service
        self._openai_client = None
        self._anthropic_client = None
        
        # Initialize AI clients if available
        if OPENAI_AVAILABLE and self.settings.OPENAI_API_KEY:
            self._openai_client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
        
        if ANTHROPIC_AVAILABLE and self.settings.ANTHROPIC_API_KEY:
            self._anthropic_client = anthropic.Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)

    async def explain_scenario(self, scenario_config: ScenarioConfig,
                             scenario_result: ScenarioResult,
                             intent: UserIntent) -> ExplanationResult:
        """Generate explanation for the best evacuation scenario."""
        logger.info("Explainer agent generating explanation", 
                   scenario_id=scenario_config.id)

        try:
            # Retrieve relevant documents from allow-listed sources
            relevant_docs = await self._retrieve_relevant_documents(
                scenario_config, intent
            )

            # Check if we have sufficient evidence
            if not relevant_docs or len(relevant_docs) == 0:
                logger.warning("No relevant documents found for explanation", 
                             scenario_id=scenario_config.id)
                return self._create_abstain_response(scenario_config.id, relevant_docs)

            # Filter documents by freshness
            fresh_docs = self._filter_by_freshness(relevant_docs, intent.freshness_days)
            
            if not fresh_docs:
                logger.warning("No fresh documents found for explanation", 
                             scenario_id=scenario_config.id,
                             freshness_days=intent.freshness_days)
                return self._create_abstain_response(scenario_config.id, relevant_docs)

            # Generate explanation using RAG
            explanation = await self._generate_rag_explanation(
                scenario_config, scenario_result, fresh_docs, intent
            )

            # Create citations from the documents
            citations = self._create_citations(fresh_docs)

            result = ExplanationResult(
                scenario_id=scenario_config.id,
                answer=explanation,
                citations=citations,
                mode="retrieval_only",
                abstained=False
            )

            logger.info("Explainer agent completed explanation generation",
                       scenario_id=scenario_config.id,
                       citations_count=len(citations),
                       abstained=False)

            return result

        except Exception as e:
            logger.error("Explanation generation failed", 
                        scenario_id=scenario_config.id, 
                        error=str(e))
            
            # Return abstain response on error
            return self._create_abstain_response(scenario_config.id, [])

    async def _retrieve_relevant_documents(self, scenario: ScenarioConfig, 
                                         intent: UserIntent) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from storage based on scenario content."""
        
        # Build search queries based on scenario elements
        search_queries = self._build_search_queries(scenario, intent)
        
        all_documents = []
        
        for query in search_queries:
            try:
                # Search each allowed tier
                for tier in intent.tiers:
                    documents = await self.storage.search_documents(
                        query=query,
                        tier=tier.value,
                        max_age_days=intent.freshness_days,
                        limit=self.settings.MAX_CITATIONS
                    )
                    all_documents.extend(documents)
                    
            except Exception as e:
                logger.warning("Document search failed", 
                             query=query, 
                             error=str(e))
                continue

        # Remove duplicates and sort by relevance
        unique_docs = self._deduplicate_documents(all_documents)
        sorted_docs = sorted(unique_docs, key=lambda x: x.get('score', 0), reverse=True)
        
        return sorted_docs[:self.settings.MAX_CITATIONS]

    def _build_search_queries(self, scenario: ScenarioConfig, 
                            intent: UserIntent) -> List[str]:
        """Build search queries based on scenario and intent."""
        queries = []
        
        # Base query from objective
        queries.append(intent.objective.replace('_', ' '))
        
        # Queries for specific scenario elements
        for closure in scenario.closures:
            if closure.area:
                queries.append(f"{closure.area} emergency evacuation")
                queries.append(f"{closure.area} road closure protocol")
        
        # Queries for infrastructure elements
        if any(change.edge_selector == "is_bridge==true" for change in scenario.capacity_changes):
            queries.append("Thames bridge emergency closure")
            queries.append("London bridge evacuation protocol")
        
        # Queries for protected POIs
        for poi in intent.constraints.must_protect_pois:
            queries.append(f"{poi} emergency access")
            queries.append(f"{poi} evacuation protocol")
        
        # General evacuation queries
        queries.extend([
            "London emergency evacuation planning",
            "TfL emergency transport protocol",
            "London emergency response guidelines",
            "evacuation route optimization"
        ])
        
        return queries

    def _deduplicate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents based on doc_id."""
        seen_ids = set()
        unique_docs = []
        
        for doc in documents:
            doc_id = doc.get('doc_id')
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)
        
        return unique_docs

    def _filter_by_freshness(self, documents: List[Dict[str, Any]], 
                           freshness_days: int) -> List[Dict[str, Any]]:
        """Filter documents by freshness requirement."""
        cutoff_date = datetime.utcnow() - timedelta(days=freshness_days)
        
        fresh_docs = []
        for doc in documents:
            try:
                published_str = doc.get('published_at')
                if published_str:
                    if isinstance(published_str, str):
                        published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    else:
                        published_date = published_str
                    
                    if published_date >= cutoff_date:
                        fresh_docs.append(doc)
            except Exception:
                # If we can't parse the date, exclude the document
                continue
        
        return fresh_docs

    async def _generate_rag_explanation(self, scenario: ScenarioConfig,
                                      result: ScenarioResult,
                                      documents: List[Dict[str, Any]],
                                      intent: UserIntent) -> str:
        """Generate explanation using RAG approach."""
        
        # Create context from retrieved documents
        context = self._build_document_context(documents)
        
        # Create prompt for explanation
        prompt = self._build_explanation_prompt(scenario, result, context, intent)
        
        # Generate explanation using available AI service
        if self._openai_client:
            return await self._generate_with_openai(prompt)
        elif self._anthropic_client:
            return await self._generate_with_anthropic(prompt)
        else:
            # Fallback to template-based explanation
            return self._generate_template_explanation(scenario, result, documents)

    def _build_document_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents."""
        context_parts = []
        
        for i, doc in enumerate(documents[:5]):  # Use top 5 documents
            title = doc.get('title', 'Untitled')
            source = doc.get('source', 'Unknown')
            # Note: We don't include full text to avoid prompt injection
            context_parts.append(f"Document {i+1}: {title} (Source: {source})")
        
        return "\n".join(context_parts)

    def _build_explanation_prompt(self, scenario: ScenarioConfig,
                                result: ScenarioResult,
                                context: str,
                                intent: UserIntent) -> str:
        """Build prompt for explanation generation."""
        
        prompt = f"""You are an expert in London emergency evacuation planning. Based on the provided context from official sources, explain why the following evacuation scenario is recommended.

Scenario: {scenario.id}
Objective: {intent.objective}

Scenario Details:
- Closures: {len(scenario.closures)} area closures
- Capacity changes: {len(scenario.capacity_changes)} modifications
- Protected corridors: {len(scenario.protected_corridors)} protections

Results:
- Clearance time: {result.metrics.clearance_time:.1f} minutes
- Fairness index: {result.metrics.fairness_index:.2f}
- Robustness: {result.metrics.robustness:.2f}

Context from official sources:
{context}

Provide a concise explanation (2-3 sentences) of why this scenario is effective, referencing the official guidance where relevant. Focus on the practical benefits and alignment with established protocols.

Explanation:"""

        return prompt

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate explanation using OpenAI API."""
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in emergency evacuation planning. Provide concise, factual explanations based only on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("OpenAI explanation generation failed", error=str(e))
            raise

    async def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate explanation using Anthropic API."""
        try:
            response = self._anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error("Anthropic explanation generation failed", error=str(e))
            raise

    def _generate_template_explanation(self, scenario: ScenarioConfig,
                                     result: ScenarioResult,
                                     documents: List[Dict[str, Any]]) -> str:
        """Generate template-based explanation when AI services unavailable."""
        
        explanation_parts = []
        
        # Base explanation
        explanation_parts.append(f"The {scenario.id} scenario achieves effective evacuation")
        
        # Add specific benefits based on metrics
        if result.metrics.clearance_time < 120:  # Less than 2 hours
            explanation_parts.append("with rapid clearance time")
        
        if result.metrics.fairness_index > 0.7:
            explanation_parts.append("while maintaining good fairness across population groups")
        
        if result.metrics.robustness > 0.6:
            explanation_parts.append("and providing robust performance under various conditions")
        
        # Add scenario-specific elements
        if scenario.protected_corridors:
            explanation_parts.append("by protecting critical access routes")
        
        if scenario.staged_egress:
            explanation_parts.append("through coordinated staged evacuation")
        
        # Reference to guidance
        if documents:
            source_names = [doc.get('source', 'official sources') for doc in documents[:2]]
            explanation_parts.append(f"following guidance from {' and '.join(set(source_names))}")
        
        explanation = " ".join(explanation_parts) + "."
        
        # Ensure proper sentence structure
        explanation = explanation.replace(" and .", ".").replace(" .", ".")
        
        return explanation

    def _create_citations(self, documents: List[Dict[str, Any]]) -> List[Citation]:
        """Create citation objects from documents."""
        citations = []
        
        for doc in documents:
            try:
                published_at_str = doc.get('published_at')
                if isinstance(published_at_str, str):
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                else:
                    published_at = published_at_str
                
                citation = Citation(
                    title=doc.get('title', 'Untitled'),
                    url=doc.get('url', ''),
                    published_at=published_at,
                    source=doc.get('source', 'Unknown'),
                    score=doc.get('score', 0.0)
                )
                citations.append(citation)
                
            except Exception as e:
                logger.warning("Failed to create citation", 
                             doc_id=doc.get('doc_id'), 
                             error=str(e))
                continue
        
        return citations

    def _create_abstain_response(self, scenario_id: str, 
                               available_docs: List[Dict[str, Any]]) -> ExplanationResult:
        """Create an abstain response when insufficient evidence is available."""
        
        # Create citations for available documents even when abstaining
        citations = self._create_citations(available_docs[:3])  # Show some available sources
        
        abstain_message = (
            "Insufficient fresh evidence available from allow-listed sources to provide "
            "a confident recommendation. Please review the available sources manually or "
            "consider expanding the freshness window."
        )
        
        return ExplanationResult(
            scenario_id=scenario_id,
            answer=abstain_message,
            citations=citations,
            mode="retrieval_only",
            abstained=True
        )
