"""
DSPy Lightweight Agents Microservice
Scalable agent framework with goldens + evaluations for evacuation analysis
"""

import dspy
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import structlog
from datetime import datetime, timezone
import json
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = structlog.get_logger(__name__)


class EvacuationContext(BaseModel):
    """Context for evacuation analysis."""
    city: str
    population: int
    news_articles: List[Dict[str, Any]] = []
    simulation_results: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnalysisResult(BaseModel):
    """Result from agent analysis."""
    agent_name: str
    analysis: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_insights: List[str]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreatAnalyzer(dspy.Signature):
    """Analyze news for potential evacuation threats."""

    news_summary = dspy.InputField(desc="Summary of recent news articles")
    city = dspy.InputField(desc="City being analyzed")

    threat_level = dspy.OutputField(desc="Threat level: low, medium, high, critical")
    analysis = dspy.OutputField(desc="Detailed threat analysis")
    key_factors = dspy.OutputField(desc="Key threat factors identified")


class RouteOptimizer(dspy.Signature):
    """Optimize evacuation routes based on simulation data."""

    simulation_data = dspy.InputField(desc="Evacuation simulation results")
    constraints = dspy.InputField(desc="Constraints and requirements")

    optimal_strategy = dspy.OutputField(desc="Recommended evacuation strategy")
    route_recommendations = dspy.OutputField(desc="Specific route recommendations")
    estimated_time = dspy.OutputField(desc="Estimated evacuation time")


class DecisionMemoGenerator(dspy.Signature):
    """Generate executive decision memo for government officials."""

    context = dspy.InputField(desc="Full evacuation context and analysis")
    priority = dspy.InputField(desc="Priority level of the situation")

    executive_summary = dspy.OutputField(desc="Executive summary for decision makers")
    action_items = dspy.OutputField(desc="Recommended immediate actions")
    risk_assessment = dspy.OutputField(desc="Risk assessment and mitigation")


class DSPyAgentService:
    """Service managing DSPy agents for evacuation analysis."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        # Updated to use new DSPy 2.5+ API
        import os

        # Check for API keys
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("No API keys found - DSPy agents will not work")
            self.lm = None
        else:
            # Use new dspy.LM() API
            try:
                if os.getenv("OPENAI_API_KEY"):
                    self.lm = dspy.LM(
                        model=f'openai/{model_name}',
                        api_key=os.getenv("OPENAI_API_KEY")
                    )
                elif os.getenv("ANTHROPIC_API_KEY"):
                    self.lm = dspy.LM(
                        model='anthropic/claude-3-5-sonnet-20241022',
                        api_key=os.getenv("ANTHROPIC_API_KEY")
                    )

                dspy.configure(lm=self.lm)
                logger.info("DSPy configured with LM", model=model_name)
            except Exception as e:
                logger.error(f"Failed to initialize DSPy LM: {e}")
                self.lm = None

        self.threat_analyzer = dspy.ChainOfThought(ThreatAnalyzer)
        self.route_optimizer = dspy.ChainOfThought(RouteOptimizer)
        self.memo_generator = dspy.ChainOfThought(DecisionMemoGenerator)

        self.goldens_path = Path("data/goldens")
        self.evals_path = Path("data/evals")
        self.goldens_path.mkdir(parents=True, exist_ok=True)
        self.evals_path.mkdir(parents=True, exist_ok=True)

        logger.info("DSPy agent service initialized", model=model_name, has_lm=self.lm is not None)

    async def analyze_threat(self, context: EvacuationContext) -> AnalysisResult:
        """Analyze threat level from news context."""
        logger.info("Running threat analysis", city=context.city)

        news_summary = "\n".join([
            f"- {article.get('title', '')}: {article.get('summary', '')[:100]}"
            for article in context.news_articles[:10]
        ])

        try:
            result = self.threat_analyzer(
                news_summary=news_summary,
                city=context.city
            )

            key_factors = [f.strip() for f in result.key_factors.split('\n') if f.strip()]

            analysis_result = AnalysisResult(
                agent_name="ThreatAnalyzer",
                analysis=result.analysis,
                confidence=0.85,
                key_insights=key_factors[:5],
                recommendations=[
                    f"Threat level: {result.threat_level}",
                    "Monitor situation continuously",
                    "Prepare evacuation protocols"
                ]
            )

            logger.info("Threat analysis complete", threat_level=result.threat_level)
            return analysis_result

        except Exception as e:
            logger.error("Threat analysis failed", error=str(e))
            return AnalysisResult(
                agent_name="ThreatAnalyzer",
                analysis="Analysis failed",
                confidence=0.0,
                key_insights=[],
                recommendations=[]
            )

    async def optimize_routes(self, context: EvacuationContext) -> AnalysisResult:
        """Optimize evacuation routes based on simulation."""
        logger.info("Running route optimization", city=context.city)

        if not context.simulation_results:
            return AnalysisResult(
                agent_name="RouteOptimizer",
                analysis="No simulation data available",
                confidence=0.0,
                key_insights=[],
                recommendations=[]
            )

        try:
            sim_summary = json.dumps(context.simulation_results, indent=2)[:500]

            result = self.route_optimizer(
                simulation_data=sim_summary,
                constraints=f"City: {context.city}, Population: {context.population}"
            )

            routes = [r.strip() for r in result.route_recommendations.split('\n') if r.strip()]

            analysis_result = AnalysisResult(
                agent_name="RouteOptimizer",
                analysis=result.optimal_strategy,
                confidence=0.90,
                key_insights=routes[:5],
                recommendations=[
                    f"Strategy: {result.optimal_strategy}",
                    f"Estimated time: {result.estimated_time}"
                ]
            )

            logger.info("Route optimization complete")
            return analysis_result

        except Exception as e:
            logger.error("Route optimization failed", error=str(e))
            return AnalysisResult(
                agent_name="RouteOptimizer",
                analysis="Optimization failed",
                confidence=0.0,
                key_insights=[],
                recommendations=[]
            )

    async def generate_memo(self, context: EvacuationContext, analyses: List[AnalysisResult]) -> AnalysisResult:
        """Generate executive decision memo."""
        logger.info("Generating decision memo", city=context.city)

        try:
            context_summary = {
                "city": context.city,
                "population": context.population,
                "analyses": [
                    {"agent": a.agent_name, "insights": a.key_insights}
                    for a in analyses
                ]
            }

            result = self.memo_generator(
                context=json.dumps(context_summary, indent=2),
                priority="HIGH"
            )

            actions = [a.strip() for a in result.action_items.split('\n') if a.strip()]

            memo_result = AnalysisResult(
                agent_name="DecisionMemoGenerator",
                analysis=result.executive_summary,
                confidence=0.88,
                key_insights=[result.risk_assessment],
                recommendations=actions[:5]
            )

            logger.info("Decision memo generated")
            return memo_result

        except Exception as e:
            logger.error("Memo generation failed", error=str(e))
            return AnalysisResult(
                agent_name="DecisionMemoGenerator",
                analysis="Memo generation failed",
                confidence=0.0,
                key_insights=[],
                recommendations=[]
            )

    def save_golden(self, golden_name: str, input_data: Dict[str, Any], expected_output: Dict[str, Any]):
        """Save a golden example for evaluation."""
        golden_file = self.goldens_path / f"{golden_name}.json"

        golden = {
            "name": golden_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": input_data,
            "expected_output": expected_output
        }

        with open(golden_file, 'w') as f:
            json.dump(golden, f, indent=2)

        logger.info(f"Saved golden: {golden_name}")

    def evaluate_agent(self, agent_name: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate agent performance against test cases."""
        logger.info(f"Evaluating agent: {agent_name}")

        results = {
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cases": len(test_cases),
            "passed": 0,
            "failed": 0,
            "avg_confidence": 0.0
        }

        eval_file = self.evals_path / f"{agent_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        with open(eval_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Evaluation complete for {agent_name}", results=results)
        return results


def create_sample_goldens():
    """Create sample golden test cases."""
    service = DSPyAgentService()

    service.save_golden(
        "threat_analysis_high",
        input_data={
            "news_summary": "Major fire in central London. Thousands evacuating. Smoke visible across city.",
            "city": "London"
        },
        expected_output={
            "threat_level": "high",
            "key_factors": ["Major fire", "Central location", "Large-scale evacuation needed"]
        }
    )

    service.save_golden(
        "route_optimization_basic",
        input_data={
            "simulation_data": {"num_routes": 10, "avg_time": 45, "success_rate": 0.95},
            "constraints": "City: London, Population: 500000"
        },
        expected_output={
            "optimal_strategy": "Use multiple routes to distribute load",
            "estimated_time": "45-60 minutes"
        }
    )

    logger.info("Sample goldens created")


if __name__ == "__main__":
    create_sample_goldens()
