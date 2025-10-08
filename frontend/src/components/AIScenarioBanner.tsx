/**
 * AI Scenario Banner - Shows AI-generated scenario context on results page
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';

interface AIScenarioInfo {
  intent: string;
  generated_scenario: string;
  description: string;
  borough: string;
  timestamp: string;
  framework_compliant: boolean;
  template_used: string;
}

interface AIScenarioBannerProps {
  runId: string;
}

const AIScenarioBanner: React.FC<AIScenarioBannerProps> = ({ runId }) => {
  const [aiScenarioInfo, setAIScenarioInfo] = useState<AIScenarioInfo | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Check if this run has AI scenario information
    const storedInfo = localStorage.getItem(`ai_scenario_${runId}`);
    if (storedInfo) {
      try {
        const info = JSON.parse(storedInfo);
        setAIScenarioInfo(info);
      } catch (error) {
        console.error('Failed to parse AI scenario info:', error);
      }
    }
  }, [runId]);

  if (!aiScenarioInfo) {
    return null;
  }

  return (
    <div className="govuk-notification-banner govuk-notification-banner--success" role="region" aria-labelledby="govuk-notification-banner-title">
      <div className="govuk-notification-banner__header">
        <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title">
          🤖 AI-Generated Scenario
        </h2>
      </div>
      <div className="govuk-notification-banner__content">
        <h3 className="govuk-notification-banner__heading">
          {aiScenarioInfo.generated_scenario}
        </h3>
        <p className="govuk-body">
          <strong>Borough:</strong> {aiScenarioInfo.borough} • 
          <strong> Framework Compliant:</strong> {aiScenarioInfo.framework_compliant ? 'Yes' : 'No'} • 
          <strong> Template:</strong> {aiScenarioInfo.template_used}
        </p>
        
        <details className="govuk-details" data-module="govuk-details">
          <summary className="govuk-details__summary">
            <span className="govuk-details__summary-text">
              View AI scenario details
            </span>
          </summary>
          <div className="govuk-details__text">
            <div className="govuk-grid-row">
              <div className="govuk-grid-column-full">
                <h4 className="govuk-heading-s">Original AI Intent</h4>
                <div className="govuk-inset-text">
                  "{aiScenarioInfo.intent}"
                </div>
                
                {aiScenarioInfo.description && (
                  <>
                    <h4 className="govuk-heading-s">Generated Scenario Description</h4>
                    <p className="govuk-body">{aiScenarioInfo.description}</p>
                  </>
                )}
                
                <h4 className="govuk-heading-s">How This Works</h4>
                <p className="govuk-body">
                  The AI analyzed your borough's characteristics and generated a scenario intent. 
                  This was then used to select and configure an appropriate framework-compliant scenario.
                  The results below show how this AI-selected scenario performs compared to other standard scenarios.
                </p>
                
                <div className="govuk-warning-text">
                  <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                  <strong className="govuk-warning-text__text">
                    <span className="govuk-warning-text__assistive">Important</span>
                    The scenarios shown below are framework-compliant templates. The AI's role was to intelligently select 
                    and contextualize the most appropriate scenario for {aiScenarioInfo.borough} based on your planning intent.
                  </strong>
                </div>
                
                <p className="govuk-body-s">
                  <strong>Generated:</strong> {new Date(aiScenarioInfo.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default AIScenarioBanner;
