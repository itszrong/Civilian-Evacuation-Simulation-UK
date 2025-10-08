/**
 * Lightweight Borough Detail View
 * Dynamically generates UI based on available data
 */

import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { notificationStore } from './govuk/Notification';
import { BoroughContextService } from '../services/boroughContextService';

interface Run {
  run_id: string;
  status: string;
  created_at: string;
  scenario_count: number;
  city: string;
  metrics?: {
    clearance_time: number;
    fairness_index: number;
    robustness: number;
  };
}

const BoroughDetail: React.FC = () => {
  const { boroughName } = useParams<{ boroughName: string }>();
  const navigate = useNavigate();
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const displayName = boroughName
    ?.split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ') || '';

  useEffect(() => {
    if (boroughName) fetchData();
  }, [boroughName]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log(`🚀 Fast-fetching data for borough: ${boroughName}`);
      
      // Use direct backend URL for debugging
      const apiUrl = API_CONFIG.baseUrl.includes('localhost:3000') || API_CONFIG.baseUrl === '/api' 
        ? 'http://localhost:8000/api/runs' 
        : `${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.list}`;
      
      const response = await fetch(apiUrl);
      if (!response.ok) throw new Error('Failed to fetch data');

      const data = await response.json();
      const allRuns = data.runs || [];
      console.log(`📊 Total runs: ${allRuns.length}`);

      // OPTIMIZATION 1: Filter and sort first, before any async operations
      const matchingCompletedRuns = allRuns
        .filter((run: any) => {
          const runCity = (run.city || '').toLowerCase().replace(/\s+/g, '-');
          return runCity === boroughName?.toLowerCase() && run.status === 'completed';
        })
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 10); // Take top 10 to check, we'll filter to 5 with visualizations

      console.log(`🎯 Found ${matchingCompletedRuns.length} completed runs for ${boroughName}`);

      if (matchingCompletedRuns.length === 0) {
        setRuns([]);
        return;
      }

      // OPTIMIZATION 2: Check visualizations in parallel, stop when we have 5
      const boroughRuns = [];
      const batchSize = 5;
      
      for (let i = 0; i < matchingCompletedRuns.length && boroughRuns.length < 5; i += batchSize) {
        const batch = matchingCompletedRuns.slice(i, i + batchSize);
        
        // Fetch scenarios for batch in parallel
        const batchResults = await Promise.all(
          batch.map(async (run: any) => {
            try {
              const scenariosResponse = await fetch(`${API_CONFIG.baseUrl}/api/runs/${run.run_id}/scenarios`);
              if (scenariosResponse.ok) {
                const scenariosData = await scenariosResponse.json();
                
                const hasVisualization = scenariosData.scenarios?.some((scenario: any) => {
                  const hasSimData = scenario.results?.simulation_data || scenario.simulation_data;
                  return hasSimData?.interactive_map_html || hasSimData?.visualisation_image;
                });
                
                if (hasVisualization) {
                  return run;
                }
              }
            } catch (err) {
              console.warn(`⚠️ Error checking ${run.run_id}:`, err);
            }
            return null;
          })
        );
        
        // Add valid runs from this batch
        boroughRuns.push(...batchResults.filter(Boolean));
        
        // Stop if we have enough
        if (boroughRuns.length >= 5) break;
      }
      
      // Limit to 5
      const finalRuns = boroughRuns.slice(0, 5);
      console.log(`✅ Found ${finalRuns.length} runs with visualizations`);

      // OPTIMIZATION 3: Fetch all details in parallel
      const enhancedRuns = await Promise.all(
        finalRuns.map(async (run: any) => {
          try {
            const detailUrl = API_CONFIG.baseUrl.includes('localhost:3000') || API_CONFIG.baseUrl === '/api' 
              ? `http://localhost:8000/api/runs/${run.run_id}` 
              : `${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.run(run.run_id)}`;
            
            const detailResponse = await fetch(detailUrl);
            if (detailResponse.ok) {
              const detail = await detailResponse.json();
              const firstScenario = detail.scenarios?.[0];
              const metrics = firstScenario?.metrics;
              
              return {
                ...run,
                scenario_count: detail.scenarios?.length || 0,
                metrics: metrics ? {
                  clearance_time: metrics.clearance_time || metrics.expected_clearance_time || 0,
                  fairness_index: metrics.fairness_index || 0,
                  robustness: metrics.robustness || 0
                } : null
              };
            }
          } catch (e) {
            console.warn(`❌ Error fetching details for run ${run.run_id}:`, e);
          }
          return run;
        })
      );

      console.log(`✅ Loaded ${enhancedRuns.length} runs with full details`);
      setRuns(enhancedRuns);
    } catch (err) {
      console.error('❌ Failed to fetch data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Generate borough-specific scenario intent
  const generateBoroughScenarioIntent = (locationSlug: string, locationName: string): string => {
    const boroughContext = BoroughContextService.getBoroughContext(locationSlug);
    
    if (!boroughContext) {
      return `Test comprehensive evacuation efficiency for ${locationName}`;
    }

    // Generate intent based on borough characteristics
    let intent = `Test evacuation efficiency for ${boroughContext.name}`;
    
    // Add risk-specific elements
    if (boroughContext.riskProfile.floodRisk === 'high') {
      intent += ' during flood conditions';
    }
    if (boroughContext.riskProfile.terroristThreat === 'high') {
      intent += ' with security considerations';
    }
    
    // Add infrastructure considerations
    if (boroughContext.infrastructure.transportHubs.length > 2) {
      intent += ` focusing on transport hub coordination`;
    }
    
    // Add population considerations
    if (boroughContext.demographics.touristAreas.length > 0) {
      intent += ' accounting for tourist populations';
    }
    if (boroughContext.demographics.density > 12000) {
      intent += ' in high-density areas';
    }
    
    // Add asset protection
    if (boroughContext.keyAssets.length > 0) {
      intent += ` while protecting ${boroughContext.keyAssets[0]}`;
    }
    
    return intent;
  };

  const startSimulation = async () => {
    if (!boroughName || isRunning) return;
    
    setIsRunning(true);
    try {
      const cityParam = boroughName.replace(/-/g, ' ');
      const boroughContext = BoroughContextService.getBoroughContext(boroughName);
      
      // Generate borough-specific scenario intent
      const scenarioIntent = generateBoroughScenarioIntent(boroughName, displayName);
      
      console.log(`🤖 Generating AI scenario for ${displayName}: "${scenarioIntent}"`);
      
      // Step 1: Generate AI scenario specification
      const scenarioGenPayload = {
        scenario_intent: scenarioIntent,
        city_context: `${displayName}, London`,
        use_framework: true
      };
      
      const scenarioResponse = await fetch(`${API_CONFIG.baseUrl}/api/agentic/scenarios/generate`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(scenarioGenPayload)
      });
      
      if (!scenarioResponse.ok) {
        throw new Error('Failed to generate AI scenario specification');
      }
      
      const scenarioResult = await scenarioResponse.json();
      console.log(`🎯 AI generated scenario:`, scenarioResult.scenario_specification?.name || 'Custom scenario');
      
      // Step 2: Run simulation with the AI-generated scenario context
      const response = await fetch(
        `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(cityParam)}?force_refresh=true&create_complete=true&ai_scenario=${encodeURIComponent(scenarioIntent)}`
      );
      
      if (response.ok) {
        const result = await response.json();
        
        console.log(`✅ AI scenario simulation completed successfully for ${displayName}!`);
        
        // Store AI scenario info in localStorage for the results page
        const aiScenarioInfo = {
          intent: scenarioIntent,
          generated_scenario: scenarioResult.scenario_specification?.name || 'Custom scenario',
          description: scenarioResult.scenario_specification?.description || '',
          borough: displayName,
          timestamp: new Date().toISOString(),
          framework_compliant: scenarioResult.framework_info?.framework_compliant || false,
          template_used: scenarioResult.framework_info?.template_used || 'custom'
        };
        
        localStorage.setItem(`ai_scenario_${result.run_id}`, JSON.stringify(aiScenarioInfo));
        
        notificationStore.show({
          title: 'AI Simulation Complete',
          message: `AI scenario: "${scenarioResult.scenario_specification?.name || 'Custom scenario'}" - View results to see how it compares to standard scenarios`,
          type: 'success'
        });
        
        if (result.run_id) {
          navigate(`/results/${result.run_id}?ai_generated=true`);
        } else {
          window.location.reload();
        }
      } else {
        const errorText = await response.text();
        console.error(`❌ API Error: ${response.status} ${response.statusText}`, errorText);
        throw new Error(`Failed to run simulation: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      setError('Failed to start AI simulation');
      notificationStore.show({
        title: 'Error',
        message: 'Failed to start AI simulation',
        type: 'error'
      });
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, string> = {
      completed: 'govuk-tag--green',
      in_progress: 'govuk-tag--blue',
      running: 'govuk-tag--blue',
      failed: 'govuk-tag--red'
    };
    const className = statusMap[status.toLowerCase()] || 'govuk-tag--grey';
    return <span className={`govuk-tag ${className}`}>{status}</span>;
  };

  const formatMetric = (value: number | undefined, suffix: string = '', multiplier: number = 1) => {
    return value ? `${Math.round(value * multiplier)}${suffix}` : '-';
  };

  // Dynamic data analysis
  const stats = {
    total: runs.length,
    completed: runs.filter(r => r.status === 'completed').length,
    active: runs.filter(r => r.status === 'in_progress' || r.status === 'running').length,
    avgClearance: runs.filter(r => r.metrics?.clearance_time).length > 0 
      ? runs.reduce((sum, r) => sum + (r.metrics?.clearance_time || 0), 0) / runs.filter(r => r.metrics?.clearance_time).length
      : 0
  };

  if (loading) {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          <Link to="/boroughs" className="govuk-back-link">Back</Link>
          <h1 className={GOVUK_CLASSES.heading.xl}>{displayName}</h1>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          <Link to="/boroughs" className="govuk-back-link">Back</Link>
          <h1 className={GOVUK_CLASSES.heading.xl}>{displayName}</h1>
          <div className="govuk-error-summary">
            <h2 className="govuk-error-summary__title">Error</h2>
            <div className="govuk-error-summary__body">
              <p>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>
        <Link to="/boroughs" className="govuk-back-link">Back</Link>
        
        <h1 className={GOVUK_CLASSES.heading.xl}>{displayName}</h1>
        
        {/* Dynamic Stats - only show if we have data */}
        {stats.total > 0 && (
          <div className={`${GOVUK_CLASSES.gridRow} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
            <div className={GOVUK_CLASSES.gridColumn.oneThird}>
              <div className={GOVUK_CLASSES.insetText}>
                <h3 className={GOVUK_CLASSES.heading.m}>{stats.total}</h3>
                <p className={GOVUK_CLASSES.body.s}>Total Runs</p>
              </div>
            </div>
            <div className={GOVUK_CLASSES.gridColumn.oneThird}>
              <div className={GOVUK_CLASSES.insetText}>
                <h3 className={GOVUK_CLASSES.heading.m}>{stats.completed}</h3>
                <p className={GOVUK_CLASSES.body.s}>Completed</p>
              </div>
            </div>
            {stats.active > 0 && (
              <div className={GOVUK_CLASSES.gridColumn.oneThird}>
                <div className={GOVUK_CLASSES.insetText}>
                  <h3 className={GOVUK_CLASSES.heading.m}>{stats.active}</h3>
                  <p className={GOVUK_CLASSES.body.s}>Active</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Average clearance time - separate row if we have the data */}
        {stats.avgClearance > 0 && (
          <div className={`${GOVUK_CLASSES.gridRow} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
            <div className={GOVUK_CLASSES.gridColumn.oneThird}>
              <div className={GOVUK_CLASSES.insetText}>
                <h3 className={GOVUK_CLASSES.heading.m}>{Math.round(stats.avgClearance)} min</h3>
                <p className={GOVUK_CLASSES.body.s}>Average Clearance Time</p>
              </div>
            </div>
          </div>
        )}

        {/* Start New Simulation */}
        <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
          <div className="govuk-button-group">
            <Link
              to={`/borough/${boroughName}/plan`}
              className="govuk-button"
            >
              Smart Planning
            </Link>
            
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <button
                className={`govuk-button govuk-button--secondary ${isRunning ? 'govuk-button--disabled' : ''}`}
                onClick={startSimulation}
                disabled={isRunning}
                title={`Run AI-generated simulation specific to ${displayName}`}
              >
                {isRunning ? 'Generating AI Scenario...' : 'AI Simulation'}
              </button>
              <span 
                className="govuk-tag govuk-tag--green" 
                style={{ 
                  position: 'absolute', 
                  top: '-8px', 
                  right: '-8px', 
                  fontSize: '10px',
                  padding: '2px 4px'
                }}
              >
                AUTO
              </span>
            </div>
          </div>
        </div>

        {/* Recent Runs - only show if we have data */}
        {runs.length > 0 ? (
          <div>
            <h2 className={GOVUK_CLASSES.heading.m}>Recent Simulations</h2>
            <table className="govuk-table">
              <thead className="govuk-table__head">
                <tr className="govuk-table__row">
                  <th scope="col" className="govuk-table__header">Run ID</th>
                  <th scope="col" className="govuk-table__header">Status</th>
                  <th scope="col" className="govuk-table__header">Date</th>
                  {runs.some(r => r.scenario_count > 0) && (
                    <th scope="col" className="govuk-table__header">Scenarios</th>
                  )}
                  {runs.some(r => r.metrics?.clearance_time) && (
                    <th scope="col" className="govuk-table__header">Clearance</th>
                  )}
                  {runs.some(r => r.metrics?.fairness_index) && (
                    <th scope="col" className="govuk-table__header">Fairness</th>
                  )}
                  {runs.some(r => r.metrics?.robustness) && (
                    <th scope="col" className="govuk-table__header">Robustness</th>
                  )}
                  <th scope="col" className="govuk-table__header">Actions</th>
                </tr>
              </thead>
              <tbody className="govuk-table__body">
                {runs.map(run => (
                  <tr key={run.run_id} className="govuk-table__row">
                    <td className="govuk-table__cell">
                      <code className="govuk-!-font-family-monospace govuk-!-font-size-14">
                        {run.run_id.substring(0, 8)}...
                      </code>
                    </td>
                    <td className="govuk-table__cell">{getStatusBadge(run.status)}</td>
                    <td className="govuk-table__cell">
                      {new Date(run.created_at).toLocaleDateString('en-GB')}
                    </td>
                    {runs.some(r => r.scenario_count > 0) && (
                      <td className="govuk-table__cell">{run.scenario_count || '-'}</td>
                    )}
                    {runs.some(r => r.metrics?.clearance_time) && (
                      <td className="govuk-table__cell">
                        {formatMetric(run.metrics?.clearance_time, ' min')}
                      </td>
                    )}
                    {runs.some(r => r.metrics?.fairness_index) && (
                      <td className="govuk-table__cell">
                        {formatMetric(run.metrics?.fairness_index, '%', 100)}
                      </td>
                    )}
                    {runs.some(r => r.metrics?.robustness) && (
                      <td className="govuk-table__cell">
                        {formatMetric(run.metrics?.robustness, '%', 100)}
                      </td>
                    )}
                    <td className="govuk-table__cell">
                      <Link
                        to={`/results/${run.run_id}?city=${boroughName?.replace(/-/g, ' ')}`}
                        className="govuk-link"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className={GOVUK_CLASSES.insetText}>
            <p>No simulations found for {displayName}.</p>
            <p>Use "Smart Planning" for guided AI planning or "AI Simulation" for automatic borough-specific scenarios.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BoroughDetail;
