/**
 * Smart Planning Page - Borough-specific AI planning interface
 * Integrates AgenticPlannerPanel with borough context
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GOVUK_CLASSES } from '../theme/govuk';
import { BoroughContext, BoroughContextService } from '../services/boroughContextService';
import AIPlanningSectionComponent from './AIPlanningSectionComponent';
import PlanAndRunGovUK from './PlanAndRunGovUK';

interface SmartPlanningPageProps {}

const SmartPlanningPage: React.FC<SmartPlanningPageProps> = () => {
  const { boroughName } = useParams<{ boroughName: string }>();
  const navigate = useNavigate();
  const [planningMode, setPlanningMode] = useState<'ai' | 'traditional'>('ai');
  const [boroughContext, setBoroughContext] = useState<BoroughContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load borough-specific context
  useEffect(() => {
    loadBoroughContext();
  }, [boroughName]);

  const loadBoroughContext = async () => {
    if (!boroughName) {
      setError('Borough name is required');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      // Get borough context from service
      const context = BoroughContextService.getBoroughContext(boroughName);
      
      if (!context) {
        // If not found in our predefined data, create a basic context
        const formattedName = BoroughContextService.formatBoroughName(boroughName);
        const basicContext: BoroughContext = {
          name: formattedName,
          slug: boroughName,
          demographics: {
            population: 200000,
            density: 10000,
            vulnerablePopulation: 15000,
            touristAreas: []
          },
          infrastructure: {
            majorRoads: [],
            transportHubs: [],
            hospitals: [],
            schools: [],
            emergencyServices: []
          },
          riskProfile: {
            floodRisk: 'medium',
            terroristThreat: 'medium',
            historicalIncidents: []
          },
          evacuationChallenges: ['Limited data available for this borough'],
          keyAssets: [],
          neighboringBoroughs: []
        };
        setBoroughContext(basicContext);
      } else {
        setBoroughContext(context);
      }
    } catch (error) {
      console.error('Failed to load borough context:', error);
      setError('Failed to load borough information');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlanGenerated = (plan: any) => {
    console.log('Plan generated:', plan);
    // Navigate to results if we have a run_id
    if (plan.run_id) {
      navigate(`/results/${plan.run_id}?city=${boroughName}`);
    }
  };

  const formatBoroughName = (slug: string): string => {
    return BoroughContextService.formatBoroughName(slug);
  };

  if (isLoading) {
    return (
      <div className="govuk-width-container">
        <div className="govuk-main-wrapper">
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-two-thirds">
              <h1 className="govuk-heading-xl">Loading...</h1>
              <p className="govuk-body">Loading borough information...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="govuk-width-container">
        <div className="govuk-main-wrapper">
          <div className="govuk-error-summary" role="alert">
            <h2 className="govuk-error-summary__title">There is a problem</h2>
            <div className="govuk-error-summary__body">
              <p>{error}</p>
              <button 
                className="govuk-button govuk-button--secondary"
                onClick={() => navigate('/boroughs')}
              >
                Back to Boroughs
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="govuk-width-container">
      <div className="govuk-main-wrapper">
        {/* Breadcrumb navigation */}
        <div className="govuk-breadcrumbs">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <a className="govuk-breadcrumbs__link" href="/boroughs">Boroughs</a>
            </li>
            <li className="govuk-breadcrumbs__list-item">
              <a className="govuk-breadcrumbs__link" href={`/borough/${boroughName}`}>
                {formatBoroughName(boroughName || '')}
              </a>
            </li>
            <li className="govuk-breadcrumbs__list-item" aria-current="page">
              Smart Planning
            </li>
          </ol>
        </div>

        {/* Page header */}
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            <h1 className="govuk-heading-xl">
              Emergency Planning for {formatBoroughName(boroughName || '')}
            </h1>
            <p className="govuk-body-l">
              Use AI-powered planning to create intelligent evacuation scenarios 
              tailored to {formatBoroughName(boroughName || '')}'s specific characteristics.
            </p>
          </div>
        </div>

        {/* Planning mode selection */}
        <div className="govuk-form-group">
          <fieldset className="govuk-fieldset">
            <legend className="govuk-fieldset__legend govuk-fieldset__legend--m">
              Choose your planning approach
            </legend>
            <div className="govuk-radios govuk-radios--inline">
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="planning-ai" 
                  name="planning-mode" 
                  type="radio" 
                  value="ai"
                  checked={planningMode === 'ai'}
                  onChange={() => setPlanningMode('ai')}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="planning-ai">
                  AI-Powered Planning (Recommended)
                </label>
                <div className="govuk-hint govuk-radios__hint">
                  Describe your planning goals in natural language. AI will generate 
                  scenarios, metrics, and analysis tailored to your needs.
                </div>
              </div>
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="planning-traditional" 
                  name="planning-mode" 
                  type="radio" 
                  value="traditional"
                  checked={planningMode === 'traditional'}
                  onChange={() => setPlanningMode('traditional')}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="planning-traditional">
                  Traditional Planning
                </label>
                <div className="govuk-hint govuk-radios__hint">
                  Manual configuration of scenarios and parameters.
                </div>
              </div>
            </div>
          </fieldset>
        </div>

        {/* AI Planning Interface */}
        {planningMode === 'ai' && (
          <AIPlanningSectionComponent 
            borough={boroughName || ''}
            context={boroughContext}
            onPlanGenerated={handlePlanGenerated}
          />
        )}

        {/* Traditional Planning Interface */}
        {planningMode === 'traditional' && (
          <div className="govuk-!-margin-top-6">
            <h2 className="govuk-heading-l">Traditional Planning Interface</h2>
            <div className="govuk-inset-text">
              <p>
                This interface provides manual configuration options for evacuation scenarios.
                For borough-specific intelligent planning, we recommend using the AI-powered approach above.
              </p>
            </div>
            <PlanAndRunGovUK />
          </div>
        )}

        {/* Help section */}
        <div className="govuk-!-margin-top-9">
          <details className="govuk-details" data-module="govuk-details">
            <summary className="govuk-details__summary">
              <span className="govuk-details__summary-text">
                How does AI-powered planning work?
              </span>
            </summary>
            <div className="govuk-details__text">
              <h3 className="govuk-heading-s">AI Planning Process</h3>
              <ol className="govuk-list govuk-list--number">
                <li>
                  <strong>Context Analysis:</strong> AI analyzes {formatBoroughName(boroughName || '')}'s 
                  demographics, infrastructure, and risk profile
                </li>
                <li>
                  <strong>Scenario Generation:</strong> Based on your natural language description, 
                  AI creates appropriate evacuation scenarios
                </li>
                <li>
                  <strong>Metrics Selection:</strong> AI recommends relevant metrics for your 
                  specific planning goals
                </li>
                <li>
                  <strong>Framework Compliance:</strong> All scenarios comply with the 
                  London Mass Evacuation Framework v3.0
                </li>
                <li>
                  <strong>Intelligent Analysis:</strong> Results include AI explanations 
                  with citations from official sources
                </li>
              </ol>

              {boroughContext && (
                <>
                  <h3 className="govuk-heading-s">Borough-Specific Intelligence</h3>
                  <p>The AI has access to the following information about {boroughContext.name}:</p>
                  <ul className="govuk-list govuk-list--bullet">
                    <li>Population: {boroughContext.demographics.population.toLocaleString()}</li>
                    <li>Population density: {boroughContext.demographics.density}/km²</li>
                    <li>Flood risk: {boroughContext.riskProfile.floodRisk}</li>
                    <li>Terrorist threat level: {boroughContext.riskProfile.terroristThreat}</li>
                    <li>Key assets: {boroughContext.keyAssets.slice(0, 3).join(', ')}</li>
                    <li>Major transport hubs: {boroughContext.infrastructure.transportHubs.slice(0, 3).join(', ')}</li>
                  </ul>
                </>
              )}
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default SmartPlanningPage;
