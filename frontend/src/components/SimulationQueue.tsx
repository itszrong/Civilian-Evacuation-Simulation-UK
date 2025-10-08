/**
 * Simulation Queue Component
 * Manages simulation requests triggered by civil unrest detection
 * GOV.UK Design System implementation
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG } from '../config/api';
import { notificationStore } from './govuk/Notification';

interface SimulationRequest {
  id: string;
  article_id: string;
  article_title: string;
  article_summary: string;
  civil_unrest_score: number;
  suggested_regions: string[];
  status: 'pending' | 'approved' | 'rejected' | 'running' | 'completed' | 'failed';
  created_at: string;
  approved_at?: string;
  approved_by?: string;
  rejection_reason?: string;
  scenario_id?: string;
  simulation_results?: {
    error?: string;
    error_type?: string;
    traceback?: string;
  };
}

interface UnrestArticle {
  id: string;
  title: string;
  summary: string;
  link: string;
  published: string;
  source: string;
  civil_unrest_score: number;
  civil_unrest_indicators: string[];
  requires_simulation: boolean;
  suggested_regions: string[];
}

interface QueueStats {
  total_requests: number;
  pending: number;
  approved: number;
  rejected: number;
  running: number;
  completed: number;
}

const SimulationQueue: React.FC = () => {
  const [requests, setRequests] = useState<SimulationRequest[]>([]);
  const [candidates, setCandidates] = useState<UnrestArticle[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<SimulationRequest | null>(null);
  const [approvalReason, setApprovalReason] = useState('');
  const [customRegions, setCustomRegions] = useState<string>('');
  const [activeView, setActiveView] = useState<'queue' | 'candidates' | 'analysis'>('queue');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [queueResponse, candidatesResponse, statsResponse] = await Promise.all([
        fetch(`${API_CONFIG.baseUrl}/api/simulation-queue/requests`),
        fetch(`${API_CONFIG.baseUrl}/api/civil-unrest/candidates`),
        fetch(`${API_CONFIG.baseUrl}/api/simulation-queue/stats`)
      ]);

      if (queueResponse.ok) {
        const queueData = await queueResponse.json();
        setRequests(queueData);
      }

      if (candidatesResponse.ok) {
        const candidatesData = await candidatesResponse.json();
        setCandidates(candidatesData);
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error('Failed to load queue data:', error);
        notificationStore.show({
          type: 'error',
          title: 'Loading Error',
          message: 'Failed to load simulation queue data'
        });
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRequest = async (requestId: string, action: 'approve' | 'reject') => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/simulation-queue/requests/${requestId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action,
          approved_by: 'Emergency Planning Officer', // In real app, get from auth
          rejection_reason: action === 'reject' ? approvalReason : undefined,
          custom_regions: customRegions ? customRegions.split(',').map(r => r.trim()) : undefined
        }),
      });

      if (response.ok) {
        notificationStore.show({
          type: 'success',
          title: `Request ${action === 'approve' ? 'Approved' : 'Rejected'}`,
          message: `Simulation request has been ${action}d successfully`
        });
        setSelectedRequest(null);
        setApprovalReason('');
        setCustomRegions('');
        loadData();
      } else {
        throw new Error(`Failed to ${action} request`);
      }
    } catch (error) {
      notificationStore.show({
        type: 'error',
        title: 'Action Failed',
        message: `Failed to ${action} simulation request`
      });
    }
  };

  const handleQueueSimulation = async (articleId: string) => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/civil-unrest/queue-simulation/${articleId}`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        notificationStore.show({
          type: 'success',
          title: 'Simulation Queued',
          message: result.message
        });
        loadData();
      } else {
        throw new Error('Failed to queue simulation');
      }
    } catch (error) {
      notificationStore.show({
        type: 'error',
        title: 'Queue Failed',
        message: 'Failed to queue simulation request'
      });
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusTag = (status: string) => {
    const statusClasses = {
      pending: 'govuk-tag--yellow',
      approved: 'govuk-tag--green',
      rejected: 'govuk-tag--red',
      running: 'govuk-tag--blue',
      completed: 'govuk-tag--grey'
    };

    return (
      <strong className={`govuk-tag ${statusClasses[status as keyof typeof statusClasses] || ''}`}>
        {status.toUpperCase()}
      </strong>
    );
  };

  const getRiskLevel = (score: number) => {
    if (score >= 8) return { level: 'Critical', class: 'govuk-tag--red' };
    if (score >= 6) return { level: 'High', class: 'govuk-tag--orange' };
    if (score >= 4) return { level: 'Medium', class: 'govuk-tag--yellow' };
    return { level: 'Low', class: 'govuk-tag--grey' };
  };

  if (loading) {
    return (
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <p className={GOVUK_CLASSES.body.m}>Loading simulation queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-full">
        
        {/* Queue Statistics */}
        {stats && (
          <div className="govuk-notification-banner" role="region">
            <div className="govuk-notification-banner__header">
              <h2 className="govuk-notification-banner__title">Queue Status</h2>
            </div>
            <div className="govuk-notification-banner__content">
              <p className={GOVUK_CLASSES.body.m}>
                <strong>{stats.pending} pending</strong>, {stats.approved} approved, {stats.rejected} rejected, {stats.running} running, {stats.completed} completed
              </p>
            </div>
          </div>
        )}

        {/* Sub-navigation */}
        <nav className="govuk-breadcrumbs" style={{ marginBottom: '30px' }}>
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <button 
                className={`govuk-link ${activeView === 'queue' ? 'govuk-!-font-weight-bold' : ''}`}
                onClick={() => setActiveView('queue')}
              >
                Queue ({stats?.pending || 0})
              </button>
            </li>
            <li className="govuk-breadcrumbs__list-item">
              <button 
                className={`govuk-link ${activeView === 'candidates' ? 'govuk-!-font-weight-bold' : ''}`}
                onClick={() => setActiveView('candidates')}
              >
                Candidates ({candidates.length})
              </button>
            </li>
            <li className="govuk-breadcrumbs__list-item">
              <button 
                className={`govuk-link ${activeView === 'analysis' ? 'govuk-!-font-weight-bold' : ''}`}
                onClick={() => setActiveView('analysis')}
              >
                Analysis
              </button>
            </li>
          </ol>
        </nav>

        {/* Queue View */}
        {activeView === 'queue' && (
          <div>
            <h2 className={GOVUK_CLASSES.heading.l}>Simulation Requests</h2>
            
            {requests.length === 0 ? (
              <div className="govuk-inset-text">
                <p>No simulation requests in queue.</p>
              </div>
            ) : (
              <div className="govuk-grid-row">
                {requests.map((request) => (
                  <div key={request.id} className="govuk-grid-column-full" style={{ marginBottom: '20px' }}>
                    <div className="govuk-summary-card">
                      <div className="govuk-summary-card__title-wrapper">
                        <h3 className="govuk-summary-card__title">
                          {request.article_title}
                        </h3>
                        <ul className="govuk-summary-card__actions">
                          <li className="govuk-summary-card__action">
                            {getStatusTag(request.status)}
                          </li>
                        </ul>
                      </div>
                      <div className="govuk-summary-card__content">
                        <dl className="govuk-summary-list">
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Risk Score</dt>
                            <dd className="govuk-summary-list__value">
                              <strong className={`govuk-tag ${getRiskLevel(request.civil_unrest_score).class}`}>
                                {request.civil_unrest_score.toFixed(1)} - {getRiskLevel(request.civil_unrest_score).level}
                              </strong>
                            </dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Affected Regions</dt>
                            <dd className="govuk-summary-list__value">
                              {request.suggested_regions.join(', ') || 'Not specified'}
                            </dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Created</dt>
                            <dd className="govuk-summary-list__value">
                              {formatDateTime(request.created_at)}
                            </dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Summary</dt>
                            <dd className="govuk-summary-list__value">
                              {request.article_summary.substring(0, 200)}...
                            </dd>
                          </div>
                        </dl>
                        
                        {request.status === 'pending' && (
                          <div className="govuk-button-group" style={{ marginTop: '20px' }}>
                            <button 
                              className={GOVUK_CLASSES.button.primary}
                              onClick={() => setSelectedRequest(request)}
                            >
                              Review Request
                            </button>
                          </div>
                        )}
                        
                        {request.status === 'approved' && (
                          <div className="govuk-button-group" style={{ marginTop: '20px' }}>
                            <button 
                              className={GOVUK_CLASSES.button.primary}
                              onClick={() => handleApproveRequest(request.id, 'approve')}
                            >
                              Start Simulation
                            </button>
                          </div>
                        )}
                        
                        {request.status === 'failed' && (
                          <div style={{ marginTop: '20px' }}>
                            <div className="govuk-warning-text">
                              <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                              <strong className="govuk-warning-text__text">
                                <span className="govuk-warning-text__assistive">Warning: </span>
                                Simulation failed
                              </strong>
                            </div>
                            {request.simulation_results?.error && (
                              <details className="govuk-details" style={{ marginBottom: '20px' }}>
                                <summary className="govuk-details__summary">
                                  <span className="govuk-details__summary-text">
                                    View Error Details
                                  </span>
                                </summary>
                                <div className="govuk-details__text">
                                  <p className="govuk-body-s">
                                    <strong>Error:</strong> {request.simulation_results.error}
                                  </p>
                                  {request.simulation_results.error_type && (
                                    <p className="govuk-body-s">
                                      <strong>Type:</strong> {request.simulation_results.error_type}
                                    </p>
                                  )}
                                </div>
                              </details>
                            )}
                            <div className="govuk-button-group">
                              <button 
                                className={GOVUK_CLASSES.button.primary}
                                onClick={() => handleApproveRequest(request.id, 'approve')}
                              >
                                Retry Simulation
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Candidates View */}
        {activeView === 'candidates' && (
          <div>
            <h2 className={GOVUK_CLASSES.heading.l}>Simulation Candidates</h2>
            <p className={GOVUK_CLASSES.body.m}>
              Articles detected with civil unrest indicators that may require evacuation simulation.
            </p>
            
            {candidates.length === 0 ? (
              <div className="govuk-inset-text">
                <p>No simulation candidates detected.</p>
              </div>
            ) : (
              <div className="govuk-grid-row">
                {candidates.map((article) => (
                  <div key={article.id} className="govuk-grid-column-full" style={{ marginBottom: '20px' }}>
                    <div className="govuk-summary-card">
                      <div className="govuk-summary-card__title-wrapper">
                        <h3 className="govuk-summary-card__title">
                          <a href={article.link} target="_blank" rel="noopener noreferrer" className="govuk-link">
                            {article.title}
                          </a>
                        </h3>
                        <ul className="govuk-summary-card__actions">
                          <li className="govuk-summary-card__action">
                            <strong className={`govuk-tag ${getRiskLevel(article.civil_unrest_score).class}`}>
                              {article.civil_unrest_score.toFixed(1)}
                            </strong>
                          </li>
                        </ul>
                      </div>
                      <div className="govuk-summary-card__content">
                        <dl className="govuk-summary-list">
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Source</dt>
                            <dd className="govuk-summary-list__value">{article.source}</dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Published</dt>
                            <dd className="govuk-summary-list__value">
                              {formatDateTime(article.published)}
                            </dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Suggested Regions</dt>
                            <dd className="govuk-summary-list__value">
                              {article.suggested_regions.join(', ') || 'Not specified'}
                            </dd>
                          </div>
                          <div className="govuk-summary-list__row">
                            <dt className="govuk-summary-list__key">Risk Indicators</dt>
                            <dd className="govuk-summary-list__value">
                              <ul className="govuk-list govuk-list--bullet">
                                {article.civil_unrest_indicators.slice(0, 3).map((indicator, index) => (
                                  <li key={index}>{indicator}</li>
                                ))}
                              </ul>
                            </dd>
                          </div>
                        </dl>
                        
                        <div className="govuk-button-group" style={{ marginTop: '20px' }}>
                          <button 
                            className={GOVUK_CLASSES.button.primary}
                            onClick={() => handleQueueSimulation(article.id)}
                          >
                            Queue Simulation
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Analysis View */}
        {activeView === 'analysis' && (
          <div>
            <h2 className={GOVUK_CLASSES.heading.l}>Civil Unrest Analysis</h2>
            <p className={GOVUK_CLASSES.body.m}>
              Real-time analysis of news feeds for civil unrest indicators and evacuation planning triggers.
            </p>
            
            <div className="govuk-inset-text">
              <p>Analysis dashboard coming soon. This will include:</p>
              <ul className="govuk-list govuk-list--bullet">
                <li>Risk score trends over time</li>
                <li>Geographic heat maps of detected incidents</li>
                <li>Source reliability metrics</li>
                <li>Automated threat escalation workflows</li>
              </ul>
            </div>
          </div>
        )}

        {/* Approval Modal */}
        {selectedRequest && (
          <div className="govuk-modal-overlay" style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div className="govuk-modal" style={{
              backgroundColor: 'white',
              padding: '30px',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto'
            }}>
              <h2 className={GOVUK_CLASSES.heading.l}>Review Simulation Request</h2>
              
              <dl className="govuk-summary-list">
                <div className="govuk-summary-list__row">
                  <dt className="govuk-summary-list__key">Article</dt>
                  <dd className="govuk-summary-list__value">{selectedRequest.article_title}</dd>
                </div>
                <div className="govuk-summary-list__row">
                  <dt className="govuk-summary-list__key">Risk Score</dt>
                  <dd className="govuk-summary-list__value">
                    <strong className={`govuk-tag ${getRiskLevel(selectedRequest.civil_unrest_score).class}`}>
                      {selectedRequest.civil_unrest_score.toFixed(1)}
                    </strong>
                  </dd>
                </div>
                <div className="govuk-summary-list__row">
                  <dt className="govuk-summary-list__key">Suggested Regions</dt>
                  <dd className="govuk-summary-list__value">
                    {selectedRequest.suggested_regions.join(', ')}
                  </dd>
                </div>
              </dl>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="custom-regions">
                  Custom Regions (optional)
                </label>
                <div className="govuk-hint">
                  Override suggested regions with comma-separated list
                </div>
                <input
                  className={GOVUK_CLASSES.form.input}
                  id="custom-regions"
                  type="text"
                  value={customRegions}
                  onChange={(e) => setCustomRegions(e.target.value)}
                  placeholder="Westminster, Camden, Islington"
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="approval-reason">
                  Reason (required for rejection)
                </label>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="approval-reason"
                  rows={3}
                  value={approvalReason}
                  onChange={(e) => setApprovalReason(e.target.value)}
                  placeholder="Provide reason for approval or rejection..."
                />
              </div>

              <div className="govuk-button-group">
                <button 
                  className={GOVUK_CLASSES.button.primary}
                  onClick={() => handleApproveRequest(selectedRequest.id, 'approve')}
                >
                  Approve Simulation
                </button>
                <button 
                  className={GOVUK_CLASSES.button.warning}
                  onClick={() => handleApproveRequest(selectedRequest.id, 'reject')}
                >
                  Reject Request
                </button>
                <button 
                  className={GOVUK_CLASSES.button.secondary}
                  onClick={() => setSelectedRequest(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default SimulationQueue;
