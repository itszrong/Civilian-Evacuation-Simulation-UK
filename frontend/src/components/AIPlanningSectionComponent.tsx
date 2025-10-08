/**
 * AI Planning Section - Borough-aware intelligent planning
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { BoroughContext, BoroughContextService } from '../services/boroughContextService';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';

interface AIPlanningSectionProps {
  borough: string;
  context: BoroughContext | null;
  onPlanGenerated: (plan: any) => void;
}

interface AISimulationRunnerProps {
  borough: string;
  context: BoroughContext | null;
  scenario: string;
  metrics: string[];
  onComplete: (results: any) => void;
}

const AISimulationRunner: React.FC<AISimulationRunnerProps> = ({
  borough,
  context,
  scenario,
  metrics,
  onComplete
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState('Initializing...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    runAISimulation();
  }, []);

  const runAISimulation = async () => {
    setIsRunning(true);
    setError(null);
    
    try {
      setCurrentPhase('Generating AI scenario...');
      setProgress(20);

      const contextPrompt = context ? BoroughContextService.generateAIPromptContext(context) : '';
      
      setCurrentPhase('Generating evacuation routes...');
      setProgress(40);

      // Use the same working endpoint as "Quick Simulation Only" button
      // This endpoint returns JSON directly (not SSE)
      const url = `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(borough)}?create_complete=true`;
      console.log(`🤖 AI simulation using endpoint:`, url);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to start AI simulation' }));
        throw new Error(errorData.detail || 'Failed to start AI simulation');
      }

      setProgress(70);
      setCurrentPhase('Processing simulation results...');

      const result = await response.json();
      console.log(`🤖 AI Simulation complete:`, Object.keys(result));

      // Extract run_id from the result
      const resultRunId = result.run_id;
      console.log(`🤖 Got run_id:`, resultRunId);

      setProgress(100);
      setCurrentPhase('Simulation complete!');
      
      // Notify completion
      onComplete({ 
        status: 'completed',
        run_id: resultRunId,
        borough: borough,
        scenario: scenario
      });

    } catch (error) {
      console.error('AI simulation failed:', error);
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
    } finally {
      setIsRunning(false);
    }
  };

  const pollSimulationStatus = async (runId: string) => {
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}/api/runs/${runId}/status`);
        if (response.ok) {
          const status = await response.json();
          
          if (status.status === 'completed') {
            setCurrentPhase('Simulation complete!');
            setProgress(100);
            onComplete({ run_id: runId, ...status });
            return;
          } else if (status.status === 'failed') {
            throw new Error('Simulation failed');
          }
          
          // Update progress based on status
          const progressMap: Record<string, number> = {
            'queued': 10,
            'running': 40,
            'analyzing': 70,
            'finalizing': 90
          };
          
          setProgress(progressMap[status.status] || 50);
          setCurrentPhase(`Status: ${status.status}`);
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          throw new Error('Simulation timeout');
        }
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Polling failed');
      }
    };

    poll();
  };

  return (
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-full">
        <h2 className="govuk-heading-l">Running AI Simulation</h2>
        
        {error ? (
          <div className="govuk-error-summary" role="alert">
            <h2 className="govuk-error-summary__title">There is a problem</h2>
            <div className="govuk-error-summary__body">
              <p>{error}</p>
              <button 
                className="govuk-button govuk-button--secondary"
                onClick={() => window.location.reload()}
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="govuk-!-margin-bottom-6">
              <h3 className="govuk-heading-s">Progress</h3>
              <div className="govuk-progress-bar" style={{ width: '100%', height: '20px', backgroundColor: '#f3f2f1', borderRadius: '4px' }}>
                <div 
                  className="govuk-progress-bar__fill" 
                  style={{ 
                    width: `${progress}%`, 
                    height: '100%', 
                    backgroundColor: '#00703c', 
                    borderRadius: '4px',
                    transition: 'width 0.3s ease'
                  }}
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
              <p className="govuk-body-s govuk-!-margin-top-2">
                {currentPhase} ({progress}%)
              </p>
            </div>

            <div className="govuk-inset-text">
              <h4 className="govuk-heading-s">AI is generating:</h4>
              <ul className="govuk-list govuk-list--bullet">
                <li>Borough-specific evacuation scenario for {context?.name}</li>
                <li>Custom metrics tailored to your planning goals</li>
                <li>Framework-compliant parameters and constraints</li>
                <li>Intelligent analysis with explanations</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const AIPlanningSectionComponent: React.FC<AIPlanningSectionProps> = ({
  borough,
  context,
  onPlanGenerated
}) => {
  const [planningStep, setPlanningStep] = useState<'intent' | 'customize' | 'generate' | 'results'>('intent');
  const [userIntent, setUserIntent] = useState('');
  const [suggestedScenarios, setSuggestedScenarios] = useState<string[]>([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [customMetrics, setCustomMetrics] = useState<string[]>([]);
  const [isGeneratingRecommendations, setIsGeneratingRecommendations] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulationResults, setSimulationResults] = useState<any>(null);

  useEffect(() => {
    if (context) {
      generateBoroughSpecificSuggestions();
    }
  }, [context]);

  const generateBoroughSpecificSuggestions = () => {
    if (!context) return;
    const suggestions = BoroughContextService.generateBoroughSpecificSuggestions(context);
    setSuggestedScenarios(suggestions);
  };

  const handleIntentSubmission = async () => {
    if (!userIntent.trim()) return;

    setIsGeneratingRecommendations(true);
    setError(null);
    setPlanningStep('customize');
    
    try {
      await generateAIRecommendations();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to generate recommendations');
      setPlanningStep('intent');
    } finally {
      setIsGeneratingRecommendations(false);
    }
  };

  const generateAIRecommendations = async () => {
    if (!context) return;

    try {
      const contextPrompt = BoroughContextService.generateAIPromptContext(context);
      
      // Generate scenario
      const scenarioResponse = await fetch(`${API_CONFIG.baseUrl}/api/agentic/scenarios/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_intent: userIntent,
          city_context: `${context.name}, London`,
          constraints: contextPrompt,
          use_framework: true
        })
      });

      // Generate metrics
      const metricsResponse = await fetch(`${API_CONFIG.baseUrl}/api/agentic/metrics/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_goal: userIntent,
          context: contextPrompt,
          run_id: null
        })
      });

      if (!scenarioResponse.ok || !metricsResponse.ok) {
        throw new Error('Failed to generate AI recommendations');
      }

      const scenarioData = await scenarioResponse.json();
      const metricsData = await metricsResponse.json();

      // Update UI with AI recommendations
      setSelectedScenario(scenarioData.specification?.name || 'AI Generated Scenario');
      setCustomMetrics(Object.keys(metricsData.specification?.metrics || {}));

    } catch (error) {
      console.error('Failed to generate AI recommendations:', error);
      throw error;
    }
  };

  return (
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-full">
        
        {/* Step 1: Intent Capture */}
        {planningStep === 'intent' && (
          <div className="govuk-form-group">
            <h2 className="govuk-heading-l">Describe Your Planning Goal</h2>
            
            {/* Borough context display */}
            {context && (
              <div className="govuk-inset-text">
                <h3 className="govuk-heading-s">Borough Context: {context.name}</h3>
                <ul className="govuk-list govuk-list--bullet">
                  <li>Population: {context.demographics.population.toLocaleString()}</li>
                  <li>Key risks: {context.riskProfile.floodRisk} flood risk, {context.riskProfile.terroristThreat} terrorist threat</li>
                  <li>Major assets: {context.keyAssets.slice(0, 3).join(', ')}</li>
                  <li>Transport hubs: {context.infrastructure.transportHubs.slice(0, 3).join(', ')}</li>
                </ul>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="govuk-error-summary" role="alert">
                <h2 className="govuk-error-summary__title">There is a problem</h2>
                <div className="govuk-error-summary__body">
                  <p>{error}</p>
                </div>
              </div>
            )}

            {/* Suggested scenarios */}
            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="planning-intent">
                What would you like to plan for?
              </label>
              <div className="govuk-hint">
                Describe your evacuation planning goal in natural language. 
                The AI will generate appropriate scenarios and metrics.
              </div>
              
              {/* Quick suggestions */}
              {suggestedScenarios.length > 0 && (
                <div className="govuk-!-margin-bottom-3">
                  <p className="govuk-body-s govuk-!-font-weight-bold">Suggested scenarios for {context?.name}:</p>
                  {suggestedScenarios.map((suggestion, index) => (
                    <button
                      key={index}
                      className="govuk-button govuk-button--secondary govuk-!-margin-right-2 govuk-!-margin-bottom-2"
                      onClick={() => setUserIntent(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}

              <textarea
                className="govuk-textarea"
                id="planning-intent"
                rows={4}
                value={userIntent}
                onChange={(e) => setUserIntent(e.target.value)}
                placeholder="e.g., 'Test evacuation efficiency during a major flood event, focusing on protecting vulnerable populations and maintaining access to hospitals'"
              />
            </div>

            <button
              className="govuk-button"
              onClick={handleIntentSubmission}
              disabled={!userIntent.trim() || isGeneratingRecommendations}
            >
              {isGeneratingRecommendations ? 'Generating AI Recommendations...' : 'Generate AI Planning Package'}
            </button>
          </div>
        )}

        {/* Step 2: Customize AI Recommendations */}
        {planningStep === 'customize' && (
          <div>
            <h2 className="govuk-heading-l">Review AI Recommendations</h2>
            
            <div className="govuk-grid-row">
              <div className="govuk-grid-column-one-half">
                <h3 className="govuk-heading-m">Generated Scenario</h3>
                <div className="govuk-panel govuk-panel--confirmation">
                  <div className="govuk-panel__body">
                    <strong>{selectedScenario}</strong>
                  </div>
                </div>
                <p className="govuk-body-s">
                  Based on your intent: "{userIntent}"
                </p>
              </div>
              
              <div className="govuk-grid-column-one-half">
                <h3 className="govuk-heading-m">Recommended Metrics</h3>
                {customMetrics.length > 0 ? (
                  <ul className="govuk-list govuk-list--bullet">
                    {customMetrics.map((metric, index) => (
                      <li key={index}>{metric}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="govuk-body">Standard evacuation metrics will be used</p>
                )}
              </div>
            </div>

            <div className="govuk-button-group govuk-!-margin-top-6">
              <button
                className="govuk-button"
                onClick={() => setPlanningStep('generate')}
              >
                Run AI-Generated Simulation
              </button>
              <button
                className="govuk-button govuk-button--secondary"
                onClick={() => setPlanningStep('intent')}
              >
                Back to Planning Goal
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generate and Run */}
        {planningStep === 'generate' && (
          <AISimulationRunner
            borough={borough}
            context={context}
            scenario={selectedScenario}
            metrics={customMetrics}
            onComplete={(results) => {
              setSimulationResults(results);
              setPlanningStep('results');
              onPlanGenerated(results);
            }}
          />
        )}

        {/* Step 4: Results */}
        {planningStep === 'results' && (
          <div>
            <h2 className="govuk-heading-l">AI Planning Results</h2>
            <div className="govuk-panel govuk-panel--confirmation">
              <h3 className="govuk-panel__title">Planning Complete</h3>
              <div className="govuk-panel__body">
                Your AI-generated evacuation plan for {context?.name} is ready for review.
              </div>
            </div>
            <div className="govuk-button-group">
              <button
                className="govuk-button"
                onClick={() => {
                  // Get the run_id from the simulation results
                  const runId = simulationResults?.run_id;
                  if (runId) {
                    window.location.href = `/results/${runId}?city=${borough}`;
                  } else {
                    window.location.href = `/results?city=${borough}`;
                  }
                }}
              >
                View Detailed Results
              </button>
              <button
                className="govuk-button govuk-button--secondary"
                onClick={() => setPlanningStep('intent')}
              >
                Plan Another Scenario
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIPlanningSectionComponent;
