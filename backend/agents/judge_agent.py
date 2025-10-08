"""
Judge Agent for London Evacuation Planning Tool.

This agent ranks scenarios based on user preferences and validates results
to ensure they meet requirements.
"""

from typing import List, Dict, Any, Optional
import structlog

from models.schemas import (
    ScenarioResult, UserPreferences, UserIntent, JudgeResult, 
    ScenarioRanking, TaskStatus
)

logger = structlog.get_logger(__name__)


class JudgeAgent:
    """Agent responsible for ranking and validating evacuation scenarios."""

    def __init__(self):
        pass

    async def rank_scenarios(self, results: List[ScenarioResult], 
                           preferences: UserPreferences,
                           intent: UserIntent) -> JudgeResult:
        """Rank scenarios based on user preferences and validate results."""
        logger.info("Judge agent starting scenario ranking", 
                   results_count=len(results))

        # Filter out failed scenarios
        valid_results = [r for r in results if r.status == TaskStatus.COMPLETED]
        
        if not valid_results:
            logger.warning("No valid scenarios to rank")
            return JudgeResult(
                ranking=[],
                weights=preferences,
                validation_passed=False,
                best_scenario_id=""
            )

        # Validate scenarios against requirements
        validated_results = []
        for result in valid_results:
            if await self._validate_result(result, intent):
                validated_results.append(result)
            else:
                logger.warning("Scenario failed validation requirements", 
                             scenario_id=result.scenario_id)

        if not validated_results:
            logger.warning("No scenarios passed validation requirements")
            return JudgeResult(
                ranking=[],
                weights=preferences,
                validation_passed=False,
                best_scenario_id=""
            )

        # Normalize metrics for fair comparison
        normalized_metrics = self._normalize_metrics(validated_results)

        # Calculate composite scores
        rankings = []
        for i, result in enumerate(validated_results):
            normalized = normalized_metrics[i]
            
            # Calculate weighted score
            score = (
                preferences.clearance_weight * (1.0 - normalized['clearance_time']) +
                preferences.fairness_weight * normalized['fairness_index'] +
                preferences.robustness_weight * normalized['robustness']
            )
            
            ranking = ScenarioRanking(
                scenario_id=result.scenario_id,
                score=score,
                rank=0  # Will be set after sorting
            )
            rankings.append(ranking)

        # Sort by score (descending)
        rankings.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1

        best_scenario_id = rankings[0].scenario_id if rankings else ""

        logger.info("Judge agent completed scenario ranking",
                   ranked_scenarios=len(rankings),
                   best_scenario=best_scenario_id,
                   best_score=rankings[0].score if rankings else 0.0)

        return JudgeResult(
            ranking=rankings,
            weights=preferences,
            validation_passed=True,
            best_scenario_id=best_scenario_id
        )

    async def _validate_result(self, result: ScenarioResult, intent: UserIntent) -> bool:
        """Validate that a scenario result meets requirements."""
        try:
            # Check basic metrics are reasonable
            metrics = result.metrics
            
            # Clearance time should be finite and positive
            if metrics.clearance_time <= 0 or metrics.clearance_time >= 999:
                logger.debug("Invalid clearance time", 
                           scenario_id=result.scenario_id,
                           clearance_time=metrics.clearance_time)
                return False

            # Fairness index should be between 0 and 1
            if not (0 <= metrics.fairness_index <= 1):
                logger.debug("Invalid fairness index", 
                           scenario_id=result.scenario_id,
                           fairness_index=metrics.fairness_index)
                return False

            # Robustness should be between 0 and 1
            if not (0 <= metrics.robustness <= 1):
                logger.debug("Invalid robustness", 
                           scenario_id=result.scenario_id,
                           robustness=metrics.robustness)
                return False

            # Max queue should be non-negative
            if metrics.max_queue < 0:
                logger.debug("Invalid max queue length", 
                           scenario_id=result.scenario_id,
                           max_queue=metrics.max_queue)
                return False

            # Check POI reachability requirements
            # This is a simplified check - in practice, would verify actual reachability
            if intent.constraints.must_protect_pois:
                # If clearance time is very high, POIs might not be reachable
                if metrics.clearance_time > intent.constraints.compute_budget_minutes * 60:
                    logger.debug("Scenario may have unreachable POIs", 
                               scenario_id=result.scenario_id,
                               clearance_time=metrics.clearance_time)
                    return False

            return True

        except Exception as e:
            logger.error("Result validation exception", 
                        scenario_id=result.scenario_id,
                        error=str(e))
            return False

    def _normalize_metrics(self, results: List[ScenarioResult]) -> List[Dict[str, float]]:
        """Normalize metrics across all results for fair comparison."""
        if not results:
            return []

        # Extract all metric values
        clearance_times = [r.metrics.clearance_time for r in results]
        fairness_indices = [r.metrics.fairness_index for r in results]
        robustness_values = [r.metrics.robustness for r in results]
        max_queues = [r.metrics.max_queue for r in results]

        # Calculate min/max for normalization
        min_clearance = min(clearance_times)
        max_clearance = max(clearance_times)
        min_fairness = min(fairness_indices)
        max_fairness = max(fairness_indices)
        min_robustness = min(robustness_values)
        max_robustness = max(robustness_values)
        min_queue = min(max_queues)
        max_queue = max(max_queues)

        normalized_results = []
        
        for result in results:
            # Normalize each metric to [0, 1]
            # For clearance time and max queue: lower is better, so we invert
            # For fairness and robustness: higher is better
            
            normalized = {}
            
            # Clearance time: normalize and invert (lower is better)
            if max_clearance > min_clearance:
                normalized['clearance_time'] = (result.metrics.clearance_time - min_clearance) / (max_clearance - min_clearance)
            else:
                normalized['clearance_time'] = 0.0

            # Fairness index: normalize (higher is better)
            if max_fairness > min_fairness:
                normalized['fairness_index'] = (result.metrics.fairness_index - min_fairness) / (max_fairness - min_fairness)
            else:
                normalized['fairness_index'] = 1.0

            # Robustness: normalize (higher is better)
            if max_robustness > min_robustness:
                normalized['robustness'] = (result.metrics.robustness - min_robustness) / (max_robustness - min_robustness)
            else:
                normalized['robustness'] = 1.0

            # Max queue: normalize and invert (lower is better)
            if max_queue > min_queue:
                normalized['max_queue'] = 1.0 - ((result.metrics.max_queue - min_queue) / (max_queue - min_queue))
            else:
                normalized['max_queue'] = 1.0

            normalized_results.append(normalized)

        return normalized_results

    async def validate_global_requirements(self, rankings: List[ScenarioRanking], 
                                         intent: UserIntent) -> bool:
        """Validate that ranked scenarios meet global requirements."""
        try:
            if not rankings:
                logger.warning("No scenarios to validate globally")
                return False

            # Check that we have at least one scenario
            if len(rankings) == 0:
                return False

            # Check that scores are reasonable
            best_score = rankings[0].score
            if best_score <= 0:
                logger.warning("Best scenario has non-positive score", score=best_score)
                return False

            # Check that rankings are properly ordered
            for i in range(1, len(rankings)):
                if rankings[i].score > rankings[i-1].score:
                    logger.warning("Rankings not properly ordered")
                    return False

            # Additional global validation could include:
            # - Pareto frontier analysis
            # - Sensitivity analysis
            # - Robustness checks across scenarios

            return True

        except Exception as e:
            logger.error("Global validation exception", error=str(e))
            return False

    async def request_replan(self, failed_results: List[ScenarioResult], 
                           intent: UserIntent) -> Dict[str, Any]:
        """Request replanning when validation fails globally."""
        logger.info("Judge agent requesting replan due to validation failures",
                   failed_count=len(failed_results))

        # Analyze failure patterns
        failure_analysis = self._analyze_failure_patterns(failed_results)

        # Generate replan request with specific guidance
        replan_request = {
            "reason": "global_validation_failure",
            "failed_scenarios": len(failed_results),
            "failure_patterns": failure_analysis,
            "recommendations": self._generate_replan_recommendations(failure_analysis, intent)
        }

        return replan_request

    def _analyze_failure_patterns(self, failed_results: List[ScenarioResult]) -> Dict[str, Any]:
        """Analyze patterns in failed results."""
        patterns = {
            "high_clearance_times": 0,
            "low_fairness": 0,
            "low_robustness": 0,
            "simulation_failures": 0,
            "validation_failures": 0
        }

        for result in failed_results:
            if result.status == TaskStatus.FAILED:
                patterns["simulation_failures"] += 1
            else:
                # Analyze metric patterns
                if result.metrics.clearance_time > 300:  # 5 hours
                    patterns["high_clearance_times"] += 1
                if result.metrics.fairness_index < 0.3:
                    patterns["low_fairness"] += 1
                if result.metrics.robustness < 0.3:
                    patterns["low_robustness"] += 1

        return patterns

    def _generate_replan_recommendations(self, failure_patterns: Dict[str, Any], 
                                       intent: UserIntent) -> List[str]:
        """Generate specific recommendations for replanning."""
        recommendations = []

        if failure_patterns["high_clearance_times"] > 0:
            recommendations.append("Focus on scenarios with enhanced capacity and fewer closures")

        if failure_patterns["low_fairness"] > 0:
            recommendations.append("Include more staged egress and equitable routing")

        if failure_patterns["low_robustness"] > 0:
            recommendations.append("Add protected corridors and redundant routes")

        if failure_patterns["simulation_failures"] > 0:
            recommendations.append("Generate simpler scenarios to avoid simulation failures")

        if not recommendations:
            recommendations.append("Generate alternative scenarios with different parameter ranges")

        return recommendations
