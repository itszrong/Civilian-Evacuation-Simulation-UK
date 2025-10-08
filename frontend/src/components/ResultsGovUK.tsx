/**
 * Results component for Civilian Evacuation Planning Tool
 * GOV.UK Design System implementation
 * Shows detailed results for completed evacuation planning runs with decision memo
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import CitySpecificVisualisation from './CitySpecificVisualisation';
import VisualizationThumbnail from './VisualizationThumbnail';
import SimulationQueue from './SimulationQueue';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { BarChart, MetricCard, ProgressRing, ComparisonTable } from './govuk/SimpleChart';
import { useResultsContextInjection } from '../hooks/useContextInjection';

// Scenario Visualization Map Component
interface ScenarioVisualizationMapProps {
  scenario: ScenarioResult;
  runResult: RunResult;
  city: string;
}

const ScenarioVisualizationMap: React.FC<ScenarioVisualizationMapProps> = ({ scenario, runResult, city }) => {
  const [mapData, setMapData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Stabilize scenario ID to prevent infinite re-renders
  const stableScenarioId = useMemo(() => scenario.scenario_id, [scenario.scenario_id]);
  const hasInteractiveMap = useMemo(() => !!scenario.simulation_data?.interactive_map_html, [scenario.simulation_data?.interactive_map_html]);

  const loadVisualizationData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      
      // PHASE 2 FIX: Single source of truth with hierarchical fallback
      let visualizationData = null;
      let dataSource = 'none';
        
        // Priority 1: Real simulation data from scenario (most specific)
        if (scenario.simulation_data?.interactive_map_html) {
          console.log('✅ Priority 1: Found real simulation data in scenario');
          visualizationData = scenario.simulation_data;
          dataSource = 'scenario_real';
        }
        
        // Priority 2: Load fresh real simulation data from API
        if (!visualizationData) {
          console.log('🔍 Priority 2: Loading fresh real simulation data from API...');
          try {
            const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(city)}?force_refresh=false`);
            if (response.ok) {
              const data = await response.json();
              console.log('✅ Loaded fresh simulation data:', {
                hasInteractiveMapHtml: !!data.interactive_map_html,
                hasRealMetrics: !!data.calculated_metrics,
                hasScenarios: !!data.scenarios,
                algorithmFeatures: data.algorithm_features
              });
              
              if (data.interactive_map_html && data.simulation_engine === 'real_evacuation_science') {
                visualizationData = data;
                dataSource = 'api_real';
                console.log('✅ Using real science simulation data from API');
              }
            } else {
              console.log('⚠️ API response not ok:', response.status);
            }
          } catch (err) {
            console.log('⚠️ Failed to load from API:', err);
          }
        }
        
        // Priority 3: Use cached real simulation data (if verified as real)
        if (!visualizationData && (window as any).citySimulationData?.simulation_engine === 'real_evacuation_science') {
          console.log('✅ Priority 3: Using cached real simulation data');
          visualizationData = (window as any).citySimulationData;
          dataSource = 'cached_real';
        }
        
        // Priority 4: Use existing data or show message - DON'T generate new simulations automatically
        if (!visualizationData) {
          console.log('ℹ️ No visualization data available - user should run a new simulation if needed');
          setError('No simulation data available. Please run a new simulation.');
        }
        
        setMapData(visualizationData);
        
        if (visualizationData) {
          console.log('🎉 Final visualization data loaded:', {
            source: dataSource,
            hasInteractiveMapHtml: !!visualizationData.interactive_map_html,
            isRealScience: visualizationData.simulation_engine === 'real_evacuation_science',
            hasRealMetrics: !!visualizationData.calculated_metrics
          });
        } else {
          console.error('❌ No real visualization data could be loaded');
          setError('No real simulation data available');
        }
        
      } catch (err) {
        console.error('❌ Failed to load visualization data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load visualization');
    } finally {
      setLoading(false);
    }
  }, [scenario.simulation_data, city, stableScenarioId, hasInteractiveMap]);

  useEffect(() => {
    loadVisualizationData();
  }, [loadVisualizationData]); // Re-run when the function changes

  if (loading) {
    return (
      <div className="govuk-inset-text">
        <h4>Loading Visualization</h4>
        <p>Loading interactive map with OSMnx graph, A* routes, and random walks...</p>
        <div style={{ 
          border: '2px solid #b1b4b6', 
          borderRadius: '4px',
          minHeight: '400px',
          backgroundColor: '#f8f8f8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column'
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '10px' }}>🔄</div>
          <p>Loading Folium map...</p>
          <p className="govuk-body-s">
            Scenario: {scenario.scenario_name || scenario.name}<br/>
            City: {city}<br/>
            Run ID: {runResult.run_id}
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="govuk-error-summary">
        <h4>Visualization Error</h4>
        <p>Failed to load visualization: {error}</p>
        <details className="govuk-details">
          <summary className="govuk-details__summary">
            <span className="govuk-details__summary-text">Debug Information</span>
          </summary>
          <div className="govuk-details__text">
            <p><strong>Scenario ID:</strong> {scenario.scenario_id}</p>
            <p><strong>Run ID:</strong> {runResult.run_id}</p>
            <p><strong>City:</strong> {city}</p>
            <p><strong>Available Data Sources:</strong></p>
            <ul>
              <li>scenario.simulation_data: {scenario.simulation_data ? 'Available' : 'None'}</li>
              <li>window.citySimulationData: {(window as any).citySimulationData ? 'Available' : 'None'}</li>
              <li>runResult._rawData: {runResult._rawData ? 'Available' : 'None'}</li>
            </ul>
          </div>
        </details>
      </div>
    );
  }

  if (mapData?.interactive_map_html || mapData?.mesa_routes_html) {
    return (
      <div>
        {/* A* Routes + Random Walks Visualization */}
        {mapData?.interactive_map_html && (
          <div style={{ marginBottom: '30px' }}>
            <h4 className="govuk-heading-s">A* Routes & Random Walks (Deterministic + Stochastic)</h4>
            <div style={{
              border: '2px solid #b1b4b6',
              borderRadius: '4px',
              minHeight: '600px',
              backgroundColor: '#fff'
            }}>
              <iframe
                srcDoc={mapData.interactive_map_html}
                style={{
                  width: '100%',
                  height: '600px',
                  border: 'none',
                  borderRadius: '4px'
                }}
                title={`${scenario.scenario_name || scenario.name} - A* Routes & Random Walks`}
              />
              <div className="govuk-body-s" style={{ padding: '10px', backgroundColor: '#f3f2f1', borderTop: '1px solid #b1b4b6' }}>
                <strong>Visualization 1 - Routing Algorithms:</strong> OSMnx street network, A* optimal routes (blue, on top), Biased random walks (red), Exit density heatmap (background)
                {mapData.astar_routes && (
                  <span> • {mapData.astar_routes.length} A* routes</span>
                )}
                {mapData.random_walks?.num_walks && (
                  <span> • {mapData.random_walks.num_walks} random walks</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Mesa Agent Routes Visualization */}
        {mapData?.mesa_routes_html && (
          <div style={{ marginBottom: '30px' }}>
            <h4 className="govuk-heading-s">Mesa Agent Simulation (Agent-Based with Queueing)</h4>
            <div style={{
              border: '2px solid #1d70b8',
              borderRadius: '4px',
              minHeight: '600px',
              backgroundColor: '#fff'
            }}>
              <iframe
                srcDoc={mapData.mesa_routes_html}
                style={{
                  width: '100%',
                  height: '600px',
                  border: 'none',
                  borderRadius: '4px'
                }}
                title={`${scenario.scenario_name || scenario.name} - Mesa Agent Routes`}
              />
              <div className="govuk-body-s" style={{ padding: '10px', backgroundColor: '#d4e5f2', borderTop: '1px solid #1d70b8' }}>
                <strong>Visualization 2 - Mesa Agent-Based Model:</strong> Individual agent evacuation paths with capacity constraints and queueing behavior
                {mapData.agent_count_total && (
                  <span> • {mapData.agent_count_total} total agents simulated ({mapData.agent_data?.length || 0} sample routes shown)</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Mesa Comprehensive Analytics */}
        {(mapData?.clearance_analysis_img || mapData?.density_analysis_img || mapData?.flow_analysis_img) && (
          <div style={{ marginBottom: '30px' }}>
            <h3 className="govuk-heading-m">Mesa Comprehensive Analytics</h3>

            {/* Clearance Time Analysis */}
            {mapData.clearance_analysis_img && (
              <div style={{ marginBottom: '30px' }}>
                <h4 className="govuk-heading-s">Clearance Time Analysis</h4>
                <div style={{
                  border: '2px solid #00703c',
                  borderRadius: '4px',
                  padding: '20px',
                  backgroundColor: '#fff'
                }}>
                  <img
                    src={`data:image/png;base64,${mapData.clearance_analysis_img}`}
                    alt="Clearance Time Analysis"
                    style={{ width: '100%', height: 'auto' }}
                  />
                  <div className="govuk-body-s" style={{ marginTop: '10px', color: '#505a5f' }}>
                    <strong>Analysis:</strong> Distribution of evacuation completion times, cumulative progress curve, start time vs completion time correlation, and comprehensive statistics including fairness index and robustness metrics.
                  </div>
                </div>
              </div>
            )}

            {/* Route Density Analysis */}
            {mapData.density_analysis_img && (
              <div style={{ marginBottom: '30px' }}>
                <h4 className="govuk-heading-s">Route Density & Bottleneck Analysis</h4>
                <div style={{
                  border: '2px solid #d4351c',
                  borderRadius: '4px',
                  padding: '20px',
                  backgroundColor: '#fff'
                }}>
                  <img
                    src={`data:image/png;base64,${mapData.density_analysis_img}`}
                    alt="Route Density Analysis"
                    style={{ width: '100%', height: 'auto' }}
                  />
                  <div className="govuk-body-s" style={{ marginTop: '10px', color: '#505a5f' }}>
                    <strong>Analysis:</strong> Edge usage distribution showing network congestion, and top 20 bottleneck edges ranked by criticality level (CRITICAL, HIGH, MODERATE, LOW).
                  </div>
                </div>
              </div>
            )}

            {/* Flow Analysis */}
            {mapData.flow_analysis_img && (
              <div style={{ marginBottom: '30px' }}>
                <h4 className="govuk-heading-s">Evacuation Flow Analysis</h4>
                <div style={{
                  border: '2px solid #4c2c92',
                  borderRadius: '4px',
                  padding: '20px',
                  backgroundColor: '#fff'
                }}>
                  <img
                    src={`data:image/png;base64,${mapData.flow_analysis_img}`}
                    alt="Flow Analysis"
                    style={{ width: '100%', height: 'auto' }}
                  />
                  <div className="govuk-body-s" style={{ marginTop: '10px', color: '#505a5f' }}>
                    <strong>Analysis:</strong> Temporal patterns of evacuation initiation (when agents start evacuating) and distribution of route lengths across the agent population.
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Data Source Info */}
        <div className="govuk-body-s" style={{ padding: '10px', backgroundColor: '#f3f2f1', borderRadius: '4px' }}>
          <strong>Data Source:</strong> {
            mapData === scenario.simulation_data ? 'Scenario-specific simulation' :
            mapData === (window as any).citySimulationData ? `City-wide simulation (${city})` :
            mapData === runResult._rawData ? 'Run raw data' : 'Unknown source'
          }
          {mapData.timestamp && (
            <span> • Generated: {new Date(mapData.timestamp).toLocaleString()}</span>
          )}
        </div>
      </div>
    );
  }

  if (mapData?.visualisation_image) {
    return (
      <div style={{ 
        border: '2px solid #b1b4b6', 
        borderRadius: '4px',
        padding: '20px',
        textAlign: 'center',
        backgroundColor: '#fff'
      }}>
        <img 
          src={`data:image/png;base64,${mapData.visualisation_image}`}
          alt={`${scenario.scenario_name || scenario.name} - Evacuation Routes`}
          style={{ 
            maxWidth: '100%', 
            height: 'auto',
            borderRadius: '4px'
          }}
        />
        <div className="govuk-body-s" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f3f2f1' }}>
          <strong>Static Visualization:</strong> Network analysis with evacuation routes and density mapping
        </div>
      </div>
    );
  }

  return (
    <div className="govuk-inset-text">
      <h4>Visualization Not Available</h4>
      <p>No interactive map or visualization data found for this scenario.</p>
      <div style={{ 
        border: '2px solid #b1b4b6', 
        borderRadius: '4px',
        minHeight: '400px',
        backgroundColor: '#f8f8f8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column'
      }}>
        <div style={{ fontSize: '1.2rem', marginBottom: '10px' }}>🗺️</div>
        <p>Interactive Folium map would appear here</p>
        <p className="govuk-body-s">
          Expected: OSMnx graph + A* routes + Random walks<br/>
          Scenario: {scenario.scenario_name || scenario.name}<br/>
          City: {city}<br/>
          Run ID: {runResult.run_id}
        </p>
        <button 
          className="govuk-button govuk-button--secondary govuk-!-margin-top-3"
          onClick={() => window.location.reload()}
        >
          Retry Loading
        </button>
      </div>
    </div>
  );
};

interface ScenarioResult {
  scenario_id: string;
  scenario_name?: string;
  name?: string;
  hazard_type?: string;
  evacuation_direction?: string;
  origin_location?: string;
  expected_clearance_time?: number;
  compliance_rate?: number;
  transport_disruption?: number;
  population_affected?: number;
  routes_calculated?: number;
  walks_simulated?: number;
  metrics: {
    clearance_time: number;
    max_queue: number;
    fairness_index: number;
    robustness: number;
    total_evacuated?: number;
    evacuation_efficiency?: number;
    [key: string]: any; // Allow for dynamic metrics
  };
  status: string;
  rank?: number;
  score?: number;
  description?: string;
  duration_ms?: number;
  simulation_data?: {
    interactive_map_html?: string;
    visualisation_image?: string;
    astar_routes?: any[];
    random_walks?: any;
    network_graph?: any;
  };
}

interface RunResult {
  run_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
  scenario_count: number;
  best_scenario_id?: string;
  city?: string;
  scenarios: ScenarioResult[];
  results?: {
    results: ScenarioResult[];
  };
  decision_memo?: {
    recommendation?: string;
    justification?: string | {
      answer: string;
      citations: Array<{
        title: string;
        source: string;
        url?: string;
        relevance: string;
      }>;
    };
    citations?: Array<{
      title: string;
      source: string;
      url?: string;
      relevance: string;
    }>;
    confidence?: number;
    metrics?: {
      clearance_time: number;
      max_queue: number;
      fairness_index: number;
      robustness: number;
      [key: string]: any;
    };
    generated_by?: string;
    timestamp?: string;
  };
  user_intent?: {
    objective: string;
    city: string;
    preferences: {
      clearance_weight: number;
      fairness_weight: number;
      robustness_weight: number;
    };
  };
  // Allow for any additional fields from JSON
  [key: string]: any;
}

// Scenarios already have their real calculated values - no need to recalculate scores

const processScenarios = (runResult: RunResult): ScenarioResult[] => {
  // Use scenarios directly from the API response - no complex processing
  const scenarios = runResult.scenarios || [];
  
  if (scenarios.length === 0) {
    console.log('❌ No scenarios found');
    return [];
  }
  
  // Sort scenarios by performance score (fairness_index) in descending order
  const sortedScenarios = [...scenarios].sort((a, b) => {
    const scoreA = a.score || a.metrics?.fairness_index || 0;
    const scoreB = b.score || b.metrics?.fairness_index || 0;
    return scoreB - scoreA;
  });
  
  // Assign proper ranks based on sorted order
  const processed = sortedScenarios.map((scenario, index) => ({
    ...scenario,
    rank: index + 1,
    score: scenario.score || scenario.metrics?.fairness_index || 0
  }));
  
  return processed;
};

const getDecisionMemoData = (runResult: RunResult) => {
  const memo = runResult.decision_memo;
  if (!memo) return null;
  
  // Handle different memo formats
  let justification = '';
  let citations: any[] = [];
  
  if (typeof memo.justification === 'string') {
    justification = memo.justification;
    citations = memo.citations || [];
  } else if (memo.justification && typeof memo.justification === 'object') {
    justification = memo.justification.answer || '';
    citations = memo.justification.citations || [];
  }
  
  return {
    recommendation: memo.recommendation || 'Analysis completed',
    justification,
    citations,
    confidence: memo.confidence || 0.8,
    metrics: memo.metrics,
    generated_by: memo.generated_by,
    timestamp: memo.timestamp
  };
};

const ResultsGovUK: React.FC = () => {
  const { runId } = useParams<{ runId?: string }>();
  const [searchParams] = useSearchParams();
  const [selectedRunId, setSelectedRunId] = useState<string>(runId || '');
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [availableRuns, setAvailableRuns] = useState<Array<{run_id: string, status: string, created_at: string, city?: string, scenario_count?: number}>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [city, setCity] = useState<string>(searchParams.get('city') || 'westminster');
  const [sendingAlert, setSendingAlert] = useState(false);
  const [showResponseDraft, setShowResponseDraft] = useState(false);
  const [generatingResponse, setGeneratingResponse] = useState(false);
  const [responseDraft, setResponseDraft] = useState<string>('');
  const [responseApproved, setResponseApproved] = useState(false);
  const [alertStatus, setAlertStatus] = useState<{type: 'success' | 'error', message: string} | null>(null);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'detail'>(selectedRunId ? 'detail' : 'list');
  const [currentPage, setCurrentPage] = useState(1);
  const [runsPerPage] = useState(5); // Show 5 runs per page

  // Get current scenario data for context injection
  const currentScenario = runResult?.scenarios?.find(s => s.scenario_id === (activeScenarioId || runResult?.scenarios?.[0]?.scenario_id)) || runResult?.scenarios?.[0];
  
  // Prepare visualization data for context
  const visualizationData = currentScenario ? {
    scenario: currentScenario,
    simulation_data: currentScenario.simulation_data,
    metrics: currentScenario.metrics,
    config: {
      name: currentScenario.name,
      scenario_name: currentScenario.scenario_name,
      hazard_type: currentScenario.hazard_type,
      evacuation_direction: currentScenario.evacuation_direction,
      population_affected: currentScenario.population_affected,
      description: currentScenario.description
    },
    hasInteractiveMap: !!currentScenario.simulation_data?.interactive_map_html,
    hasRealData: !!currentScenario.metrics
  } : null;

  // Inject context for chat integration
  useResultsContextInjection(
    availableRuns,
    runResult,
    visualizationData,
    { 
      activeTab, 
      viewMode, 
      city,
      selectedRunId,
      activeScenarioId,
      currentScenarioName: currentScenario?.name || currentScenario?.scenario_name,
      hazardType: currentScenario?.hazard_type,
      evacuationDirection: currentScenario?.evacuation_direction
    },
    loading,
    error,
    'Prime Minister'
  );

  // Extract target city from results data with multiple fallback sources
  const getTargetCityFromResults = (runResult: RunResult): string => {
    // Priority 1: Check direct city field from API response (most reliable)
    if (runResult.city) {
      return runResult.city;
    }
    
    // Priority 2: Check user_intent.city (legacy approach)
    if (runResult.user_intent?.city) {
      return runResult.user_intent.city;
    }
    
    // Priority 3: Try to extract from scenarios or artifacts
    // Look for city-specific data patterns in scenarios
    if (runResult.scenarios && runResult.scenarios.length > 0) {
      const firstScenario = runResult.scenarios[0];
      // Check if scenario description contains city hints
      if (firstScenario.description) {
        const desc = firstScenario.description.toLowerCase();
        if (desc.includes('london') || desc.includes('uk') || desc.includes('britain')) {
          return 'london';
        }
      }
    }
    
    // Priority 4: Fallback to URL parameter or default
    return searchParams.get('city') || city || 'westminster';
  };

  // Format borough/city name for display with appropriate flag and formatting
  const formatCityDisplay = (cityName: string): string => {
    if (!cityName) return 'London';
    
    const city = cityName.toLowerCase();
    
    // London boroughs - format with proper capitalization and UK flag
    const londonBoroughs = [
      'city of london', 'westminster', 'kensington and chelsea', 'hammersmith and fulham',
      'wandsworth', 'lambeth', 'southwark', 'tower hamlets', 'hackney', 'islington',
      'camden', 'brent', 'ealing', 'hounslow', 'richmond upon thames', 'kingston upon thames',
      'merton', 'sutton', 'croydon', 'bromley', 'lewisham', 'greenwich', 'bexley',
      'havering', 'redbridge', 'newham', 'waltham forest', 'haringey', 'enfield',
      'barnet', 'harrow', 'hillingdon', 'barking and dagenham'
    ];
    
    if (londonBoroughs.includes(city)) {
      // Format borough name with proper capitalization
      const formattedName = city
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      return formattedName;
    }
    
    // Generic London fallback
    if (city.includes('london') || city.includes('uk') || city.includes('britain')) {
      return 'London';
    }
    
    // Default fallback - assume it's a UK location
    const formattedName = city
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
    return formattedName;
  };

  // Handle clicking into a run from the list
  const handleRunClick = (runId: string) => {
    setSelectedRunId(runId);
    setViewMode('detail');
    setActiveTab('overview'); // Reset to overview tab when switching runs
  };

  // Handle going back to the list
  const handleBackToList = () => {
    setViewMode('list');
    setSelectedRunId('');
    setRunResult(null);
  };

  // Update view mode based on selectedRunId
  useEffect(() => {
    if (selectedRunId && viewMode === 'list') {
      setViewMode('detail');
    } else if (!selectedRunId && viewMode === 'detail') {
      setViewMode('list');
    }
  }, [selectedRunId]); // Remove viewMode from dependencies to prevent infinite loop

  // Debug logging - reduced to prevent infinite loops
  useEffect(() => {
    console.log('ResultsGovUK - Initial load:', { 
      cityFromURL: searchParams.get('city'), 
      selectedRunId, 
      viewMode 
    });
  }, []); // No dependencies to prevent infinite loops

  // Fetch available runs - only show completed runs with visualization data
  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.list}`);
        if (response.ok) {
          const data = await response.json();
          const allRuns = data.runs || [];
          
          // Show all completed runs (visualization data will be checked when viewing details)
          const validRuns = allRuns.filter(run => run.status === 'completed');
          setAvailableRuns(validRuns);
          
          // Only auto-select if we have a runId from URL params or if we're in detail mode
          if (!selectedRunId && validRuns.length > 0 && (runId || viewMode === 'detail')) {
            setSelectedRunId(validRuns[0].run_id);
            setViewMode('detail');
          }
        }
      } catch (err) {
        console.error('Failed to fetch runs:', err);
      }
    };

    fetchRuns();
  }, [runId]); // Remove viewMode from dependencies to prevent infinite loop

  // Fetch specific run result - only when in detail mode
  useEffect(() => {
    if (!selectedRunId || viewMode !== 'detail') return;

    const fetchRunResult = async () => {
      setLoading(true);
      setError(null);

      try {
        // Try to fetch real simulation run first (from new agentic endpoint)
        let response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.runResult(selectedRunId)}`);

        if (response.ok) {
          const data = await response.json();
          console.log('🎯 Real simulation data loaded:', data);

          // Try to load additional scenario and result data
          let enhancedScenarios = data.scenarios || [];
          
          // REMOVED: Problematic fallback to /scenarios endpoint that returns corrupted data
          console.log('✅ Using scenarios directly from primary API response - no fallbacks needed');
          console.log('🔍 DEBUG: Primary scenarios data:', enhancedScenarios.slice(0, 2).map(s => ({
            name: s.scenario_name,
            clearance: s.metrics?.clearance_time,
            fairness: s.metrics?.fairness_index
          })));

          const realResult: RunResult = {
            run_id: selectedRunId,
            status: data.status || 'completed',
            created_at: data.created_at || new Date().toISOString(),
            completed_at: data.completed_at || new Date().toISOString(),
            scenario_count: data.scenario_count || enhancedScenarios.length,
            best_scenario_id: data.best_scenario_id,
            city: data.city || 'westminster',
            scenarios: enhancedScenarios,
            decision_memo: data.decision_memo,
            user_intent: data.user_intent || data.intent,
            // Store the raw data for debugging
            _rawData: data
          };

          console.log('🏗️ Final processed result:', realResult);
          setRunResult(realResult);
        } else {
          // Try to fetch evacuation run (for legacy agentic runs)
          response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.run(selectedRunId)}`);

          if (response.ok) {
            const data = await response.json();
            console.log('🎯 Evacuation run data loaded:', data);

            // Try to load additional scenario and result data
            let enhancedScenarios = data.scenarios || [];
            
            // REMOVED: Second problematic fallback to /scenarios endpoint
            console.log('✅ Using evacuation scenarios directly from primary API response');

            const realResult: RunResult = {
              run_id: selectedRunId,
              status: data.status || 'completed',
              created_at: data.created_at || new Date().toISOString(),
              completed_at: data.completed_at || new Date().toISOString(),
              scenario_count: data.scenario_count || enhancedScenarios.length,
              best_scenario_id: data.best_scenario_id,
              scenarios: enhancedScenarios,
              decision_memo: data.decision_memo,
              user_intent: data.user_intent || data.intent,
              // Store the raw data for debugging
              _rawData: data
            };

            console.log('🏗️ Final evacuation result:', realResult);
            setRunResult(realResult);
          } else {
            // If evacuation run not found, try city simulation result
            response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.result(city, selectedRunId)}`);

            if (response.ok) {
              const simData = await response.json();
              console.log('🏙️ City simulation data loaded:', simData);
              
              // Store simulation data for visualisation component
              (window as any).citySimulationData = simData;

              // Try to load scenarios and results from the local storage files
              let scenarios: ScenarioResult[] = [];
              let decision_memo = null;
              
              try {
                // Try to load scenarios.json and results.json from the run directory
                const scenariosResponse = await fetch(`/api/runs/${selectedRunId}/scenarios.json`);
                const resultsResponse = await fetch(`/api/runs/${selectedRunId}/results.json`);
                const memoResponse = await fetch(`/api/runs/${selectedRunId}/memo.json`);
                
                if (scenariosResponse.ok && resultsResponse.ok) {
                  const scenariosData = await scenariosResponse.json();
                  const resultsData = await resultsResponse.json();
                  
                  console.log('📋 Loaded scenarios from files:', scenariosData);
                  console.log('📊 Loaded results from files:', resultsData);
                  
                  // Use scenarios directly without complex processing
                  if (scenariosData.scenarios) {
                    scenarios = scenariosData.scenarios;
                  }
                }
                
                if (memoResponse.ok) {
                  decision_memo = await memoResponse.json();
                  console.log('📝 Loaded memo from file:', decision_memo);
                }
              } catch (err) {
                console.log('⚠️ Could not load data from files:', err);
              }

              // Create a RunResult for display
              const simResult: RunResult = {
                run_id: selectedRunId,
                status: simData.status || 'completed',
                created_at: simData.completed_at || simData.timestamp || new Date().toISOString(),
                completed_at: simData.completed_at || simData.timestamp,
                scenario_count: scenarios.length,
                scenarios: scenarios,
                decision_memo: decision_memo,
                user_intent: {
                  objective: 'City Evacuation Simulation',
                  city: simData.city || city,
                  preferences: {
                    clearance_weight: 0.5,
                    fairness_weight: 0.3,
                    robustness_weight: 0.2
                  }
                },
                // Store the raw data for debugging
                _rawData: simData
              };

              setRunResult(simResult);
            } else {
              setError('Failed to fetch run results');
            }
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchRunResult();
  }, [selectedRunId, viewMode]); // Remove city dependency to prevent infinite loops

  // Auto-refresh when simulation is in progress
  useEffect(() => {
    if (!runResult || runResult.status !== 'in_progress') return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.runResult(selectedRunId)}`);
        if (response.ok) {
          const data = await response.json();
          if (data.status !== 'in_progress') {
            // Simulation completed or failed, trigger full refresh
            window.location.reload();
          }
        }
      } catch (err) {
        console.error('Polling failed:', err);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [runResult?.status, selectedRunId]);

  // Send WhatsApp alert to government contact
  const generateCoordinatedResponse = async () => {
    if (!runResult) return;
    
    setGeneratingResponse(true);
    setShowResponseDraft(true);
    
    try {
      const targetCity = getTargetCityFromResults(runResult);
      const scenarios = runResult.scenarios || [];
      const bestScenario = scenarios.find(s => s.metrics) || scenarios[0];
      
      // Prepare context for LLM
      const context = {
        city: targetCity,
        run_id: runResult.run_id,
        scenario_count: scenarios.length,
        metrics: bestScenario?.metrics,
        clearance_time: bestScenario?.metrics?.clearance_time,
        fairness_index: bestScenario?.metrics?.fairness_index,
        robustness: bestScenario?.metrics?.robustness,
        timestamp: new Date().toISOString()
      };
      
      const response = await fetch(`${API_CONFIG.baseUrl}/api/coordination/generate-response`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          context,
          response_type: 'coordinated_emergency_response'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setResponseDraft(data.draft_response || 'Failed to generate response draft.');
      } else {
        // Fallback: Generate a basic template if API fails
        const fallbackResponse = generateFallbackResponse(context);
        setResponseDraft(fallbackResponse);
      }
    } catch (error) {
      console.error('Failed to generate coordinated response:', error);
      const fallbackResponse = generateFallbackResponse({
        city: getTargetCityFromResults(runResult),
        run_id: runResult.run_id,
        scenario_count: runResult.scenarios?.length || 0,
        timestamp: new Date().toISOString()
      });
      setResponseDraft(fallbackResponse);
    } finally {
      setGeneratingResponse(false);
    }
  };

  const generateFallbackResponse = (context: any) => {
    return `EMERGENCY COORDINATION RESPONSE - ${context.city?.toUpperCase()}

SITUATION ASSESSMENT:
- Location: ${context.city}
- Analysis Run ID: ${context.run_id}
- Scenarios Evaluated: ${context.scenario_count}
- Assessment Time: ${new Date(context.timestamp).toLocaleString()}

EVACUATION METRICS:
${context.clearance_time ? `- Estimated Clearance Time: ${Math.round(context.clearance_time)} minutes` : '- Clearance Time: Under analysis'}
${context.fairness_index ? `- Route Equity Index: ${(context.fairness_index * 100).toFixed(1)}%` : '- Route Equity: Under analysis'}
${context.robustness ? `- Network Resilience: ${(context.robustness * 100).toFixed(1)}%` : '- Network Resilience: Under analysis'}

RECOMMENDED ACTIONS:
1. Activate emergency coordination protocols for ${context.city}
2. Deploy resources to identified bottleneck areas
3. Establish communication with local authorities
4. Monitor situation and adjust response as needed

COORDINATION REQUIREMENTS:
- Emergency Services: Police, Fire, Ambulance
- Local Authority: ${context.city} Council
- Transport: TfL coordination required
- Communications: Public information systems

This is an AI-generated draft requiring human approval before distribution.

Generated: ${new Date().toLocaleString()}`;
  };

  const sendWhatsAppAlert = async () => {
    if (!runResult) return;

    setSendingAlert(true);
    setAlertStatus(null);

    try {
      const targetCity = getTargetCityFromResults(runResult);
      const formattedCity = formatCityDisplay(targetCity);
      const message = `🚨 EMERGENCY EVACUATION ALERT\n\nRun ID: ${runResult.run_id}\nLocation: ${formattedCity}\nStatus: ${runResult.status}\nScenarios: ${runResult.scenario_count}\nBest Scenario: ${runResult.best_scenario_id || 'N/A'}\n\nView results: ${window.location.href}\n\nImmediate action required.`;

      const response = await fetch(`${API_CONFIG.baseUrl}/api/notifications/government-alert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          priority: 'critical'
        })
      });

      if (response.ok) {
        setAlertStatus({ type: 'success', message: '✅ WhatsApp alert sent to government contact' });
        setTimeout(() => setAlertStatus(null), 5000);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send alert');
      }
    } catch (error) {
      console.error('Failed to send WhatsApp alert:', error);
      setAlertStatus({
        type: 'error',
        message: `❌ Failed to send alert: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    } finally {
      setSendingAlert(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const generateRunDisplayName = (run: {run_id: string, status: string, created_at: string, city?: string, scenario_count?: number}) => {
    const cityName = run.city ? formatCityDisplay(run.city) : '🏙️ Unknown City';
    const scenarioText = run.scenario_count ? `${run.scenario_count} scenarios` : 'City simulation';
    const date = new Date(run.created_at).toLocaleDateString('en-GB', { 
      day: 'numeric', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
    return `${cityName} - ${scenarioText} (${date})`;
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      'completed': GOVUK_CLASSES.tag.green,
      'failed': GOVUK_CLASSES.tag.red,
      'in_progress': GOVUK_CLASSES.tag.orange,
      'pending': GOVUK_CLASSES.tag.grey
    };
    return statusMap[status as keyof typeof statusMap] || GOVUK_CLASSES.tag.grey;
  };

  // Manhattan gets super simple results page  
  if (city === 'manhattan' && !selectedRunId) {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          <span className="govuk-caption-xl">🗽 Manhattan Simulation</span>
          <h1 className={GOVUK_CLASSES.heading.xl}>Comprehensive Evacuation Analysis</h1>
          <p className={GOVUK_CLASSES.body.lead}>
            A* optimal routing, biased random walk simulation, and exit point density analysis on real street network
          </p>

          <div className="govuk-grid-row govuk-!-margin-top-6">
            <div className="govuk-grid-column-full">
              <CitySpecificVisualisation city={runResult ? getTargetCityFromResults(runResult) : "manhattan"} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render list view
  if (viewMode === 'list') {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          
          {/* Page Header */}
          <div style={{ marginBottom: '32px' }}>
            <span className="govuk-caption-xl">Emergency Planning Results</span>
            <h1 className={GOVUK_CLASSES.heading.xl}>Evacuation Planning Runs</h1>
            <p className={GOVUK_CLASSES.body.lead}>
              View all completed evacuation planning runs. Click on any run to see detailed results and analysis.
            </p>
          </div>

          {/* Alert Status Banner */}
          {alertStatus && (
            <div className={alertStatus.type === 'success' ? 'govuk-panel govuk-panel--confirmation' : 'govuk-error-summary'}
                 style={{ marginBottom: '24px', padding: '15px' }}>
              <p style={{ margin: 0 }}>{alertStatus.message}</p>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className={GOVUK_CLASSES.insetText}>
              <p>Loading evacuation planning runs...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="govuk-error-summary" aria-labelledby="error-summary-title" role="alert">
              <h2 className="govuk-error-summary__title" id="error-summary-title">
                There is a problem
              </h2>
              <div className="govuk-error-summary__body">
                <ul className="govuk-list govuk-error-summary__list">
                  <li>{error}</li>
                </ul>
              </div>
            </div>
          )}

          {/* Runs List */}
          {!loading && !error && (
            <>
              {/* Queue Status Section */}
              <div style={{ marginBottom: '40px' }}>
                <h2 className={GOVUK_CLASSES.heading.l} style={{ marginBottom: '16px' }}>
                  Simulation Queue
                </h2>
                <p className={GOVUK_CLASSES.body.m} style={{ marginBottom: '20px' }}>
                  Monitor pending, running, and completed simulations.
                </p>
                <details className="govuk-details" open>
                  <summary className="govuk-details__summary">
                    <span className="govuk-details__summary-text">
                      View Queue Details
                    </span>
                  </summary>
                  <div className="govuk-details__text">
                    <SimulationQueue />
                  </div>
                </details>
              </div>

              {availableRuns.length === 0 ? (
                <div className={GOVUK_CLASSES.insetText}>
                  <p>No evacuation planning results available. <Link to="/plan" className="govuk-link">Start a new planning run</Link> to see results here.</p>
                </div>
              ) : (
                <>
                  <h2 className={GOVUK_CLASSES.heading.l} style={{ marginBottom: '16px' }}>
                    Completed Simulation Results
                  </h2>
                  <p className={GOVUK_CLASSES.body.m} style={{ marginBottom: '20px' }}>
                    {availableRuns.length} completed run{availableRuns.length !== 1 ? 's' : ''}
                  </p>
                  
                  {/* Pagination Controls */}
                  {availableRuns.length > runsPerPage && (
                    <nav className="govuk-pagination" role="navigation" aria-label="Pagination" style={{ marginBottom: '24px' }}>
                      <div className="govuk-pagination__prev">
                        {currentPage > 1 && (
                          <button
                            className="govuk-link govuk-pagination__link"
                            onClick={() => setCurrentPage(currentPage - 1)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                          >
                            <svg className="govuk-pagination__icon govuk-pagination__icon--prev" xmlns="http://www.w3.org/2000/svg" height="13" width="15" aria-hidden="true" focusable="false" viewBox="0 0 15 13">
                              <path d="m6.5938-0.0078125-6.7266 6.7266 6.7441 6.4062 1.377-1.449-4.1856-3.9768h12.896v-2h-12.984l4.2931-4.293-1.414-1.414z"></path>
                            </svg>
                            <span className="govuk-pagination__link-title">Previous</span>
                          </button>
                        )}
                      </div>
                      
                      <ul className="govuk-pagination__list">
                        {Array.from({ length: Math.ceil(availableRuns.length / runsPerPage) }, (_, i) => i + 1).map(page => (
                          <li key={page} className="govuk-pagination__item">
                            <button
                              className={`govuk-link govuk-pagination__link ${page === currentPage ? 'govuk-pagination__link--current' : ''}`}
                              onClick={() => setCurrentPage(page)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                              aria-label={`Page ${page}`}
                              aria-current={page === currentPage ? 'page' : undefined}
                            >
                              {page}
                            </button>
                          </li>
                        ))}
                      </ul>
                      
                      <div className="govuk-pagination__next">
                        {currentPage < Math.ceil(availableRuns.length / runsPerPage) && (
                          <button
                            className="govuk-link govuk-pagination__link"
                            onClick={() => setCurrentPage(currentPage + 1)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                          >
                            <span className="govuk-pagination__link-title">Next</span>
                            <svg className="govuk-pagination__icon govuk-pagination__icon--next" xmlns="http://www.w3.org/2000/svg" height="13" width="15" aria-hidden="true" focusable="false" viewBox="0 0 15 13">
                              <path d="m8.107-0.0078125-1.4136 1.414 4.2926 4.293h-12.986v2h12.896l-4.1855 3.9766 1.377 1.4492 6.7441-6.4062-6.7246-6.7266z"></path>
                            </svg>
                          </button>
                        )}
                      </div>
                    </nav>
                  )}
                  
                  <div className="govuk-grid-row">
                    {availableRuns
                      .slice((currentPage - 1) * runsPerPage, currentPage * runsPerPage)
                      .map(run => (
                      <div key={run.run_id} className="govuk-grid-column-full" style={{ marginBottom: '24px' }}>
                        <div 
                          className="govuk-summary-card"
                          style={{ 
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            border: '2px solid #b1b4b6',
                            borderRadius: '4px'
                          }}
                          onClick={() => handleRunClick(run.run_id)}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = '#1d70b8';
                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(29, 112, 184, 0.1)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = '#b1b4b6';
                            e.currentTarget.style.boxShadow = 'none';
                          }}
                        >
                          <div className="govuk-summary-card__title-wrapper">
                            <h3 className="govuk-summary-card__title">
                              {run.city ? formatCityDisplay(run.city) : 'Unknown City'} Evacuation Plan
                            </h3>
                            <div className="govuk-summary-card__actions">
                              <span className={getStatusTag(run.status)}>
                                {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                              </span>
                            </div>
                          </div>
                          <div className="govuk-summary-card__content">
                            <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
                              {/* Visualization Thumbnail */}
                              <div style={{ flexShrink: 0 }}>
                                <VisualizationThumbnail
                                  runId={run.run_id}
                                  city={run.city || 'westminster'}
                                  style={{
                                    width: '160px',
                                    height: '120px',
                                    borderRadius: '4px',
                                    border: '1px solid #b1b4b6'
                                  }}
                                />
                              </div>
                              
                              {/* Run Details */}
                              <div style={{ flex: 1 }}>
                                <dl className={GOVUK_CLASSES.summaryList.container}>
                                  <div className={GOVUK_CLASSES.summaryList.row}>
                                    <dt className={GOVUK_CLASSES.summaryList.key}>Run ID</dt>
                                    <dd className={GOVUK_CLASSES.summaryList.value}>
                                      <code className="govuk-!-font-family-monospace">{run.run_id}</code>
                                    </dd>
                                  </div>
                                  <div className={GOVUK_CLASSES.summaryList.row}>
                                    <dt className={GOVUK_CLASSES.summaryList.key}>Created</dt>
                                    <dd className={GOVUK_CLASSES.summaryList.value}>
                                      {formatDateTime(run.created_at)}
                                    </dd>
                                  </div>
                                  <div className={GOVUK_CLASSES.summaryList.row}>
                                    <dt className={GOVUK_CLASSES.summaryList.key}>Scenarios</dt>
                                    <dd className={GOVUK_CLASSES.summaryList.value}>
                                      {run.scenario_count || 'Multiple'} scenarios analyzed
                                    </dd>
                                  </div>
                                </dl>
                                <div style={{ marginTop: '16px', textAlign: 'right' }}>
                                  <span className="govuk-link" style={{ textDecoration: 'none' }}>
                                    View detailed results →
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  // Render detail view
  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>
        
        {/* Back to List Button */}
        <div style={{ marginBottom: '24px' }}>
          <button 
            onClick={handleBackToList}
            className="govuk-back-link"
            style={{ 
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textDecoration: 'none'
            }}
          >
            Back to all runs
          </button>
        </div>
        
        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
          <div>
            <span className="govuk-caption-xl">Emergency Planning Results</span>
            <h1 className={GOVUK_CLASSES.heading.xl}>Evacuation Scenario Analysis</h1>
            <p className={GOVUK_CLASSES.body.lead}>
              Detailed results for evacuation planning run with decision memo and supporting evidence
            </p>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            {/* Coordinate Response Button */}
            <button
              onClick={generateCoordinatedResponse}
              disabled={generatingResponse || !runResult}
              className={`govuk-button ${generatingResponse || !runResult ? 'govuk-button--disabled' : ''}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                minWidth: '200px',
                justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              {/* Background animation for generating state */}
              {generatingResponse && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: '-100%',
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
                  animation: 'shimmer 1.5s infinite'
                }} />
              )}
              
              <span>
                {generatingResponse ? 'Generating Response...' : 'Coordinate Response'}
              </span>
              
              {sendingAlert && (
                <div style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid rgba(255,255,255,0.3)',
                  borderTop: '2px solid #ffffff',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
              )}
            </button>
          </div>

          {/* Add CSS animations */}
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
            
            @keyframes shimmer {
              0% { left: -100%; }
              100% { left: 100%; }
            }
          `}</style>
        </div>

        {/* Alert Status Banner */}
        {alertStatus && (
          <div className={alertStatus.type === 'success' ? 'govuk-panel govuk-panel--confirmation' : 'govuk-error-summary'}
               style={{ marginBottom: '24px', padding: '15px' }}>
            <p style={{ margin: 0 }}>{alertStatus.message}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className={GOVUK_CLASSES.insetText}>
            <p>Loading evacuation planning results...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="govuk-error-summary" aria-labelledby="error-summary-title" role="alert">
            <h2 className="govuk-error-summary__title" id="error-summary-title">
              There is a problem
            </h2>
            <div className="govuk-error-summary__body">
              <ul className="govuk-list govuk-error-summary__list">
                <li>{error}</li>
              </ul>
            </div>
          </div>
        )}

        {/* Results Content */}
        {runResult && !loading && (
          <>
            {/* In Progress Banner */}
            {runResult.status === 'in_progress' && (
              <div className="govuk-notification-banner govuk-notification-banner--info" role="alert" style={{ marginBottom: '24px' }}>
                <div className="govuk-notification-banner__header">
                  <h2 className="govuk-notification-banner__title">Simulation In Progress</h2>
                </div>
                <div className="govuk-notification-banner__content">
                  <p className={GOVUK_CLASSES.body.m}>
                    <strong>Simulation is currently running...</strong>
                  </p>
                  <p className={GOVUK_CLASSES.body.s}>
                    The evacuation simulation is being computed in the background.
                    This page will automatically refresh when results are available (checking every 5 seconds).
                  </p>
                  <div style={{ marginTop: '12px' }}>
                    <div style={{
                      width: '100%',
                      height: '4px',
                      backgroundColor: '#e0e0e0',
                      borderRadius: '2px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: '30%',
                        height: '100%',
                        backgroundColor: '#1d70b8',
                        animation: 'progress 2s ease-in-out infinite'
                      }} />
                    </div>
                  </div>
                  <style>{`
                    @keyframes progress {
                      0% { width: 10%; margin-left: 0%; }
                      50% { width: 40%; margin-left: 30%; }
                      100% { width: 10%; margin-left: 90%; }
                    }
                  `}</style>
                </div>
              </div>
            )}

            {/* Run Overview */}
            <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
              <h2 className={GOVUK_CLASSES.heading.m}>Run Overview</h2>
              
              <dl className={GOVUK_CLASSES.summaryList.container}>
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Run ID</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>
                    <code className="govuk-!-font-family-monospace">{runResult.run_id}</code>
                  </dd>
                </div>
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Status</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>
                    <span className={getStatusTag(runResult.status)}>
                      {runResult.status.charAt(0).toUpperCase() + runResult.status.slice(1)}
                    </span>
                  </dd>
                </div>
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Created</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>{formatDateTime(runResult.created_at)}</dd>
                </div>
                {runResult.completed_at && (
                  <div className={GOVUK_CLASSES.summaryList.row}>
                    <dt className={GOVUK_CLASSES.summaryList.key}>Completed</dt>
                    <dd className={GOVUK_CLASSES.summaryList.value}>{formatDateTime(runResult.completed_at)}</dd>
                  </div>
                )}
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Scenarios Generated</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>{runResult.scenario_count}</dd>
                </div>
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Objective</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>
                    {runResult.user_intent?.objective.replace(/_/g, ' ')}
                  </dd>
                </div>
                <div className={GOVUK_CLASSES.summaryList.row}>
                  <dt className={GOVUK_CLASSES.summaryList.key}>Target City</dt>
                  <dd className={GOVUK_CLASSES.summaryList.value}>
                    {formatCityDisplay(getTargetCityFromResults(runResult))}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Tabs for different views */}
            <div className={`${GOVUK_CLASSES.tabs.container} ${GOVUK_CLASSES.spacing.marginBottom[6]}`} data-module="govuk-tabs">
              <h2 className="govuk-tabs__title">Contents</h2>
              
              <ul className={GOVUK_CLASSES.tabs.list}>
                <li className={GOVUK_CLASSES.tabs.item}>
                  <button 
                    className={`${GOVUK_CLASSES.tabs.tab} ${activeTab === 'overview' ? 'govuk-tabs__tab--selected' : ''}`}
                    onClick={() => setActiveTab('overview')}
                  >
                    Scenario Rankings
                  </button>
                </li>
                <li className={GOVUK_CLASSES.tabs.item}>
                  <button 
                    className={`${GOVUK_CLASSES.tabs.tab} ${activeTab === 'memo' ? 'govuk-tabs__tab--selected' : ''}`}
                    onClick={() => setActiveTab('memo')}
                  >
                    Decision Memo
                  </button>
                </li>
                <li className={GOVUK_CLASSES.tabs.item}>
                  <button 
                    className={`${GOVUK_CLASSES.tabs.tab} ${activeTab === 'metrics' ? 'govuk-tabs__tab--selected' : ''}`}
                    onClick={() => setActiveTab('metrics')}
                  >
                    Detailed Metrics
                  </button>
                </li>
                <li className={GOVUK_CLASSES.tabs.item}>
                  <button 
                    className={`${GOVUK_CLASSES.tabs.tab} ${activeTab === 'visualisation' ? 'govuk-tabs__tab--selected' : ''}`}
                    onClick={() => setActiveTab('visualisation')}
                  >
                    Visualisation
                  </button>
                </li>
              </ul>

              {/* Scenario Rankings Tab */}
              {activeTab === 'overview' && (
                <div className={`${GOVUK_CLASSES.tabs.panel}`}>
                  <h2 className={GOVUK_CLASSES.heading.m}>Scenario Rankings</h2>
                  
                  {runResult.best_scenario_id && (
                    <div className="govuk-notification-banner govuk-notification-banner--success" role="alert">
                      <div className="govuk-notification-banner__header">
                        <h2 className="govuk-notification-banner__title">Success</h2>
                      </div>
                      <div className="govuk-notification-banner__content">
                        <h3 className="govuk-notification-banner__heading">
                          Recommended Evacuation Strategy
                        </h3>
                        <p className={GOVUK_CLASSES.body.m}>
                          <strong>{runResult.scenarios.find(s => s.scenario_id === runResult.best_scenario_id)?.scenario_name}</strong> 
                          {' '}has been identified as the optimal evacuation strategy for this scenario.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Mobile-responsive table wrapper */}
                  <div style={{ overflowX: 'auto', marginBottom: '1rem' }}>
                    <table className={GOVUK_CLASSES.table.container} style={{ minWidth: '600px' }}>
                      <caption className={GOVUK_CLASSES.table.caption}>
                        Evacuation scenarios ranked by overall performance score
                      </caption>
                      <thead className={GOVUK_CLASSES.table.head}>
                        <tr className={GOVUK_CLASSES.table.row}>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Rank</th>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Scenario</th>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Clearance Time</th>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Fairness Index</th>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Score</th>
                          <th scope="col" className={GOVUK_CLASSES.table.header}>Status</th>
                        </tr>
                      </thead>
                      <tbody className={GOVUK_CLASSES.table.body}>
                        {(() => {
                          const processedScenarios = processScenarios(runResult);
                          
                          if (processedScenarios.length === 0) {
                            return (
                              <tr className={GOVUK_CLASSES.table.row}>
                                <td className={GOVUK_CLASSES.table.cell} colSpan={6}>
                                  <div className="govuk-inset-text">
                                    <p><strong>No scenario data available</strong></p>
                                    <details className="govuk-details">
                                      <summary className="govuk-details__summary">
                                        <span className="govuk-details__summary-text">
                                          Debug Information
                                        </span>
                                      </summary>
                                      <div className="govuk-details__text">
                                        <p><strong>Run ID:</strong> {runResult.run_id}</p>
                                        <p><strong>Status:</strong> {runResult.status}</p>
                                        <p><strong>Scenario Count:</strong> {runResult.scenario_count}</p>
                                        <p><strong>Available Keys:</strong> {Object.keys(runResult).join(', ')}</p>
                                        {runResult._rawData && (
                                          <p><strong>Raw Data Keys:</strong> {Object.keys(runResult._rawData).join(', ')}</p>
                                        )}
                                      </div>
                                    </details>
                                  </div>
                                </td>
                              </tr>
                            );
                          }
                          
                          return processedScenarios.map((scenario) => (
                            <tr key={scenario.scenario_id} className={GOVUK_CLASSES.table.row}>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <span className={scenario.rank === 1 ? GOVUK_CLASSES.tag.green : GOVUK_CLASSES.tag.blue}>
                                  #{scenario.rank}
                                </span>
                              </td>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <div>
                                  <strong>{scenario.scenario_name || scenario.name || scenario.scenario_id}</strong>
                                  {scenario.hazard_type && (
                                    <div className="govuk-body-s govuk-!-margin-top-1">
                                      <span className={`govuk-tag govuk-tag--${
                                        scenario.hazard_type === 'fire' ? 'red' :
                                        scenario.hazard_type === 'flood' ? 'blue' :
                                        scenario.hazard_type === 'terrorist' ? 'orange' :
                                        scenario.hazard_type === 'chemical' ? 'purple' : 'grey'
                                      }`}>
                                        {scenario.hazard_type}
                                      </span>
                                      {scenario.evacuation_direction && (
                                        <span className="govuk-!-margin-left-2 govuk-body-s">
                                          {scenario.evacuation_direction}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                  {scenario.population_affected && (
                                    <div className="govuk-body-s govuk-!-margin-top-1">
                                      Population: {scenario.population_affected.toLocaleString()}
                                    </div>
                                  )}
                                  {scenario.description && (
                                    <div className="govuk-hint" style={{ marginTop: '5px', fontSize: '0.875rem' }}>
                                      {scenario.description}
                                    </div>
                                  )}
                                </div>
                              </td>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <strong>{scenario.metrics.clearance_time.toFixed(1)} min</strong>
                                {scenario.expected_clearance_time && scenario.expected_clearance_time !== scenario.metrics.clearance_time && (
                                  <div className="govuk-body-s">
                                    Expected: {scenario.expected_clearance_time.toFixed(1)} min
                                  </div>
                                )}
                              </td>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <div>
                                  <strong>{(scenario.metrics.fairness_index * 100).toFixed(0)}%</strong>
                                </div>
                                <div className="govuk-body-s">
                                  Robustness: {(scenario.metrics.robustness * 100).toFixed(0)}%
                                </div>
                              </td>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <strong>{((scenario.score || 0) * 100).toFixed(0)}%</strong>
                                {scenario.rank === 1 && (
                                  <div className="govuk-!-margin-top-1">
                                    <span className="govuk-tag govuk-tag--green">BEST</span>
                                  </div>
                                )}
                              </td>
                              <td className={GOVUK_CLASSES.table.cell}>
                                <span className={getStatusTag(scenario.status)}>
                                  {scenario.status}
                                </span>
                                {scenario.duration_ms && (
                                  <div className="govuk-body-s govuk-!-margin-top-1">
                                    Runtime: {(scenario.duration_ms / 1000).toFixed(1)}s
                                  </div>
                                )}
                              </td>
                            </tr>
                          ));
                        })()}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Decision Memo Tab */}
              {activeTab === 'memo' && (
                <div className={GOVUK_CLASSES.tabs.panel}>
                  <h2 className={GOVUK_CLASSES.heading.m}>Decision Memo</h2>
                  
                  {(() => {
                    const memoData = getDecisionMemoData(runResult);
                    
                    if (!memoData) {
                      return (
                        <div className="govuk-inset-text">
                          <p><strong>No decision memo available for this run.</strong></p>
                          <details className="govuk-details">
                            <summary className="govuk-details__summary">
                              <span className="govuk-details__summary-text">
                                Debug Information
                              </span>
                            </summary>
                            <div className="govuk-details__text">
                              <p><strong>Run ID:</strong> {runResult.run_id}</p>
                              <p><strong>Decision Memo Present:</strong> {runResult.decision_memo ? 'Yes' : 'No'}</p>
                              {runResult.decision_memo && (
                                <p><strong>Memo Keys:</strong> {Object.keys(runResult.decision_memo).join(', ')}</p>
                              )}
                            </div>
                          </details>
                        </div>
                      );
                    }
                    
                    return (
                      <>
                        {/* Confidence and metadata */}
                        <div className={`${GOVUK_CLASSES.insetText} ${GOVUK_CLASSES.spacing.marginBottom[4]}`}>
                          <div className="govuk-grid-row">
                            <div className="govuk-grid-column-one-half">
                              <p className={GOVUK_CLASSES.font.weightBold}>
                                Recommendation Confidence: {(memoData.confidence * 100).toFixed(0)}%
                              </p>
                            </div>
                            <div className="govuk-grid-column-one-half">
                              {memoData.generated_by && (
                                <p className="govuk-body-s">
                                  Generated by: {memoData.generated_by}
                                </p>
                              )}
                              {memoData.timestamp && (
                                <p className="govuk-body-s">
                                  Generated: {new Date(memoData.timestamp).toLocaleString()}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Key metrics from memo */}
                        {memoData.metrics && (
                          <div className="govuk-grid-row govuk-!-margin-bottom-4">
                            <div className="govuk-grid-column-full">
                              <h3 className={GOVUK_CLASSES.heading.s}>Key Performance Indicators</h3>
                              <div className="govuk-grid-row">
                                <div className="govuk-grid-column-one-quarter">
                                  <div className="govuk-panel govuk-panel--confirmation" style={{ padding: '15px', textAlign: 'center' }}>
                                    <h4 className="govuk-panel__title" style={{ fontSize: '1.2rem', marginBottom: '5px' }}>
                                      Clearance Time
                                    </h4>
                                    <div className="govuk-panel__body" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                      {memoData.metrics.clearance_time.toFixed(1)} min
                                    </div>
                                  </div>
                                </div>
                                {/* <div className="govuk-grid-column-one-quarter">
                                  <div className="govuk-panel govuk-panel--confirmation" style={{ padding: '15px', textAlign: 'center' }}>
                                    <h4 className="govuk-panel__title" style={{ fontSize: '1.2rem', marginBottom: '5px' }}>
                                      Max Queue
                                    </h4>
                                    <div className="govuk-panel__body" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                      {memoData.metrics.max_queue}
                                    </div>
                                  </div>
                                </div> */}
                                <div className="govuk-grid-column-one-quarter">
                                  <div className="govuk-panel govuk-panel--confirmation" style={{ padding: '15px', textAlign: 'center' }}>
                                    <h4 className="govuk-panel__title" style={{ fontSize: '1.2rem', marginBottom: '5px' }}>
                                      Fairness Index
                                    </h4>
                                    <div className="govuk-panel__body" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                      {(memoData.metrics.fairness_index * 100).toFixed(0)}%
                                    </div>
                                  </div>
                                </div>
                                <div className="govuk-grid-column-one-quarter">
                                  <div className="govuk-panel govuk-panel--confirmation" style={{ padding: '15px', textAlign: 'center' }}>
                                    <h4 className="govuk-panel__title" style={{ fontSize: '1.2rem', marginBottom: '5px' }}>
                                      Robustness
                                    </h4>
                                    <div className="govuk-panel__body" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                      {(memoData.metrics.robustness * 100).toFixed(0)}%
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        <h3 className={GOVUK_CLASSES.heading.s}>Executive Summary</h3>
                        <p className={GOVUK_CLASSES.body.m}>{memoData.recommendation}</p>

                        <h3 className={GOVUK_CLASSES.heading.s}>Analysis & Justification</h3>
                        <div className={GOVUK_CLASSES.body.m} style={{ whiteSpace: 'pre-wrap' }}>
                          {memoData.justification}
                        </div>

                        {memoData.citations && memoData.citations.length > 0 && (
                          <>
                            <h3 className={GOVUK_CLASSES.heading.s}>Supporting Evidence</h3>
                            <ul className="govuk-list">
                              {memoData.citations.map((citation, index) => (
                                <li key={index}>
                                  <details className={GOVUK_CLASSES.details.container}>
                                    <summary className={GOVUK_CLASSES.details.summary}>
                                      <span className={GOVUK_CLASSES.details.text}>
                                        {citation.title} - {citation.source}
                                      </span>
                                    </summary>
                                    <div className={GOVUK_CLASSES.details.text}>
                                      <p><strong>Relevance:</strong> {citation.relevance}</p>
                                      {citation.url && (
                                        <p>
                                          <a href={citation.url} className="govuk-link" target="_blank" rel="noopener noreferrer">
                                            View source document
                                          </a>
                                        </p>
                                      )}
                                    </div>
                                  </details>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Detailed Metrics Tab */}
              {activeTab === 'metrics' && (
                <div className={GOVUK_CLASSES.tabs.panel}>
                  <h2 className={GOVUK_CLASSES.heading.m}>Detailed Performance Metrics</h2>
                  
                  {(() => {
                    const processedScenarios = processScenarios(runResult);
                    
                    if (processedScenarios.length === 0) {
                      return (
                        <div className="govuk-inset-text">
                          <p>No detailed metrics available for this run.</p>
                        </div>
                      );
                    }
                    
                    return processedScenarios.map((scenario) => (
                      <div key={scenario.scenario_id} className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
                        <div className="govuk-grid-row">
                          <div className="govuk-grid-column-two-thirds">
                            <h3 className={GOVUK_CLASSES.heading.s}>
                              {scenario.scenario_name || scenario.name || scenario.scenario_id}
                              {scenario.rank === 1 && (
                                <span className="govuk-tag govuk-tag--green govuk-!-margin-left-2">
                                  RECOMMENDED
                                </span>
                              )}
                            </h3>
                            {scenario.hazard_type && (
                              <p className="govuk-body-s">
                                <span className={`govuk-tag govuk-tag--${
                                  scenario.hazard_type === 'fire' ? 'red' :
                                  scenario.hazard_type === 'flood' ? 'blue' :
                                  scenario.hazard_type === 'terrorist' ? 'orange' :
                                  scenario.hazard_type === 'chemical' ? 'purple' : 'grey'
                                }`}>
                                  {scenario.hazard_type}
                                </span>
                                {scenario.evacuation_direction && (
                                  <span className="govuk-!-margin-left-2">
                                    Direction: {scenario.evacuation_direction}
                                  </span>
                                )}
                              </p>
                            )}
                          </div>
                          <div className="govuk-grid-column-one-third">
                            <div className="govuk-panel govuk-panel--confirmation" style={{ padding: '10px', textAlign: 'center' }}>
                              <h4 className="govuk-panel__title" style={{ fontSize: '1rem', marginBottom: '5px' }}>
                                Overall Score
                              </h4>
                              <div className="govuk-panel__body" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                {((scenario.score || 0) * 100).toFixed(0)}%
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <dl className={GOVUK_CLASSES.summaryList.container}>
                          {/* Core Performance Metrics */}
                          <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Clearance Time</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              <strong>{scenario.metrics.clearance_time.toFixed(1)} minutes</strong>
                              {scenario.expected_clearance_time && scenario.expected_clearance_time !== scenario.metrics.clearance_time && (
                                <div className="govuk-body-s">
                                  Expected: {scenario.expected_clearance_time.toFixed(1)} minutes
                                </div>
                              )}
                            </dd>
                          </div>
                          {/* <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Maximum Queue Length</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              <strong>{scenario.metrics.max_queue.toLocaleString()} people</strong>
                            </dd>
                          </div> */}
                          <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Fairness Index</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              <strong>{(scenario.metrics.fairness_index * 100).toFixed(1)}%</strong>
                              <div className="govuk-body-s">Raw value: {scenario.metrics.fairness_index.toFixed(3)}</div>
                            </dd>
                          </div>
                          <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Robustness Score</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              <strong>{(scenario.metrics.robustness * 100).toFixed(1)}%</strong>
                              <div className="govuk-body-s">Raw value: {scenario.metrics.robustness.toFixed(3)}</div>
                            </dd>
                          </div>
                          
                          {/* Population and Scale Metrics */}
                          {(scenario.metrics.total_evacuated || scenario.population_affected) && (
                            <div className={GOVUK_CLASSES.summaryList.row}>
                              <dt className={GOVUK_CLASSES.summaryList.key}>Population Affected</dt>
                              <dd className={GOVUK_CLASSES.summaryList.value}>
                                <strong>
                                  {(scenario.metrics.total_evacuated || scenario.population_affected || 0).toLocaleString()} people
                                </strong>
                              </dd>
                            </div>
                          )}
                          
                          {/* Behavioral Metrics */}
                          {scenario.compliance_rate && (
                            <div className={GOVUK_CLASSES.summaryList.row}>
                              <dt className={GOVUK_CLASSES.summaryList.key}>Compliance Rate</dt>
                              <dd className={GOVUK_CLASSES.summaryList.value}>
                                <strong>{(scenario.compliance_rate * 100).toFixed(1)}%</strong>
                              </dd>
                            </div>
                          )}
                          {scenario.transport_disruption && (
                            <div className={GOVUK_CLASSES.summaryList.row}>
                              <dt className={GOVUK_CLASSES.summaryList.key}>Transport Disruption</dt>
                              <dd className={GOVUK_CLASSES.summaryList.value}>
                                <strong>{(scenario.transport_disruption * 100).toFixed(1)}%</strong>
                              </dd>
                            </div>
                          )}
                          
                          {/* Simulation Configuration */}
                          {(scenario.routes_calculated || scenario.walks_simulated) && (
                            <>
                              {scenario.routes_calculated && (
                                <div className={GOVUK_CLASSES.summaryList.row}>
                                  <dt className={GOVUK_CLASSES.summaryList.key}>Routes Calculated</dt>
                                  <dd className={GOVUK_CLASSES.summaryList.value}>
                                    {scenario.routes_calculated} optimal paths
                                  </dd>
                                </div>
                              )}
                              {scenario.walks_simulated && (
                                <div className={GOVUK_CLASSES.summaryList.row}>
                                  <dt className={GOVUK_CLASSES.summaryList.key}>Walks Simulated</dt>
                                  <dd className={GOVUK_CLASSES.summaryList.value}>
                                    {scenario.walks_simulated} random walks
                                  </dd>
                                </div>
                              )}
                            </>
                          )}
                          
                          {/* Runtime Performance */}
                          {scenario.duration_ms && (
                            <div className={GOVUK_CLASSES.summaryList.row}>
                              <dt className={GOVUK_CLASSES.summaryList.key}>Simulation Runtime</dt>
                              <dd className={GOVUK_CLASSES.summaryList.value}>
                                {(scenario.duration_ms / 1000).toFixed(2)} seconds
                              </dd>
                            </div>
                          )}
                          
                          {/* Additional Metrics (dynamic) */}
                          {Object.entries(scenario.metrics).map(([key, value]) => {
                            // Skip already displayed metrics
                            if (['clearance_time', 'fairness_index', 'robustness', 'total_evacuated'].includes(key)) {
                              return null;
                            }
                            
                            // Only show numeric values
                            if (typeof value !== 'number') return null;
                            
                            return (
                              <div key={key} className={GOVUK_CLASSES.summaryList.row}>
                                <dt className={GOVUK_CLASSES.summaryList.key}>
                                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </dt>
                                <dd className={GOVUK_CLASSES.summaryList.value}>
                                  {typeof value === 'number' ? 
                                    (value < 1 && value > 0 ? 
                                      (value * 100).toFixed(1) + '%' : 
                                      value.toLocaleString()
                                    ) : 
                                    String(value)
                                  }
                                </dd>
                              </div>
                            );
                          })}
                        </dl>
                      </div>
                    ));
                  })()}
                </div>
              )}

              {/* Queue Status Tab */}
              {activeTab === 'queue' && (
                <div className={GOVUK_CLASSES.tabs.panel}>
                  <h2 className={GOVUK_CLASSES.heading.m}>Simulation Queue Status</h2>
                  <p className={GOVUK_CLASSES.body.m}>
                    View all simulations currently in the queue, including pending and running simulations.
                  </p>
                  <SimulationQueue />
                </div>
              )}

              {/* Visualisation Tab */}
              {activeTab === 'visualisation' && (
                <div className={GOVUK_CLASSES.tabs.panel} style={{ padding: '20px' }}>
                  {/* Modern Header Section */}
                  <div style={{
                    background: '#1e40af',
                    borderRadius: '4px',
                    padding: '32px',
                    marginBottom: '24px',
                    color: 'white'
                  }}>
                    <h2 style={{
                      fontSize: '2rem',
                      fontWeight: '600',
                      margin: '0 0 12px 0'
                    }}>
                      Scenario Visualizations
                    </h2>
                    <p style={{
                      fontSize: '1.1rem',
                      margin: 0,
                      maxWidth: '600px'
                    }}>
                      Interactive maps and route visualizations powered by real OpenStreetMap data and advanced pathfinding algorithms
                    </p>
                  </div>

                  {(() => {
                    const processedScenarios = processScenarios(runResult);
                    
                    if (processedScenarios.length === 0) {
                      return (
                        <div className="govuk-inset-text">
                          <p><strong>No scenario visualizations available</strong></p>
                          <p>This run does not contain scenario data with visualizations.</p>
                          <details className="govuk-details">
                            <summary className="govuk-details__summary">
                              <span className="govuk-details__summary-text">
                                Debug Information
                              </span>
                            </summary>
                            <div className="govuk-details__text">
                              <p><strong>Run ID:</strong> {runResult.run_id}</p>
                              <p><strong>Scenario Count:</strong> {runResult.scenario_count}</p>
                              <p><strong>Available Keys:</strong> {Object.keys(runResult).join(', ')}</p>
                            </div>
                          </details>
                        </div>
                      );
                    }

                    return (
                      <>
                        {/* Modern Scenario Selector */}
                        <div style={{
                          backgroundColor: '#f3f4f6',
                          borderRadius: '4px',
                          padding: '20px',
                          marginBottom: '24px',
                          border: '1px solid #d1d5db'
                        }}>
                          <label style={{
                            display: 'block',
                            fontSize: '1.1rem',
                            fontWeight: '600',
                            color: '#1e293b',
                            marginBottom: '12px'
                          }}>
                            Select Scenario to Visualize
                          </label>
                          <select 
                            id="scenario-select"
                            value={activeScenarioId || processedScenarios[0]?.scenario_id}
                            onChange={(e) => setActiveScenarioId(e.target.value)}
                            style={{
                              width: '100%',
                              padding: '12px 16px',
                              fontSize: '1rem',
                              border: '2px solid #cbd5e1',
                              borderRadius: '8px',
                              backgroundColor: 'white',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              outline: 'none'
                            }}
                            onFocus={(e) => {
                              e.target.style.borderColor = '#3b82f6';
                              e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
                            }}
                            onBlur={(e) => {
                              e.target.style.borderColor = '#cbd5e1';
                              e.target.style.boxShadow = 'none';
                            }}
                          >
                            {processedScenarios.map((scenario) => (
                              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                                #{scenario.rank} - {scenario.scenario_name || scenario.name || scenario.scenario_id}
                                {scenario.hazard_type && ` (${scenario.hazard_type})`}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Selected Scenario Details */}
                        {(() => {
                          const selectedScenario = processedScenarios.find(s => s.scenario_id === (activeScenarioId || processedScenarios[0]?.scenario_id)) || processedScenarios[0];
                          
                          if (!selectedScenario) return null;

                          return (
                            <div className="govuk-grid-row govuk-!-margin-bottom-6">
                              <div className="govuk-grid-column-full">
                                {/* Modern Scenario Header Card */}
                                <div style={{
                                  background: selectedScenario.hazard_type === 'fire' ? '#dc2626' : 
                                             selectedScenario.hazard_type === 'flood' ? '#2563eb' :
                                             selectedScenario.hazard_type === 'terrorist' ? '#ea580c' :
                                             selectedScenario.hazard_type === 'chemical' ? '#7c3aed' : '#475569',
                                  borderRadius: '4px',
                                  padding: '24px',
                                  marginBottom: '24px',
                                  color: 'white'
                                }}>
                                  <div className="govuk-grid-row">
                                    <div className="govuk-grid-column-two-thirds">
                                      <div style={{ marginBottom: '20px' }}>
                                        <h3 style={{
                                          fontSize: '1.5rem',
                                          fontWeight: '600',
                                          color: 'white',
                                          margin: '0 0 12px 0'
                                        }}>
                                          {selectedScenario.scenario_name || selectedScenario.name || selectedScenario.scenario_id}
                                        </h3>
                                      </div>
                                      
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                                        {selectedScenario.hazard_type && (
                                          <div style={{
                                            backgroundColor: 'rgba(255,255,255,0.15)',
                                            padding: '6px 12px',
                                            borderRadius: '4px',
                                            border: '1px solid rgba(255,255,255,0.3)'
                                          }}>
                                            <span style={{ color: 'white', fontWeight: '500', fontSize: '0.9rem' }}>
                                              Type: {selectedScenario.hazard_type.toUpperCase()}
                                            </span>
                                          </div>
                                        )}
                                        {selectedScenario.evacuation_direction && (
                                          <div style={{
                                            backgroundColor: 'rgba(255,255,255,0.15)',
                                            padding: '6px 12px',
                                            borderRadius: '4px',
                                            border: '1px solid rgba(255,255,255,0.3)'
                                          }}>
                                            <span style={{ color: 'white', fontWeight: '500', fontSize: '0.9rem' }}>
                                              Direction: {selectedScenario.evacuation_direction}
                                            </span>
                                          </div>
                                        )}
                                        {selectedScenario.population_affected && (
                                          <div style={{
                                            backgroundColor: 'rgba(255,255,255,0.15)',
                                            padding: '6px 12px',
                                            borderRadius: '4px',
                                            border: '1px solid rgba(255,255,255,0.3)'
                                          }}>
                                            <span style={{ color: 'white', fontWeight: '500', fontSize: '0.9rem' }}>
                                              Population: {selectedScenario.population_affected.toLocaleString()}
                                            </span>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    
                                    <div className="govuk-grid-column-one-third">
                                      <div style={{
                                        backgroundColor: 'rgba(255,255,255,0.15)',
                                        borderRadius: '4px',
                                        padding: '20px',
                                        textAlign: 'center',
                                        border: '1px solid rgba(255,255,255,0.3)'
                                      }}>
                                        <div style={{
                                          fontSize: '0.8rem',
                                          color: 'rgba(255,255,255,0.9)',
                                          marginBottom: '8px',
                                          textTransform: 'uppercase',
                                          fontWeight: '500'
                                        }}>
                                          Performance Score
                                        </div>
                                        <div style={{
                                          fontSize: '2.5rem',
                                          fontWeight: '700',
                                          color: 'white',
                                          lineHeight: '1',
                                          marginBottom: '8px'
                                        }}>
                                          {((selectedScenario.score || 0) * 100).toFixed(0)}%
                                        </div>
                                        <div style={{
                                          fontSize: '0.8rem',
                                          color: 'rgba(255,255,255,0.9)'
                                        }}>
                                          Rank #{selectedScenario.rank} of {processedScenarios.length}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Modern Key Metrics Cards */}
                                <div className="govuk-grid-row govuk-!-margin-bottom-6" style={{ gap: '20px' }}>
                                  {[
                                    { 
                                      title: 'Clearance Time', 
                                      value: `${selectedScenario.metrics.clearance_time.toFixed(1)} min`,
                                      color: '#10b981',
                                      bgColor: '#ecfdf5',
                                      borderColor: '#a7f3d0'
                                    },
                                    { 
                                      title: 'Fairness', 
                                      value: `${(selectedScenario.metrics.fairness_index * 100).toFixed(0)}%`,
                                      color: '#3b82f6',
                                      bgColor: '#eff6ff',
                                      borderColor: '#bfdbfe'
                                    },
                                    { 
                                      title: 'Robustness', 
                                      value: `${(selectedScenario.metrics.robustness * 100).toFixed(0)}%`,
                                      color: '#8b5cf6',
                                      bgColor: '#f5f3ff',
                                      borderColor: '#ddd6fe'
                                    }
                                  ].map((metric, index) => (
                                    <div key={index} className="govuk-grid-column-one-quarter">
                                      <div style={{
                                        backgroundColor: '#f9fafb',
                                        border: `2px solid ${metric.color}`,
                                        borderRadius: '4px',
                                        padding: '20px',
                                        textAlign: 'center'
                                      }}>
                                        <h4 style={{ 
                                          fontSize: '0.8rem',
                                          color: '#6b7280',
                                          marginBottom: '8px',
                                          textTransform: 'uppercase',
                                          fontWeight: '600'
                                        }}>
                                          {metric.title}
                                        </h4>
                                        <div style={{ 
                                          fontSize: '1.8rem', 
                                          fontWeight: '700', 
                                          color: metric.color,
                                          lineHeight: '1'
                                        }}>
                                          {metric.value}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>

                                {/* Visualization Content */}
                                <div className="govuk-grid-row">
                                  <div className="govuk-grid-column-full">
                                    <h3 className="govuk-heading-m">Interactive Map & Route Visualization</h3>
                                    
                                    {/* Interactive Map Display */}
                                    <ScenarioVisualizationMap 
                                      scenario={selectedScenario}
                                      runResult={runResult}
                                      city={getTargetCityFromResults(runResult)}
                                    />
                                  </div>
                                </div>

                                {/* Route Details */}
                                {selectedScenario.routes_calculated && (
                                  <div className="govuk-grid-row govuk-!-margin-top-4">
                                    <div className="govuk-grid-column-full">
                                      <h3 className="govuk-heading-s">Route Analysis</h3>
                                      <dl className="govuk-summary-list">
                                        <div className="govuk-summary-list__row">
                                          <dt className="govuk-summary-list__key">Optimal Routes Calculated</dt>
                                          <dd className="govuk-summary-list__value">{selectedScenario.routes_calculated}</dd>
                                        </div>
                                        {selectedScenario.walks_simulated && (
                                          <div className="govuk-summary-list__row">
                                            <dt className="govuk-summary-list__key">Random Walks Simulated</dt>
                                            <dd className="govuk-summary-list__value">{selectedScenario.walks_simulated}</dd>
                                          </div>
                                        )}
                                        {selectedScenario.compliance_rate && (
                                          <div className="govuk-summary-list__row">
                                            <dt className="govuk-summary-list__key">Expected Compliance Rate</dt>
                                            <dd className="govuk-summary-list__value">{(selectedScenario.compliance_rate * 100).toFixed(1)}%</dd>
                                          </div>
                                        )}
                                        {selectedScenario.transport_disruption && (
                                          <div className="govuk-summary-list__row">
                                            <dt className="govuk-summary-list__key">Transport Disruption Level</dt>
                                            <dd className="govuk-summary-list__value">{(selectedScenario.transport_disruption * 100).toFixed(1)}%</dd>
                                          </div>
                                        )}
                                      </dl>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Scenario Comparison */}
                        {processedScenarios.length > 1 && (() => {
                          // Sort scenarios by performance score (descending) for consistent ordering
                          const sortedScenarios = [...processedScenarios].sort((a, b) => {
                            const scoreA = (a.score || a.metrics?.fairness_index || 0);
                            const scoreB = (b.score || b.metrics?.fairness_index || 0);
                            return scoreB - scoreA;
                          });

                          return (
                            <div className="govuk-grid-row govuk-!-margin-top-6" style={{ border: 'none', outline: 'none' }}>
                              <div className="govuk-grid-column-full" style={{ border: 'none', outline: 'none' }}>
                                <h3 className="govuk-heading-m">Scenario Comparison</h3>
                                <div className="govuk-grid-row" style={{ border: 'none', outline: 'none' }}>
                                  <div className="govuk-grid-column-one-half" style={{ border: 'none', outline: 'none' }}>
                                    <BarChart
                                      title="Clearance Time Comparison"
                                      data={sortedScenarios.map((s, index) => {
                                        const clearanceTime = s.metrics?.clearance_time || 0;
                                        return {
                                          label: (s.scenario_name || s.name || s.scenario_id).substring(0, 20),
                                          value: clearanceTime,
                                          color: index === 0 ? '#00703c' : '#1d70b8' // Best performer in green
                                        };
                                      })}
                                      unit=" min"
                                    />
                                  </div>
                                  <div className="govuk-grid-column-one-half" style={{ border: 'none', outline: 'none' }}>
                                    <BarChart
                                      title="Performance Score Comparison"
                                      data={sortedScenarios.map((s, index) => ({
                                        label: (s.scenario_name || s.name || s.scenario_id).substring(0, 20),
                                        value: Math.round((s.score || s.metrics?.fairness_index || 0) * 100),
                                        color: index === 0 ? '#00703c' : '#1d70b8' // Best performer in green
                                      }))}
                                      unit="%"
                                    />
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })()}
                      </>
                    );
                  })()}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
              <h2 className={GOVUK_CLASSES.heading.m}>Actions</h2>
              <div className="govuk-button-group" style={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                gap: '0.5rem'
              }}>
                <Link to="/plan" className={GOVUK_CLASSES.button.secondary} style={{ 
                  flex: '1 1 auto', 
                  minWidth: '200px',
                  marginBottom: '0.5rem'
                }}>
                  Run New Planning Session
                </Link>
                <button className={GOVUK_CLASSES.button.secondary} style={{ 
                  flex: '1 1 auto', 
                  minWidth: '150px',
                  marginBottom: '0.5rem'
                }}>
                  Export Results
                </button>
                <button className={GOVUK_CLASSES.button.secondary} style={{ 
                  flex: '1 1 auto', 
                  minWidth: '180px',
                  marginBottom: '0.5rem'
                }}>
                  Download Decision Memo
                </button>
              </div>
            </div>
          </>
        )}

        {/* No Results State */}
        {!runResult && !loading && !error && (
          <div className={GOVUK_CLASSES.insetText}>
            <p>No evacuation planning results available. <Link to="/plan" className="govuk-link">Start a new planning run</Link> to see results here.</p>
          </div>
        )}

      </div>

      {/* Coordinated Response Draft Modal */}
      {showResponseDraft && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '4px',
            maxWidth: '800px',
            width: '100%',
            maxHeight: '90vh',
            overflow: 'auto',
            padding: '30px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 className={GOVUK_CLASSES.heading.l}>Coordinated Emergency Response Draft</h2>
              <button
                onClick={() => {
                  setShowResponseDraft(false);
                  setResponseApproved(false);
                  setResponseDraft('');
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#505a5f'
                }}
              >
                ×
              </button>
            </div>

            {generatingResponse ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  border: '4px solid #f3f2f1',
                  borderTop: '4px solid #1d70b8',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto 20px'
                }} />
                <p className={GOVUK_CLASSES.body.m}>Generating coordinated response using AI analysis...</p>
              </div>
            ) : (
              <>
                <div className="govuk-warning-text">
                  <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                  <strong className="govuk-warning-text__text">
                    <span className="govuk-warning-text__assistive">Warning: </span>
                    This is an AI-generated draft requiring human review and approval
                  </strong>
                </div>

                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="response-draft">
                    Draft Coordinated Response
                  </label>
                  <textarea
                    className={GOVUK_CLASSES.form.textarea}
                    id="response-draft"
                    rows={20}
                    value={responseDraft}
                    onChange={(e) => setResponseDraft(e.target.value)}
                    style={{ fontFamily: 'monospace', fontSize: '14px' }}
                  />
                </div>

                <div className="govuk-checkboxes">
                  <div className="govuk-checkboxes__item">
                    <input
                      className="govuk-checkboxes__input"
                      id="approve-response"
                      type="checkbox"
                      checked={responseApproved}
                      onChange={(e) => setResponseApproved(e.target.checked)}
                    />
                    <label className="govuk-checkboxes__label" htmlFor="approve-response">
                      I have reviewed this response and approve it for distribution
                    </label>
                  </div>
                </div>

                <div className="govuk-button-group" style={{ marginTop: '30px' }}>
                  <button
                    className={`govuk-button ${!responseApproved ? 'govuk-button--disabled' : ''}`}
                    disabled={!responseApproved || sendingAlert}
                    onClick={async () => {
                      if (responseApproved && responseDraft.trim()) {
                        setSendingAlert(true);
                        try {
                          const response = await fetch(`${API_CONFIG.baseUrl}/api/coordination/send-response`, {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              response_text: responseDraft,
                              run_id: runResult?.run_id,
                              approved_by: 'Human Operator',
                              timestamp: new Date().toISOString()
                            })
                          });
                          
                          if (response.ok) {
                            setAlertStatus({ type: 'success', message: 'Coordinated response sent successfully' });
                            setShowResponseDraft(false);
                          } else {
                            setAlertStatus({ type: 'error', message: 'Failed to send coordinated response' });
                          }
                        } catch (error) {
                          setAlertStatus({ type: 'error', message: 'Failed to send coordinated response' });
                        } finally {
                          setSendingAlert(false);
                        }
                      }
                    }}
                  >
                    {sendingAlert ? 'Sending Response...' : 'Send Coordinated Response'}
                  </button>
                  
                  <button
                    className="govuk-button govuk-button--secondary"
                    onClick={() => {
                      setShowResponseDraft(false);
                      setResponseApproved(false);
                      setResponseDraft('');
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsGovUK;
