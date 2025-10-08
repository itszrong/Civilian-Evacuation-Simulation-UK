/**
 * Plan & Run component for Civilian Evacuation Planning Tool
 * GOV.UK Design System implementation
 * Form for user intent and real-time streaming of evacuation planning runs
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { notificationStore } from './govuk/Notification';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import AgenticPlannerPanel from './AgenticPlannerPanel';

interface UserIntent {
  objective: string;
  city: string;
  constraints: {
    max_scenarios: number;
    compute_budget_minutes: number;
    must_protect_pois: string[];
  };
  hypotheses: string[];
  preferences: {
    fairness_weight: number;
    clearance_weight: number;
    robustness_weight: number;
  };
  freshness_days: number;
  tiers: string[];
}

interface RunEvent {
  event: string;
  data: any;
}

const PlanAndRunGovUK: React.FC = () => {
  const [selectedCity, setSelectedCity] = useState('westminster');
  const [availableCities, setAvailableCities] = useState<{value: string, label: string}[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);
  const [intent, setIntent] = useState<UserIntent>({
    objective: 'minimise_clearance_time_and_improve_fairness',
    city: 'westminster',
    constraints: {
      max_scenarios: 8,
      compute_budget_minutes: 3,
      must_protect_pois: ['StThomasHospital', 'KingsCollegeHospital']
    },
    hypotheses: ['Westminster cordon 2h', 'Two Thames bridges closed'],
    preferences: {
      fairness_weight: 0.35,
      clearance_weight: 0.5,
      robustness_weight: 0.15
    },
    freshness_days: 7,
    tiers: ['gov_primary']
  });

  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [runId, setRunId] = useState<string>('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activeSimulations, setActiveSimulations] = useState<Array<{
    run_id: string;
    city: string;
    status: string;
    started_at: string;
  }>>([]);
  const [showAgenticPlanner, setShowAgenticPlanner] = useState(false);
  const [agenticScenario, setAgenticScenario] = useState<any>(null);
  const [agenticMetrics, setAgenticMetrics] = useState<any>(null);

  // Sync selectedCity with intent.city
  useEffect(() => {
    setIntent(prev => ({
      ...prev,
      city: selectedCity
    }));
  }, [selectedCity]);

  // Fetch available cities from API
  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.cities}`);
        if (response.ok) {
          const data = await response.json();
          const cityOptions = data.cities.map((city: string) => ({
            value: city,
            label: city.charAt(0).toUpperCase() + city.slice(1).replace(/_/g, ' ')
          }));
          setAvailableCities(cityOptions);
          if (data.default && !cityOptions.some((c: any) => c.value === selectedCity)) {
            setSelectedCity(data.default);
          }
        }
      } catch (error) {
        console.error('Failed to fetch cities:', error);
        setAvailableCities([
          { value: 'westminster', label: 'Westminster' },
          { value: 'kensington and chelsea', label: 'Kensington and Chelsea' }
        ]);
      } finally {
        setLoadingCities(false);
      }
    };

    fetchCities();
  }, [selectedCity]);

  const weightSum = intent.preferences.fairness_weight +
                    intent.preferences.clearance_weight +
                    intent.preferences.robustness_weight;

  const handleStartRun = async () => {
    if (isRunning) return;

    // Simple direct simulation that waits for results
    setIsRunning(true);
    setProgress(10);
    setCurrentPhase(`Running ${selectedCity} evacuation simulation...`);

    try {
      // Use visualisation endpoint with create_complete to get full run with scenarios
      const url = `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(selectedCity)}?create_complete=true`;
      console.log(`🌍 ${selectedCity} simulation starting:`, url);

      setProgress(30);
      setCurrentPhase(`Generating evacuation routes...`);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      console.log(`🌍 Response status:`, response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to generate simulation');
      }

      setProgress(70);
      setCurrentPhase(`Processing simulation results...`);

      const result = await response.json();
      console.log(`🌍 Simulation complete:`, Object.keys(result));

      // Extract run_id from the result
      const resultRunId = result.run_id;
      console.log(`🌍 Got run_id:`, resultRunId);

      setProgress(100);
      setCurrentPhase(`${selectedCity} simulation complete!`);
      setRunId(resultRunId);

      notificationStore.show({
        title: 'Simulation Complete',
        message: `${selectedCity} evacuation analysis generated successfully`,
        type: 'success'
      });

      // Wait a moment then redirect to results with run_id
      setTimeout(() => {
        if (resultRunId) {
          window.location.href = `/results/${resultRunId}?city=${selectedCity}`;
        } else {
          window.location.href = `/results?city=${selectedCity}`;
        }
      }, 1500);

    } catch (error) {
      console.error(`🌍 ${selectedCity} simulation failed:`, error);
      notificationStore.show({
        title: 'Simulation Failed',
        message: error instanceof Error ? error.message : 'Unknown error',
        type: 'error'
      });
      setProgress(0);
      setCurrentPhase('Ready');
    } finally {
      setIsRunning(false);
    }
  };

  // Start full evacuation planning run with intent
  const handleStartEvacuationRun = async () => {
    if (isRunning) return;

    setIsRunning(true);
    setProgress(10);
    setCurrentPhase('Starting evacuation planning run...');
    setEvents([]);

    try {
      const url = `${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.runs}`;
      console.log(`🚀 Starting evacuation run:`, url);

      setProgress(20);
      setCurrentPhase('Connecting to planning service...');

      // The /api/runs POST endpoint returns Server-Sent Events (SSE) stream
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          intent: intent
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to start evacuation run');
      }

      // Consume the SSE stream properly
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let completedRunId: string | null = null;

      if (!reader) {
        throw new Error('No response body');
      }

      setProgress(30);
      setCurrentPhase('Planning scenarios...');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('event:')) {
            const eventType = line.substring(6).trim();
            console.log('📡 SSE event:', eventType);
          } else if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.substring(5).trim());
              console.log('📡 SSE data:', data);

              // Add to events log
              setEvents(prev => [...prev, { event: 'data', data }]);

              // Update progress based on event data
              if (data.run_id && !completedRunId) {
                setRunId(data.run_id);
                completedRunId = data.run_id;
              }

              if (data.status === 'started') {
                setProgress(35);
                setCurrentPhase('Run started...');
              } else if (data.message?.includes('Planning') || data.message?.includes('scenarios')) {
                setProgress(45);
                setCurrentPhase('Generating scenarios...');
              } else if (data.message?.includes('simulation') || data.message?.includes('Running')) {
                setProgress(60);
                setCurrentPhase('Running city simulation...');
              } else if (data.ranking || data.message?.includes('Ranking')) {
                setProgress(80);
                setCurrentPhase('Ranking scenarios...');
              } else if (data.answer || data.message?.includes('Explain')) {
                setProgress(90);
                setCurrentPhase('Generating explanation...');
              } else if (data.status === 'completed') {
                setProgress(100);
                setCurrentPhase('Evacuation planning complete!');
                
                notificationStore.show({
                  title: 'Run Complete',
                  message: `AI evacuation planning workflow completed for ${selectedCity}`,
                  type: 'success'
                });

                // Redirect to results page
                setTimeout(() => {
                  if (completedRunId) {
                    window.location.href = `/results/${completedRunId}?city=${selectedCity}`;
                  } else {
                    window.location.href = `/results?city=${selectedCity}`;
                  }
                }, 1500);
                return;
              }
            } catch (e) {
              // Ignore parsing errors for non-JSON SSE lines
              console.log('⚠️ Could not parse SSE line:', line);
            }
          }
        }
      }

    } catch (error) {
      console.error(`🚀 Evacuation run failed:`, error);
      notificationStore.show({
        title: 'Run Failed',
        message: error instanceof Error ? error.message : 'Unknown error',
        type: 'error'
      });
      setProgress(0);
      setCurrentPhase('Ready');
    } finally {
      setIsRunning(false);
    }
  };

  // Agentic planner handlers
  const handleScenarioGenerated = (scenario: any) => {
    setAgenticScenario(scenario);
    notificationStore.show({
      title: 'Scenario Generated',
      message: `AI generated scenario: ${scenario.specification?.name || 'Custom scenario'}`,
      type: 'success'
    });
  };

  const handleMetricsGenerated = (metrics: any) => {
    setAgenticMetrics(metrics);
    notificationStore.show({
      title: 'Metrics Generated',
      message: `AI generated ${Object.keys(metrics.specification?.metrics || {}).length} custom metrics`,
      type: 'success'
    });
  };

  const handleAnalysisPackageCreated = (packageData: any) => {
    // Check if this is a run result with real simulation data
    if (packageData.run_id && packageData.scenarios && packageData.has_real_metrics) {
      // This is from the "Generate Realistic Scenarios" button - navigate to results
      notificationStore.show({
        title: 'Real Simulation Complete',
        message: `Generated ${packageData.scenario_count} scenarios with real Westminster network data`,
        type: 'success'
      });
      
      // Navigate to results page with the real run data
      setTimeout(() => {
        window.location.href = `/results/${packageData.run_id}`;
      }, 1500);
    } else {
      // This is from the "Create Analysis Package" button - store for later use
      setAgenticScenario(packageData.scenario);
      setAgenticMetrics(packageData.metrics);
      notificationStore.show({
        title: 'Analysis Package Created',
        message: `Complete analysis package generated with scenario and optimized metrics`,
        type: 'success'
      });
    }
  };

  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>
        
        {/* Page Header */}
        <span className="govuk-caption-xl">Emergency Planning</span>
        <h1 className={GOVUK_CLASSES.heading.xl}>Evacuation Simulation</h1>
        <p className={GOVUK_CLASSES.body.lead}>
          Run comprehensive evacuation simulations with A* routing and biased random walk analysis
        </p>

        {/* City Selection */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <fieldset className={GOVUK_CLASSES.form.fieldset}>
            <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.m}`}>
              Select City
            </legend>

            <div className={GOVUK_CLASSES.form.group}>
              <select
                className={GOVUK_CLASSES.form.select}
                id="city-select"
                name="city"
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                disabled={loadingCities || isRunning}
              >
                {availableCities.map(city => (
                  <option key={city.value} value={city.value}>
                    {city.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={GOVUK_CLASSES.insetText}>
              All cities run comprehensive simulation suite:
              <ul>
                <li>🔵 A* optimal routing from center to boundary</li>
                <li>🔴 Biased random walk paths with density analysis</li>
                <li>🟠 Exit point heatmap visualisation</li>
              </ul>
            </div>
          </fieldset>
        </div>

        {/* Hide all configuration options */}
        <div style={{display: 'none'}}>
        {/* Constraints */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <fieldset className={GOVUK_CLASSES.form.fieldset}>
            <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.m}`}>
              Planning Constraints
            </legend>
            
            <div className={GOVUK_CLASSES.gridRow}>
              <div className={GOVUK_CLASSES.gridColumn.half}>
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="max-scenarios">
                    Maximum scenarios
                  </label>
                  <div className="govuk-hint">
                    Number of evacuation scenarios to generate (1-20)
                  </div>
                  <input
                    className={GOVUK_CLASSES.form.input}
                    id="max-scenarios"
                    name="max-scenarios"
                    type="number"
                    min="1"
                    max="20"
                    value={intent.constraints.max_scenarios}
                    onChange={(e) => setIntent(prev => ({
                      ...prev,
                      constraints: {
                        ...prev.constraints,
                        max_scenarios: parseInt(e.target.value) || 8
                      }
                    }))}
                    disabled={isRunning}
                  />
                </div>
              </div>
              
              <div className={GOVUK_CLASSES.gridColumn.half}>
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="compute-budget">
                    Compute budget (minutes)
                  </label>
                  <div className="govuk-hint">
                    Maximum time for computation (1-15 minutes)
                  </div>
                  <input
                    className={GOVUK_CLASSES.form.input}
                    id="compute-budget"
                    name="compute-budget"
                    type="number"
                    min="1"
                    max="15"
                    value={intent.constraints.compute_budget_minutes}
                    onChange={(e) => setIntent(prev => ({
                      ...prev,
                      constraints: {
                        ...prev.constraints,
                        compute_budget_minutes: parseInt(e.target.value) || 3
                      }
                    }))}
                    disabled={isRunning}
                  />
                </div>
              </div>
            </div>

            <div className={GOVUK_CLASSES.form.group}>
              <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="hypotheses">
                Planning hypotheses
              </label>
              <div className="govuk-hint">
                Enter key assumptions or scenarios to test, one per line
              </div>
              <textarea
                className={GOVUK_CLASSES.form.textarea}
                id="hypotheses"
                name="hypotheses"
                rows={3}
                value={intent.hypotheses.join('\n')}
                onChange={(e) => setIntent(prev => ({
                  ...prev,
                  hypotheses: e.target.value.split('\n').filter(h => h.trim())
                }))}
                disabled={isRunning}
              />
            </div>
          </fieldset>
        </div>

        {/* Optimization Preferences */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <fieldset className={GOVUK_CLASSES.form.fieldset}>
            <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.m}`}>
              Optimization Preferences
            </legend>
            <div className="govuk-hint">
              Set the relative importance of different factors. Weights must sum to 1.0
            </div>
            
            <div className={GOVUK_CLASSES.gridRow}>
              <div className={GOVUK_CLASSES.gridColumn.oneThird}>
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="clearance-weight">
                    Clearance time weight
                  </label>
                  <input
                    className={GOVUK_CLASSES.form.input}
                    id="clearance-weight"
                    name="clearance-weight"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={intent.preferences.clearance_weight}
                    onChange={(e) => setIntent(prev => ({
                      ...prev,
                      preferences: {
                        ...prev.preferences,
                        clearance_weight: parseFloat(e.target.value) || 0.5
                      }
                    }))}
                    disabled={isRunning}
                  />
                </div>
              </div>
              
              <div className={GOVUK_CLASSES.gridColumn.oneThird}>
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="fairness-weight">
                    Fairness weight
                  </label>
                  <input
                    className={GOVUK_CLASSES.form.input}
                    id="fairness-weight"
                    name="fairness-weight"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={intent.preferences.fairness_weight}
                    onChange={(e) => setIntent(prev => ({
                      ...prev,
                      preferences: {
                        ...prev.preferences,
                        fairness_weight: parseFloat(e.target.value) || 0.35
                      }
                    }))}
                    disabled={isRunning}
                  />
                </div>
              </div>
              
              <div className={GOVUK_CLASSES.gridColumn.oneThird}>
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="robustness-weight">
                    Robustness weight
                  </label>
                  <input
                    className={GOVUK_CLASSES.form.input}
                    id="robustness-weight"
                    name="robustness-weight"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={intent.preferences.robustness_weight}
                    onChange={(e) => setIntent(prev => ({
                      ...prev,
                      preferences: {
                        ...prev.preferences,
                        robustness_weight: parseFloat(e.target.value) || 0.15
                      }
                    }))}
                    disabled={isRunning}
                  />
                </div>
              </div>
            </div>

            {/* Weight validation */}
            <div className={`govuk-inset-text ${Math.abs(weightSum - 1.0) > 0.01 ? 'govuk-error-message' : ''}`}>
              <span className={GOVUK_CLASSES.font.weightBold}>
                Current weight sum: {weightSum.toFixed(2)}
              </span>
              {Math.abs(weightSum - 1.0) > 0.01 && (
                <span className="govuk-error-message"> - Weights must sum to 1.0</span>
              )}
            </div>
          </fieldset>
        </div>

        {/* Advanced Options */}
        <details className={`${GOVUK_CLASSES.details.container} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <summary className={GOVUK_CLASSES.details.summary}>
            <span className={GOVUK_CLASSES.details.text}>Advanced options</span>
          </summary>
          <div className={GOVUK_CLASSES.details.text}>
            <div className={GOVUK_CLASSES.form.group}>
              <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="protected-pois">
                Protected points of interest
              </label>
              <div className="govuk-hint">
                Comma-separated list of locations that must remain accessible
              </div>
              <input
                className={GOVUK_CLASSES.form.input}
                id="protected-pois"
                name="protected-pois"
                type="text"
                value={intent.constraints.must_protect_pois.join(', ')}
                onChange={(e) => setIntent(prev => ({
                  ...prev,
                  constraints: {
                    ...prev.constraints,
                    must_protect_pois: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                  }
                }))}
                disabled={isRunning}
              />
            </div>
          </div>
        </details>
        </div>

        {/* Agentic Planning */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <div className="govuk-inset-text">
            <h3 className={GOVUK_CLASSES.heading.s}>AI-Powered Planning</h3>
            <p className="govuk-body-s">
              Use natural language to generate custom scenarios and metrics. 
              Describe what you want to test and the AI will create the complete analysis setup.
            </p>
            <button
              className={`${GOVUK_CLASSES.button.secondary} govuk-!-margin-right-3`}
              onClick={() => setShowAgenticPlanner(true)}
              disabled={isRunning}
            >
Open AI Planner
            </button>
            {agenticScenario && (
              <span className="govuk-tag govuk-tag--green">
                Scenario: {agenticScenario.specification?.name || 'Generated'}
              </span>
            )}
            {agenticMetrics && (
              <span className="govuk-tag govuk-tag--blue govuk-!-margin-left-2">
                Metrics: {Object.keys(agenticMetrics.specification?.metrics || {}).length} generated
              </span>
            )}
          </div>
        </div>

        {/* Run Controls */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <div className="govuk-button-group">
            <button
              className={`${GOVUK_CLASSES.button.start} ${isRunning ? GOVUK_CLASSES.button.disabled : ''}`}
              onClick={handleStartEvacuationRun}
              disabled={isRunning}
              data-module="govuk-button"
            >
              {isRunning ? 'Running evacuation planning...' : 'Start Evacuation Planning Run'}
              <svg 
                className="govuk-button__start-icon" 
                xmlns="http://www.w3.org/2000/svg" 
                width="17.5" 
                height="19" 
                viewBox="0 0 33 40" 
                aria-hidden="true" 
                focusable="false"
              >
                <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
              </svg>
            </button>
            
            <button
              className={`${GOVUK_CLASSES.button.secondary} ${isRunning ? GOVUK_CLASSES.button.disabled : ''}`}
              onClick={handleStartRun}
              disabled={isRunning}
            >
              {isRunning ? 'Running...' : 'Quick Simulation Only'}
            </button>
          </div>
        </div>

        {/* Live Results */}
        {(isRunning || events.length > 0) && (
          <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
            <h2 className={GOVUK_CLASSES.heading.m}>Live Planning Status</h2>
            
            {runId && (
              <p className={GOVUK_CLASSES.body.s}>
                <span className={GOVUK_CLASSES.font.weightBold}>Run ID:</span> 
                <code className="govuk-!-font-family-monospace">{runId}</code>
              </p>
            )}

            <div className={GOVUK_CLASSES.form.group}>
              <div className="govuk-progress-bar" style={{ marginBottom: '15px' }}>
                <div 
                  className="govuk-progress-bar__fill" 
                  style={{ 
                    width: `${progress}%`,
                    height: '20px',
                    backgroundColor: '#1d70b8',
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>
              <p className={GOVUK_CLASSES.body.s}>
                <span className={GOVUK_CLASSES.font.weightBold}>{currentPhase}</span> ({progress}%)
              </p>
            </div>

            {events.length > 0 && (
              <details className={GOVUK_CLASSES.details.container}>
                <summary className={GOVUK_CLASSES.details.summary}>
                  <span className={GOVUK_CLASSES.details.text}>
                    View event stream ({events.length} events)
                  </span>
                </summary>
                <div className={GOVUK_CLASSES.details.text}>
                  <div style={{ maxHeight: '300px', overflow: 'auto', border: '1px solid #b1b4b6', padding: '10px' }}>
                    {events.map((event, index) => (
                      <div key={index} style={{ marginBottom: '10px', padding: '5px', backgroundColor: '#f3f2f1' }}>
                        <div>
                          <span className={`${GOVUK_CLASSES.tag.blue} ${GOVUK_CLASSES.spacing.marginBottom[1]}`}>
                            {event.event}
                          </span>
                        </div>
                        <pre className="govuk-!-font-family-monospace govuk-!-font-size-14">
                          {JSON.stringify(event.data, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              </details>
            )}
          </div>
        )}

        {/* Agentic Planner Panel */}
        <AgenticPlannerPanel
          isOpen={showAgenticPlanner}
          onClose={() => setShowAgenticPlanner(false)}
          city={selectedCity}
          onScenarioGenerated={handleScenarioGenerated}
          onMetricsGenerated={handleMetricsGenerated}
          onAnalysisPackageCreated={handleAnalysisPackageCreated}
        />
      </div>
    </div>
  );
};

export default PlanAndRunGovUK;
