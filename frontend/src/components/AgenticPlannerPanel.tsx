/**
 * Emergency Planning Assistant
 * 
 * Intelligent natural language interface for creating evacuation scenarios and metrics.
 * Integrates with the existing simulation workflow to enable advanced planning capabilities.
 */

import React, { useState, useEffect } from 'react';
import { API_CONFIG, API_ENDPOINTS, REQUEST_CONFIG } from '../config/api';
import { GOVUK_CLASSES } from '../theme/govuk';
import { BoroughContext, BoroughContextService } from '../services/boroughContextService';

interface AgenticPlannerPanelProps {
  isOpen: boolean;
  onClose: () => void;
  city: string;
  onScenarioGenerated?: (scenario: any) => void;
  onMetricsGenerated?: (metrics: any) => void;
  onAnalysisPackageCreated?: (packageData: any) => void;
}

interface GeneratedScenario {
  specification: any;
  variants_suggestion: any;
  reasoning: string;
  generated_by: string;
  intent: string;
  timestamp: string;
}

interface GeneratedMetrics {
  specification: any;
  reasoning: string;
  generated_by: string;
  analysis_goal: string;
  timestamp: string;
}

interface AnalysisPackage {
  package_id: string;
  analysis_goal: string;
  scenario: GeneratedScenario;
  metrics: GeneratedMetrics;
  city_context: string;
  created_at: string;
  framework_info?: {
    framework_compliant: boolean;
    evaluation_ready: boolean;
    template_used?: string;
    golden_standards_available: boolean;
  };
}

interface FrameworkTemplate {
  name: string;
  description: string;
  scale: string;
  hazard_type: string;
  people_affected: number | string;
  duration_minutes: number | string;
  compliance_level: string;
  source: string;
}

const AgenticPlannerPanel: React.FC<AgenticPlannerPanelProps> = ({
  isOpen,
  onClose,
  city,
  onScenarioGenerated,
  onMetricsGenerated,
  onAnalysisPackageCreated
}) => {
  const [activeTab, setActiveTab] = useState<'scenario' | 'metrics' | 'package'>('package');
  const [isLoading, setIsLoading] = useState(false);
  
  // Scenario generation state
  const [scenarioIntent, setScenarioIntent] = useState('');
  const [scenarioConstraints, setScenarioConstraints] = useState('');
  const [generatedScenario, setGeneratedScenario] = useState<GeneratedScenario | null>(null);
  
  // Metrics generation state
  const [analysisGoal, setAnalysisGoal] = useState('');
  const [metricsContext, setMetricsContext] = useState('');
  const [generatedMetrics, setGeneratedMetrics] = useState<GeneratedMetrics | null>(null);
  
  // Analysis package state
  const [packageAnalysisGoal, setPackageAnalysisGoal] = useState('');
  const [packageScenarioIntent, setPackageScenarioIntent] = useState('');
  const [generatedPackage, setGeneratedPackage] = useState<AnalysisPackage | null>(null);
  
  // Framework state
  const [frameworkTemplates, setFrameworkTemplates] = useState<Record<string, FrameworkTemplate>>({});
  const [useFramework, setUseFramework] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [availableMetrics, setAvailableMetrics] = useState<any>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  
  // Capabilities and examples
  const [capabilities, setCapabilities] = useState<any>(null);
  const [examples, setExamples] = useState<any>(null);

  // Load capabilities and examples on mount
  useEffect(() => {
    if (isOpen) {
      loadCapabilitiesAndExamples();
      loadFrameworkTemplates();
      loadAvailableMetrics();
      loadBoroughSpecificTemplates();
    }
  }, [isOpen, city]);

  const loadFrameworkTemplates = async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/agentic/framework-templates`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setFrameworkTemplates(data.templates);
      }
    } catch (error) {
      console.error('Failed to load framework templates:', error);
    }
  };

  const loadAvailableMetrics = async () => {
    try {
      // Load golden standards and evaluation metrics
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/evaluation/goldens`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAvailableMetrics(data);
      }
    } catch (error) {
      console.error('Failed to load available metrics:', error);
      // Set some default metrics info if the endpoint doesn't exist
      setAvailableMetrics({
        framework_metrics: [
          'evacuees_total_expected',
          'assisted_evacuees_expected', 
          'clearance_p95_minutes',
          'clearance_p50_minutes',
          'decision_latency_minutes_max',
          'queue_len_p95_max',
          'platform_overcap_minutes_max'
        ],
        source: 'London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)'
      });
    }
  };

  const loadCapabilitiesAndExamples = async () => {
    try {
      const [capabilitiesResponse, examplesResponse] = await Promise.all([
        fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.capabilities}`),
        fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.examples}`)
      ]);

      if (capabilitiesResponse.ok) {
        const caps = await capabilitiesResponse.json();
        setCapabilities(caps);
      }

      if (examplesResponse.ok) {
        const exs = await examplesResponse.json();
        setExamples(exs);
      }
    } catch (error) {
      console.error('Failed to load agentic capabilities:', error);
    }
  };

  const loadBoroughSpecificTemplates = () => {
    // Get borough context and generate specific templates
    const boroughContext = BoroughContextService.getBoroughContext(city);
    if (!boroughContext) return;

    const boroughTemplates = getBoroughSpecificTemplates(city, boroughContext);
    
    // Merge with existing framework templates
    setFrameworkTemplates(prev => ({
      ...prev,
      ...boroughTemplates.reduce((acc, template) => {
        acc[template.id] = template;
        return acc;
      }, {} as Record<string, any>)
    }));
  };

  const getBoroughSpecificTemplates = (borough: string, context: BoroughContext) => {
    const templates = [];
    
    // Risk-based templates
    if (context.riskProfile.floodRisk === 'high') {
      templates.push({
        id: `${borough}_flood_response`,
        name: `${context.name} Flood Response`,
        description: `Tailored flood evacuation for ${context.name}'s specific geography and infrastructure`,
        category: 'Borough-Specific',
        parameters: {
          hazard_type: 'flood',
          affected_areas: context.infrastructure.majorRoads,
          population_affected: Math.floor(context.demographics.population * 0.3),
          transport_disruption: 0.8,
          protected_assets: context.keyAssets
        }
      });
    }

    // Tourism-based templates
    if (context.demographics.touristAreas.length > 0) {
      templates.push({
        id: `${borough}_tourist_emergency`,
        name: `${context.name} Tourist Season Emergency`,
        description: `Emergency response during peak tourism with increased population density`,
        category: 'Borough-Specific',
        parameters: {
          population_multiplier: 1.5,
          unfamiliar_population_percentage: 0.4,
          language_barriers: true,
          affected_areas: context.demographics.touristAreas
        }
      });
    }

    // High-density templates
    if (context.demographics.density > 12000) {
      templates.push({
        id: `${borough}_high_density`,
        name: `${context.name} High-Density Evacuation`,
        description: `Specialized evacuation for high population density areas`,
        category: 'Borough-Specific',
        parameters: {
          density_factor: context.demographics.density / 10000,
          vulnerable_population: context.demographics.vulnerablePopulation,
          transport_capacity_constraints: true
        }
      });
    }

    // Transport hub templates
    if (context.infrastructure.transportHubs.length > 2) {
      templates.push({
        id: `${borough}_transport_disruption`,
        name: `${context.name} Transport Hub Disruption`,
        description: `Evacuation scenario with major transport hub closures`,
        category: 'Borough-Specific',
        parameters: {
          closed_hubs: context.infrastructure.transportHubs.slice(0, 2),
          alternative_routes: context.infrastructure.majorRoads,
          capacity_reduction: 0.6
        }
      });
    }

    return templates;
  };

  const generateScenario = async () => {
    if (!scenarioIntent.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.generateScenario}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_intent: scenarioIntent,
          city_context: city,
          constraints: scenarioConstraints,
          use_framework: useFramework,
          framework_template: selectedTemplate || undefined
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate scenario');
      }

      const result = await response.json();
      setGeneratedScenario(result);
      onScenarioGenerated?.(result);
      
    } catch (error) {
      console.error('Scenario generation failed:', error);
      alert('Failed to generate scenario. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const generateMetrics = async () => {
    if (!analysisGoal.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.generateMetrics}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_goal: selectedMetrics.length > 0 
            ? `${analysisGoal}. Focus specifically on these metrics: ${selectedMetrics.join(', ')}`
            : analysisGoal,
          context: metricsContext
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate metrics');
      }

      const result = await response.json();
      setGeneratedMetrics(result);
      onMetricsGenerated?.(result);
      
    } catch (error) {
      console.error('Metrics generation failed:', error);
      alert('Failed to generate metrics. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const generateRealisticScenarios = async () => {
    if (!packageAnalysisGoal.trim() || !packageScenarioIntent.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/agentic/generate-realistic-scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_goal: packageAnalysisGoal,
          scenario_intent: packageScenarioIntent,
          city_context: city,
          num_scenarios: 3
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate realistic scenarios');
      }

      const result = await response.json();
      
      if (result.success && result.run_result) {
        // Trigger the callback with the run result to navigate to results
        onAnalysisPackageCreated?.(result.run_result);
        console.log('Generated realistic scenarios with real metrics!');
      }
      
    } catch (error) {
      console.error('Realistic scenario generation failed:', error);
      alert('Failed to generate realistic scenarios. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const createAnalysisPackage = async () => {
    if (!packageAnalysisGoal.trim() || !packageScenarioIntent.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.analysisPackage}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_goal: packageAnalysisGoal,
          scenario_intent: packageScenarioIntent,
          city_context: city,
          use_framework: useFramework,
          framework_template: selectedTemplate || undefined
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create analysis package');
      }

      const result = await response.json();
      
      // If this is a framework scenario with executable configs, automatically execute it
      if (result.framework_compliant && result.executable_scenarios && result.executable_scenarios.length > 0) {
        try {
          const executionResponse = await fetch('/api/agentic/execute-framework-scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              package_id: result.package_id
            })
          });
          
          if (executionResponse.ok) {
            const executionResult = await executionResponse.json();
            
            // Update the package with execution results
            result.execution_results = executionResult;
            result.has_real_metrics = true;
            
            console.log('Framework scenario executed successfully with real metrics!');
          } else {
            console.warn('Scenario created but execution failed. Using template data.');
          }
        } catch (execError) {
          console.error('Failed to execute framework scenario:', execError);
        }
      }
      
      setGeneratedPackage(result);
      onAnalysisPackageCreated?.(result);
      
    } catch (error) {
      console.error('Analysis package creation failed:', error);
      alert('Failed to create analysis package. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillExample = (type: 'scenario' | 'metrics' | 'package', exampleKey: string) => {
    if (!examples) return;

    if (type === 'scenario' && examples.scenario_examples?.[exampleKey]) {
      setScenarioIntent(examples.scenario_examples[exampleKey].scenario_intent);
    } else if (type === 'metrics' && examples.metrics_examples?.[exampleKey]) {
      setAnalysisGoal(examples.metrics_examples[exampleKey].analysis_goal);
    } else if (type === 'package' && examples.analysis_package_examples?.[exampleKey]) {
      const example = examples.analysis_package_examples[exampleKey];
      setPackageAnalysisGoal(example.analysis_goal);
      setPackageScenarioIntent(example.scenario_intent);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="govuk-modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.8)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      paddingTop: '2rem'
    }}>
      <div className="govuk-modal" style={{
        backgroundColor: 'white',
        width: '95%',
        maxWidth: '1200px',
        maxHeight: '90vh',
        overflow: 'hidden',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      }}>
        
        {/* GOV.UK Header */}
        <div style={{ backgroundColor: '#1d70b8', color: 'white', padding: '1.5rem 2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h1 className={`${GOVUK_CLASSES.heading.l}`} style={{ color: 'white', margin: 0, fontSize: '1.5rem' }}>
                Emergency Planning Assistant
              </h1>
              <p style={{ color: '#b3d1f2', margin: '0.5rem 0 0 0', fontSize: '1rem' }}>
                Advanced scenario and metrics generation for {city}
              </p>
            </div>
            <button
              onClick={onClose}
              className="govuk-button govuk-button--inverse"
              style={{ margin: 0, minWidth: 'auto', padding: '0.5rem 1rem' }}
              aria-label="Close planning assistant"
            >
              Close
            </button>
          </div>
        </div>

        {/* GOV.UK Tabs */}
        <div className="govuk-tabs" data-module="govuk-tabs" style={{ margin: 0 }}>
          <h2 className="govuk-tabs__title">Contents</h2>
          <ul className="govuk-tabs__list">
            {[
              { id: 'package', label: 'Complete Analysis Package', desc: 'Generate scenario and metrics together' },
              { id: 'scenario', label: 'Scenario Builder', desc: 'Create evacuation scenarios' },
              { id: 'metrics', label: 'Metrics Builder', desc: 'Define analysis metrics' }
            ].map((tab) => (
              <li key={tab.id} className={`govuk-tabs__list-item ${activeTab === tab.id ? 'govuk-tabs__list-item--selected' : ''}`}>
                <a 
                  className="govuk-tabs__tab" 
                  href={`#${tab.id}`}
                  onClick={(e) => { e.preventDefault(); setActiveTab(tab.id as any); }}
                >
                  {tab.label}
                </a>
              </li>
            ))}
          </ul>

          {/* Complete Package Tab */}
          <div className={`govuk-tabs__panel ${activeTab === 'package' ? '' : 'govuk-tabs__panel--hidden'}`} id="package">
            <div style={{ padding: '2rem', maxHeight: 'calc(90vh - 200px)', overflowY: 'auto' }}>
              
              <div className="govuk-notification-banner" role="region" aria-labelledby="govuk-notification-banner-title">
                <div className="govuk-notification-banner__header">
                  <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title">
                    Complete Analysis Package
                  </h2>
                </div>
                <div className="govuk-notification-banner__content">
                  <p className={GOVUK_CLASSES.body.m}>
                    Generate both a scenario and optimized metrics together. The system will create a scenario 
                    based on your intent and automatically select the best metrics for analysing that scenario type.
                  </p>
                </div>
              </div>

              <div className={GOVUK_CLASSES.gridRow}>
                <div className={GOVUK_CLASSES.gridColumn.half}>
                  <div className={GOVUK_CLASSES.form.group}>
                    <label className={GOVUK_CLASSES.form.label} htmlFor="analysis-goal">
                      Analysis Goal
                    </label>
                    <div className="govuk-hint">
                      What do you want to analyze? (e.g., 'Analyze flood evacuation efficiency and safety risks')
                    </div>
                    <textarea
                      className={GOVUK_CLASSES.form.textarea}
                      id="analysis-goal"
                      rows={4}
                      value={packageAnalysisGoal}
                      onChange={(e) => setPackageAnalysisGoal(e.target.value)}
                    />
                  </div>
                </div>

                <div className={GOVUK_CLASSES.gridColumn.half}>
                  <div className={GOVUK_CLASSES.form.group}>
                    <label className={GOVUK_CLASSES.form.label} htmlFor="scenario-intent">
                      Scenario Intent
                    </label>
                    <div className="govuk-hint">
                      Describe the scenario you want to test (e.g., 'Major Thames flood during rush hour')
                    </div>
                    <textarea
                      className={GOVUK_CLASSES.form.textarea}
                      id="scenario-intent"
                      rows={4}
                      value={packageScenarioIntent}
                      onChange={(e) => setPackageScenarioIntent(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <fieldset className="govuk-fieldset">
                  <legend className="govuk-fieldset__legend govuk-fieldset__legend--s">
                    Framework Compliance
                  </legend>
                  <div className="govuk-hint">
                    Use framework-compliant scenarios with evaluation against golden standards
                  </div>
                  <div className="govuk-checkboxes">
                    <div className="govuk-checkboxes__item">
                      <input
                        className="govuk-checkboxes__input"
                        id="package-use-framework"
                        type="checkbox"
                        checked={useFramework}
                        onChange={(e) => setUseFramework(e.target.checked)}
                      />
                      <label className="govuk-label govuk-checkboxes__label" htmlFor="package-use-framework">
                        Use framework-compliant scenarios with evaluation
                      </label>
                    </div>
                  </div>
                </fieldset>
              </div>

              {useFramework && Object.keys(frameworkTemplates).length > 0 && (
                <div className={GOVUK_CLASSES.form.group}>
                  <label className={GOVUK_CLASSES.form.label} htmlFor="package-framework-template">
                    Framework Template (Optional)
                  </label>
                  <div className="govuk-hint">
                    Select a specific framework template for evaluation, or leave blank for AI selection
                  </div>
                  <select
                    className={GOVUK_CLASSES.form.select}
                    id="package-framework-template"
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                  >
                    <option value="">Let AI choose best template</option>
                    {Object.entries(frameworkTemplates).map(([key, template]) => (
                      <option key={key} value={key}>
                        {template.name} ({template.scale.toUpperCase()}, {template.hazard_type})
                      </option>
                    ))}
                  </select>
                  {selectedTemplate && frameworkTemplates[selectedTemplate] && (
                    <div className="govuk-inset-text" style={{ marginTop: '1rem' }}>
                      <strong>{frameworkTemplates[selectedTemplate].name}</strong><br/>
                      Scale: {frameworkTemplates[selectedTemplate].scale.toUpperCase()}<br/>
                      People affected: {frameworkTemplates[selectedTemplate].people_affected}<br/>
                      Duration: {frameworkTemplates[selectedTemplate].duration_minutes} minutes<br/>
                      <em>{frameworkTemplates[selectedTemplate].description}</em>
                    </div>
                  )}
                </div>
              )}

              {examples?.analysis_package_examples && (
                <div className={GOVUK_CLASSES.form.group}>
                  <fieldset className={GOVUK_CLASSES.form.fieldset}>
                    <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.s}`}>
                      Quick Examples
                    </legend>
                    <div className="govuk-hint">
                      Select a pre-configured example to get started quickly
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                      {Object.keys(examples.analysis_package_examples).map((key) => (
                        <button
                          key={key}
                          onClick={() => fillExample('package', key)}
                          className={GOVUK_CLASSES.button.secondary}
                          style={{ margin: 0 }}
                        >
                          {key.replace(/_/g, ' ')}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                </div>
              )}

              <div className="govuk-button-group">
                <button
                  onClick={createAnalysisPackage}
                  disabled={isLoading || !packageAnalysisGoal.trim() || !packageScenarioIntent.trim()}
                  className={`${GOVUK_CLASSES.button.primary} ${(isLoading || !packageAnalysisGoal.trim() || !packageScenarioIntent.trim()) ? 'govuk-button--disabled' : ''}`}
                >
                  {isLoading ? 'Generating Analysis Package...' : 'Create Complete Analysis Package'}
                </button>
                
                <button
                  onClick={generateRealisticScenarios}
                  disabled={isLoading || !packageAnalysisGoal.trim() || !packageScenarioIntent.trim()}
                  className={`${GOVUK_CLASSES.button.secondary} ${(isLoading || !packageAnalysisGoal.trim() || !packageScenarioIntent.trim()) ? 'govuk-button--disabled' : ''}`}
                >
                  {isLoading ? 'Generating Scenarios...' : 'Generate Realistic Scenarios'}
                </button>
              </div>

              {generatedPackage && (
                <div className="govuk-notification-banner govuk-notification-banner--success" role="alert" aria-labelledby="govuk-notification-banner-title">
                  <div className="govuk-notification-banner__header">
                    <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title">
                      Success
                    </h2>
                  </div>
                  <div className="govuk-notification-banner__content">
                    <h3 className="govuk-notification-banner__heading">
                      Analysis Package Created Successfully
                    </h3>
                    <dl className="govuk-summary-list govuk-summary-list--no-border">
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Package ID</dt>
                        <dd className="govuk-summary-list__value">{generatedPackage.package_id}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Scenario</dt>
                        <dd className="govuk-summary-list__value">{generatedPackage.scenario.specification.name}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Metrics Generated</dt>
                        <dd className="govuk-summary-list__value">{Object.keys(generatedPackage.metrics.specification.metrics || {}).length} metrics</dd>
                      </div>
                      {generatedPackage.framework_info && (
                        <>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Framework Compliant</dt>
                            <dd className="govuk-summary-list__value">
                              {generatedPackage.framework_info.framework_compliant ? (
                                <span className="govuk-tag govuk-tag--green">✓ Yes</span>
                              ) : (
                                <span className="govuk-tag govuk-tag--grey">No</span>
                              )}
                            </dd>
                          </div>
                          {generatedPackage.framework_info.template_used && (
                            <div className="govuk-summary-list__row">
                              <dt className="govuk-summary-list__key">Template Used</dt>
                              <dd className="govuk-summary-list__value">{generatedPackage.framework_info.template_used}</dd>
                            </div>
                          )}
                          {generatedPackage.framework_info.evaluation_ready && (
                            <div className="govuk-summary-list__row">
                              <dt className="govuk-summary-list__key">Evaluation Ready</dt>
                              <dd className="govuk-summary-list__value">
                                <span className="govuk-tag govuk-tag--blue">✓ Ready for evaluation against golden standards</span>
                              </dd>
                            </div>
                          )}
                        </>
                      )}
                    </dl>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Scenario Builder Tab */}
          <div className={`govuk-tabs__panel ${activeTab === 'scenario' ? '' : 'govuk-tabs__panel--hidden'}`} id="scenario">
            <div style={{ padding: '2rem', maxHeight: 'calc(90vh - 200px)', overflowY: 'auto' }}>
              
              <div className="govuk-notification-banner" role="region" aria-labelledby="govuk-notification-banner-title-scenario">
                <div className="govuk-notification-banner__header">
                  <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title-scenario">
                    Scenario Builder
                  </h2>
                </div>
                <div className="govuk-notification-banner__content">
                  <p className={GOVUK_CLASSES.body.m}>
                    Describe the evacuation scenario you want to create in natural language. 
                    The system will generate realistic parameters, affected areas, and constraints.
                  </p>
                </div>
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="scenario-intent-input">
                  Scenario Intent
                </label>
                <div className="govuk-hint">
                  Describe the scenario (e.g., 'Major Thames flood affecting central London transport during rush hour')
                </div>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="scenario-intent-input"
                  rows={5}
                  value={scenarioIntent}
                  onChange={(e) => setScenarioIntent(e.target.value)}
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="scenario-constraints">
                  Constraints (Optional)
                </label>
                <div className="govuk-hint">
                  Any specific constraints (e.g., 'High severity, 50,000 people affected, 4 hours duration')
                </div>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="scenario-constraints"
                  rows={3}
                  value={scenarioConstraints}
                  onChange={(e) => setScenarioConstraints(e.target.value)}
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <fieldset className="govuk-fieldset">
                  <legend className="govuk-fieldset__legend govuk-fieldset__legend--s">
                    Framework Compliance
                  </legend>
                  <div className="govuk-hint">
                    Use framework-compliant scenarios based on the London Mass Evacuation Framework
                  </div>
                  <div className="govuk-checkboxes">
                    <div className="govuk-checkboxes__item">
                      <input
                        className="govuk-checkboxes__input"
                        id="use-framework"
                        type="checkbox"
                        checked={useFramework}
                        onChange={(e) => setUseFramework(e.target.checked)}
                      />
                      <label className="govuk-label govuk-checkboxes__label" htmlFor="use-framework">
                        Use framework-compliant scenarios
                      </label>
                    </div>
                  </div>
                </fieldset>
              </div>

              {useFramework && Object.keys(frameworkTemplates).length > 0 && (
                <>
                  <div className={GOVUK_CLASSES.form.group}>
                    <label className={GOVUK_CLASSES.form.label} htmlFor="framework-template">
                      Framework Template (Optional)
                    </label>
                    <div className="govuk-hint">
                      Select a specific framework template from the London Resilience Mass Evacuation Framework v3.0 (June 2018)
                    </div>
                    <select
                      className={GOVUK_CLASSES.form.select}
                      id="framework-template"
                      value={selectedTemplate}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                    >
                      <option value="">Let AI choose best template</option>
                      {Object.entries(frameworkTemplates).map(([key, template]) => (
                        <option key={key} value={key}>
                          {template.name} ({template.scale.toUpperCase()}, {template.hazard_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className={GOVUK_CLASSES.form.group}>
                    <details className="govuk-details" data-module="govuk-details">
                      <summary className="govuk-details__summary">
                        <span className="govuk-details__summary-text">
                          View all available framework templates
                        </span>
                      </summary>
                      <div className="govuk-details__text">
                        <div className="govuk-hint" style={{ marginBottom: '1rem' }}>
                          <strong>Source:</strong> London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)
                        </div>
                        {Object.entries(frameworkTemplates).map(([key, template]) => (
                          <div key={key} className="govuk-inset-text" style={{ marginBottom: '1rem' }}>
                            <h4 className="govuk-heading-s" style={{ marginBottom: '0.5rem' }}>
                              {template.name}
                              <button
                                type="button"
                                className="govuk-button govuk-button--secondary"
                                style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem', fontSize: '0.875rem' }}
                                onClick={() => setSelectedTemplate(key)}
                              >
                                Select This Template
                              </button>
                            </h4>
                            <dl className="govuk-summary-list govuk-summary-list--no-border" style={{ fontSize: '0.875rem' }}>
                              <div className="govuk-summary-list__row">
                                <dt className="govuk-summary-list__key" style={{ width: '30%' }}>Scale</dt>
                                <dd className="govuk-summary-list__value">{template.scale.toUpperCase()}</dd>
                              </div>
                              <div className="govuk-summary-list__row">
                                <dt className="govuk-summary-list__key">Hazard Type</dt>
                                <dd className="govuk-summary-list__value">{template.hazard_type}</dd>
                              </div>
                              <div className="govuk-summary-list__row">
                                <dt className="govuk-summary-list__key">People Affected</dt>
                                <dd className="govuk-summary-list__value">{typeof template.people_affected === 'number' ? template.people_affected.toLocaleString() : template.people_affected}</dd>
                              </div>
                              <div className="govuk-summary-list__row">
                                <dt className="govuk-summary-list__key">Duration</dt>
                                <dd className="govuk-summary-list__value">{template.duration_minutes} minutes</dd>
                              </div>
                            </dl>
                            <p style={{ fontSize: '0.875rem', fontStyle: 'italic', marginTop: '0.5rem' }}>
                              {template.description}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                </>
              )}

              {examples?.scenario_examples && (
                <div className={GOVUK_CLASSES.form.group}>
                  <fieldset className={GOVUK_CLASSES.form.fieldset}>
                    <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.s}`}>
                      Quick Examples
                    </legend>
                    <div className="govuk-hint">
                      Select a pre-configured scenario example
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                      {Object.keys(examples.scenario_examples).map((key) => (
                        <button
                          key={key}
                          onClick={() => fillExample('scenario', key)}
                          className={GOVUK_CLASSES.button.secondary}
                          style={{ margin: 0 }}
                        >
                          {key.replace(/_/g, ' ')}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                </div>
              )}

              <div className="govuk-button-group">
                <button
                  onClick={generateScenario}
                  disabled={isLoading || !scenarioIntent.trim()}
                  className={`${GOVUK_CLASSES.button.primary} ${(isLoading || !scenarioIntent.trim()) ? 'govuk-button--disabled' : ''}`}
                >
                  {isLoading ? 'Generating Scenario...' : 'Generate Scenario'}
                </button>
              </div>

              {generatedScenario && (
                <div className="govuk-notification-banner govuk-notification-banner--success" role="alert">
                  <div className="govuk-notification-banner__header">
                    <h2 className="govuk-notification-banner__title">Success</h2>
                  </div>
                  <div className="govuk-notification-banner__content">
                    <h3 className="govuk-notification-banner__heading">
                      Scenario Generated Successfully
                    </h3>
                    <dl className="govuk-summary-list govuk-summary-list--no-border">
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Name</dt>
                        <dd className="govuk-summary-list__value">{generatedScenario.specification.name}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Hazard Type</dt>
                        <dd className="govuk-summary-list__value">{generatedScenario.specification.hazard_type}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Population Affected</dt>
                        <dd className="govuk-summary-list__value">{generatedScenario.specification.population_affected?.toLocaleString()}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Duration</dt>
                        <dd className="govuk-summary-list__value">{generatedScenario.specification.duration_minutes} minutes</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Metrics Builder Tab */}
          <div className={`govuk-tabs__panel ${activeTab === 'metrics' ? '' : 'govuk-tabs__panel--hidden'}`} id="metrics">
            <div style={{ padding: '2rem', maxHeight: 'calc(90vh - 200px)', overflowY: 'auto' }}>
              
              <div className="govuk-notification-banner" role="region" aria-labelledby="govuk-notification-banner-title-metrics">
                <div className="govuk-notification-banner__header">
                  <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title-metrics">
                    Metrics Builder
                  </h2>
                </div>
                <div className="govuk-notification-banner__content">
                  <p className={GOVUK_CLASSES.body.m}>
                    Describe what you want to analyze in natural language. 
                    The system will generate appropriate metrics specifications for your analysis goals.
                  </p>
                </div>
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="analysis-goal-input">
                  Analysis Goal
                </label>
                <div className="govuk-hint">
                  What do you want to analyze? (e.g., 'I want to analyze evacuation efficiency and identify bottlenecks')
                </div>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="analysis-goal-input"
                  rows={5}
                  value={analysisGoal}
                  onChange={(e) => setAnalysisGoal(e.target.value)}
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="metrics-context">
                  Context (Optional)
                </label>
                <div className="govuk-hint">
                  Additional context (e.g., 'Focus on transport stations and main evacuation routes')
                </div>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="metrics-context"
                  rows={3}
                  value={metricsContext}
                  onChange={(e) => setMetricsContext(e.target.value)}
                />
              </div>

              {availableMetrics && (
                <div className={GOVUK_CLASSES.form.group}>
                  <details className="govuk-details" data-module="govuk-details">
                    <summary className="govuk-details__summary">
                      <span className="govuk-details__summary-text">
                        View available framework metrics and evaluation standards
                      </span>
                    </summary>
                    <div className="govuk-details__text">
                      <div className="govuk-hint" style={{ marginBottom: '1rem' }}>
                        <strong>Source:</strong> {availableMetrics.source || 'London Resilience Partnership - Mass Evacuation Framework v3.0 (June 2018)'}
                        <br/>
                        <strong>Evidence:</strong> Exercise Unified Response (2016), 7 July Review Committee Report (2006), Grenfell Inquiry Phase 2 Report (2024)
                      </div>
                      
                      <h4 className="govuk-heading-s">Framework Evaluation Metrics</h4>
                      <div className="govuk-inset-text">
                        <p className="govuk-body-s">
                          These metrics are evaluated against golden standards derived from the London Mass Evacuation Framework 
                          and historical exercises. Each metric has pass/amber/fail thresholds based on evidence.
                        </p>
                      </div>
                      
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                        {(availableMetrics.framework_metrics || []).map((metric: string) => (
                          <div key={metric} className="govuk-summary-card">
                            <div className="govuk-summary-card__title-wrapper">
                              <h3 className="govuk-summary-card__title">
                                <div className="govuk-checkboxes__item" style={{ marginBottom: '0.5rem' }}>
                                  <input
                                    className="govuk-checkboxes__input"
                                    id={`metric-${metric}`}
                                    type="checkbox"
                                    checked={selectedMetrics.includes(metric)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedMetrics([...selectedMetrics, metric]);
                                      } else {
                                        setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
                                      }
                                    }}
                                  />
                                  <label className="govuk-label govuk-checkboxes__label" htmlFor={`metric-${metric}`}>
                                    {metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </label>
                                </div>
                              </h3>
                            </div>
                            <div className="govuk-summary-card__content">
                              <dl className="govuk-summary-list govuk-summary-list--no-border">
                                <div className="govuk-summary-list__row">
                                  <dt className="govuk-summary-list__key">Type</dt>
                                  <dd className="govuk-summary-list__value">
                                    {metric.includes('time') || metric.includes('minutes') ? 'Time-based' :
                                     metric.includes('count') || metric.includes('expected') ? 'Count-based' :
                                     metric.includes('rate') || metric.includes('prop') ? 'Rate-based' : 'Performance'}
                                  </dd>
                                </div>
                                <div className="govuk-summary-list__row">
                                  <dt className="govuk-summary-list__key">Evaluation</dt>
                                  <dd className="govuk-summary-list__value">
                                    <span className="govuk-tag govuk-tag--blue">Golden Standard Available</span>
                                  </dd>
                                </div>
                              </dl>
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      {selectedMetrics.length > 0 && (
                        <div className="govuk-inset-text" style={{ marginTop: '1rem' }}>
                          <strong>Selected metrics ({selectedMetrics.length}):</strong>
                          <ul className="govuk-list govuk-list--bullet" style={{ marginTop: '0.5rem' }}>
                            {selectedMetrics.map(metric => (
                              <li key={metric}>{metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</li>
                            ))}
                          </ul>
                          <p className="govuk-body-s" style={{ marginTop: '0.5rem' }}>
                            Include these metrics in your analysis goal (e.g., "Focus on {selectedMetrics.slice(0, 2).map(m => m.replace(/_/g, ' ')).join(' and ')}")
                          </p>
                        </div>
                      )}
                      
                      <div className="govuk-warning-text" style={{ marginTop: '1.5rem' }}>
                        <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                        <strong className="govuk-warning-text__text">
                          <span className="govuk-warning-text__assistive">Warning: </span>
                          Tell the AI which specific metrics you want to focus on, or let it select the most relevant ones for your analysis goal.
                        </strong>
                      </div>
                    </div>
                  </details>
                </div>
              )}

              {examples?.metrics_examples && (
                <div className={GOVUK_CLASSES.form.group}>
                  <fieldset className={GOVUK_CLASSES.form.fieldset}>
                    <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.s}`}>
                      Quick Examples
                    </legend>
                    <div className="govuk-hint">
                      Select a pre-configured metrics example
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                      {Object.keys(examples.metrics_examples).map((key) => (
                        <button
                          key={key}
                          onClick={() => fillExample('metrics', key)}
                          className={GOVUK_CLASSES.button.secondary}
                          style={{ margin: 0 }}
                        >
                          {key.replace(/_/g, ' ')}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                </div>
              )}

              <div className="govuk-button-group">
                <button
                  onClick={generateMetrics}
                  disabled={isLoading || !analysisGoal.trim()}
                  className={`${GOVUK_CLASSES.button.primary} ${(isLoading || !analysisGoal.trim()) ? 'govuk-button--disabled' : ''}`}
                >
                  {isLoading ? 'Generating Metrics...' : 'Generate Metrics'}
                </button>
              </div>

              {generatedMetrics && (
                <div className="govuk-notification-banner govuk-notification-banner--success" role="alert">
                  <div className="govuk-notification-banner__header">
                    <h2 className="govuk-notification-banner__title">Success</h2>
                  </div>
                  <div className="govuk-notification-banner__content">
                    <h3 className="govuk-notification-banner__heading">
                      Metrics Generated Successfully
                    </h3>
                    <dl className="govuk-summary-list govuk-summary-list--no-border">
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Analysis Goal</dt>
                        <dd className="govuk-summary-list__value">{generatedMetrics.analysis_goal}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Metrics Count</dt>
                        <dd className="govuk-summary-list__value">{Object.keys(generatedMetrics.specification.metrics || {}).length}</dd>
                      </div>
                      <div className="govuk-summary-list__row">
                        <dt className="govuk-summary-list__key">Reasoning</dt>
                        <dd className="govuk-summary-list__value">{generatedMetrics.reasoning.substring(0, 150)}...</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* GOV.UK Footer */}
        <div style={{ backgroundColor: '#f3f2f1', padding: '1rem 2rem', borderTop: '1px solid #b1b4b6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className={GOVUK_CLASSES.body.s} style={{ color: '#505a5f' }}>
              Emergency Planning for: <strong>{city}</strong>
            </div>
            <div className={GOVUK_CLASSES.body.s} style={{ color: '#505a5f' }}>
              Cabinet Office Emergency Planning
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgenticPlannerPanel;
