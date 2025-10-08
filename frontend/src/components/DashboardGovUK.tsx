/**
 * Dashboard component for Civilian Evacuation Planning Tool
 * GOV.UK Design System implementation
 */

import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { GOVUK_CLASSES } from '../theme/govuk';
import { useDashboardContextInjection } from '../hooks/useContextInjection';

const DashboardGovUK: React.FC = () => {
  // Inject dashboard context for chat
  useDashboardContextInjection(
    {
      total_runs: 0,
      average_evacuation_time: null,
      success_rate: null
    },
    [],
    { status: 'operational' },
    false,
    null,
    'Prime Minister'
  );

  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>
        
        {/* Service overview */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <h1 className={GOVUK_CLASSES.heading.xl}>Emergency Planning Dashboard</h1>
          <p className={GOVUK_CLASSES.body.lead}>
            Evacuation planning system providing real-time analysis and simulation capabilities 
            for emergency response coordination across UK cities and boroughs.
          </p>
        </div>

        {/* Key capabilities */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <h2 className={GOVUK_CLASSES.heading.l}>Key Capabilities</h2>
          
          <ul className="govuk-list govuk-list--bullet">
            <li><strong>Real-time threat detection</strong> from government and news sources</li>
            <li><strong>Network simulation</strong> using A* pathfinding on real street data</li>
            <li><strong>Multi-agent AI</strong> for scenario generation and evaluation</li>
            <li><strong>Performance metrics</strong> with traffic light indicators and trend analysis</li>
          </ul>
        </div>

        {/* Quick actions */}
        <div className={`${GOVUK_CLASSES.gridRow} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <div className={GOVUK_CLASSES.gridColumn.half}>
            <div className="govuk-panel govuk-panel--confirmation">
              <h2 className="govuk-panel__title">Borough Dashboard</h2>
              <div className="govuk-panel__body">
                <p className={GOVUK_CLASSES.body.m}>
                  View traffic light status and manage simulations for all London boroughs
                </p>
                <Link to="/boroughs" className={`${GOVUK_CLASSES.button.start} ${GOVUK_CLASSES.spacing.marginTop[3]}`}>
                  View Boroughs
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
                </Link>
              </div>
            </div>
          </div>

          <div className={GOVUK_CLASSES.gridColumn.half}>
            <div className="govuk-panel">
              <h2 className="govuk-panel__title">View Results</h2>
              <div className="govuk-panel__body">
                <p className={GOVUK_CLASSES.body.m}>
                  Review completed evacuation scenarios and analysis
                </p>
                <Link to="/results" className={`${GOVUK_CLASSES.button.secondary} ${GOVUK_CLASSES.spacing.marginTop[3]}`}>
                  View Results
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* System status */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <h2 className={GOVUK_CLASSES.heading.m}>System Status</h2>
          
          <dl className={GOVUK_CLASSES.summaryList.container}>
            <div className={GOVUK_CLASSES.summaryList.row}>
              <dt className={GOVUK_CLASSES.summaryList.key}>
                Backend Service
              </dt>
              <dd className={GOVUK_CLASSES.summaryList.value}>
                <span className={`${GOVUK_CLASSES.tag.green}`}>
                  Operational
                </span>
              </dd>
            </div>
            <div className={GOVUK_CLASSES.summaryList.row}>
              <dt className={GOVUK_CLASSES.summaryList.key}>
                Multi-Agent System
              </dt>
              <dd className={GOVUK_CLASSES.summaryList.value}>
                <span className={`${GOVUK_CLASSES.tag.blue}`}>
                  Ready
                </span>
              </dd>
            </div>
            <div className={GOVUK_CLASSES.summaryList.row}>
              <dt className={GOVUK_CLASSES.summaryList.key}>
                Data Sources
              </dt>
              <dd className={GOVUK_CLASSES.summaryList.value}>
                <Link to="/sources" className="govuk-link">
                  View data feeds
                </Link>
              </dd>
            </div>
          </dl>
        </div>

        {/* Recent activity placeholder */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <h2 className={GOVUK_CLASSES.heading.m}>Recent Planning Runs</h2>
          
          <div className={GOVUK_CLASSES.insetText}>
            <p>No recent planning runs found. <Link to="/plan" className="govuk-link">Start your first evacuation planning run</Link>.</p>
          </div>
        </div>

        {/* Purpose */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <div className="govuk-warning-text">
            <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
            <strong className="govuk-warning-text__text">
              <span className="govuk-warning-text__assistive">Warning: </span>
              Emergency evacuation planning is critical for public safety and national security
            </strong>
          </div>
          
          <p className={GOVUK_CLASSES.body.m}>
            This system provides evidence-based insights for government decision makers and emergency services, 
            enabling rapid response to natural disasters, infrastructure failures, security threats, and civil unrest.
          </p>
        </div>

        {/* Information panel */}
        <div className="govuk-notification-banner" role="region" aria-labelledby="govuk-notification-banner-title">
          <div className="govuk-notification-banner__header">
            <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title">
              Important
            </h2>
          </div>
          <div className="govuk-notification-banner__content">
            <h3 className="govuk-notification-banner__heading">
              Multi-Agent Evacuation Planning System
            </h3>
            <p className={GOVUK_CLASSES.body.m}>
              This system uses specialized AI agents to generate, simulate, evaluate and explain civilian evacuation scenarios for emergency planning purposes.
            </p>
            <p className={GOVUK_CLASSES.body.m}>
              All planning runs are logged and can be reviewed for audit and improvement purposes.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DashboardGovUK;
