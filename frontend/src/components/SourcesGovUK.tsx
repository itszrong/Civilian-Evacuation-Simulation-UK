/**
 * Sources component for Civilian Evacuation Planning Tool
 * GOV.UK Design System implementation
 * Manages data source configuration, feed status, and government data compliance
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { notificationStore } from './govuk/Notification';
import SimulationQueue from './SimulationQueue';
import { useSourcesContextInjection } from '../hooks/useContextInjection';

interface SourceInfo {
  name: string;
  type: 'api' | 'rss' | 'gov_api';
  tier: 'gov_primary' | 'news_verified';
  last_updated: string | null;
  last_error: string | null;
  documents_count: number;
  status: 'healthy' | 'error' | 'stale' | 'disabled';
  url?: string;
  description: string;
  compliance: {
    gdpr_compliant: boolean;
    data_classification: 'official' | 'official_sensitive' | 'secret';
    retention_days: number;
  };
}

interface FeedsStatus {
  timestamp: string;
  total_sources: number;
  healthy_sources: number;
  last_refresh: string | null;
  last_global_refresh: string | null;
  feeds: {
    gov_primary: SourceInfo[];
    news_verified: SourceInfo[];
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

interface UnrestAnalysis {
  total_articles: number;
  unrest_articles: number;
  simulation_candidates: number;
  highest_score: number;
  articles: UnrestArticle[];
}

const SourcesGovUK: React.FC = () => {
  const [feedsStatus, setFeedsStatus] = useState<FeedsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<'all' | 'gov_primary' | 'news_verified' | 'rss_feeds' | 'api_endpoints'>('all');
  const [activeTab, setActiveTab] = useState<'sources' | 'queue' | 'unrest'>('sources');
  const [unrestAnalysis, setUnrestAnalysis] = useState<UnrestAnalysis | null>(null);
  const [loadingUnrest, setLoadingUnrest] = useState(false);
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [newSourceForm, setNewSourceForm] = useState({
    name: '',
    url: '',
    description: '',
    type: 'rss' as 'rss' | 'api'
  });

  // Inject context for chat integration
  useSourcesContextInjection(
    feedsStatus,
    unrestAnalysis,
    null, // simulationQueue - would need to be passed from SimulationQueue component
    activeTab,
    selectedTier,
    loading || loadingUnrest,
    error,
    'Prime Minister' // This should come from user context/auth
  );

  // Minimal fallback status for when feeds API is unavailable
  const fallbackFeedsStatus: FeedsStatus = {
    timestamp: new Date().toISOString(),
    total_sources: 0,
    healthy_sources: 0,
    last_refresh: null,
    last_global_refresh: null,
    feeds: {
      gov_primary: [],
      news_verified: []
    }
  };

  // Load public safety flags analysis
  const loadUnrestAnalysis = async () => {
    setLoadingUnrest(true);
    
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/civil-unrest/analysis?min_score=5.0&limit=20`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Public safety flags API response:', data);
        setUnrestAnalysis(data);
      } else {
        console.warn('Public safety flags API response not OK:', response.status, response.statusText);
        // Use minimal fallback when API unavailable
        setUnrestAnalysis({
          total_articles: 0,
          unrest_articles: 0,
          simulation_candidates: 0,
          highest_score: 0,
          articles: []
        });
      }
    } catch (err) {
      console.warn('Failed to fetch public safety flags analysis:', err);
      // Use minimal fallback when API unavailable
      setUnrestAnalysis({
        total_articles: 0,
        unrest_articles: 0,
        simulation_candidates: 0,
        highest_score: 0,
        articles: []
      });
    } finally {
      setLoadingUnrest(false);
    }
  };

  // Load feeds status
  useEffect(() => {
    const loadFeedsStatus = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Try to fetch from backend, fall back to fallback data
        const response = await fetch(`${API_CONFIG.baseUrl}/api/feeds/status`);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Feeds API response:', data);
          
          // Validate and transform API data structure
          if (data && data.feeds) {
            // API returns feeds.gov_primary.sources, but component expects feeds.gov_primary to be array
            // Add tier information to each source
            const govPrimarySources = Array.isArray(data.feeds.gov_primary?.sources) 
              ? data.feeds.gov_primary.sources.map(source => ({ ...source, tier: 'gov_primary' }))
              : [];
            const newsVerifiedSources = Array.isArray(data.feeds.news_verified?.sources)
              ? data.feeds.news_verified.sources.map(source => ({ ...source, tier: 'news_verified' }))
              : [];
              
            // Calculate system status metrics
            const allSources = [...govPrimarySources, ...newsVerifiedSources];
            const operationalSources = allSources.filter(source => 
              source.status === 'operational'
            );
            
            const transformedData = {
              ...data,
              feeds: {
                gov_primary: govPrimarySources,
                news_verified: newsVerifiedSources
              },
              total_sources: allSources.length,
              healthy_sources: operationalSources.length,
              last_global_refresh: data.last_global_refresh
            };
            setFeedsStatus(transformedData);
          } else {
            console.warn('Invalid API data structure, using fallback:', data);
            setFeedsStatus(fallbackFeedsStatus);
          }
        } else {
          console.warn('API response not OK:', response.status, response.statusText);
          // Use minimal fallback when API unavailable
          setFeedsStatus(fallbackFeedsStatus);
        }
      } catch (err) {
        console.warn('Failed to fetch feeds status, using fallback:', err);
        setFeedsStatus(fallbackFeedsStatus);
      } finally {
        setLoading(false);
      }
    };

    loadFeedsStatus();
    loadUnrestAnalysis();
  }, []);

  const handleRefreshFeeds = async () => {
    setRefreshing(true);
    
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/feeds/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        notificationStore.show({
          title: 'Feeds Refreshed',
          message: 'All data sources have been refreshed successfully',
          type: 'success'
        });
        
        // Reload status and civil unrest data
        setLoading(true);
        setTimeout(() => {
          // Reload feeds status from API after refresh
          const loadFeedsStatus = async () => {
            try {
              const response = await fetch(`${API_CONFIG.baseUrl}/api/feeds/status`);
              if (response.ok) {
                const data = await response.json();
                // Add tier information to sources
                const govPrimarySources = Array.isArray(data.feeds.gov_primary?.sources) 
                  ? data.feeds.gov_primary.sources.map(source => ({ ...source, tier: 'gov_primary' }))
                  : [];
                const newsVerifiedSources = Array.isArray(data.feeds.news_verified?.sources)
                  ? data.feeds.news_verified.sources.map(source => ({ ...source, tier: 'news_verified' }))
                  : [];
                  
                // Calculate system status metrics
                const allSources = [...govPrimarySources, ...newsVerifiedSources];
                const operationalSources = allSources.filter(source => 
                  source.status === 'operational'
                );
                
                setFeedsStatus({
                  ...data,
                  feeds: {
                    gov_primary: govPrimarySources,
                    news_verified: newsVerifiedSources
                  },
                  total_sources: allSources.length,
                  healthy_sources: operationalSources.length,
                  last_global_refresh: data.last_global_refresh,
                  last_refresh: new Date().toISOString()
                });
              } else {
                setFeedsStatus({ ...fallbackFeedsStatus, last_refresh: new Date().toISOString() });
              }
            } catch (err) {
              setFeedsStatus({ ...fallbackFeedsStatus, last_refresh: new Date().toISOString() });
            }
          };
          loadFeedsStatus();
          setLoading(false);
          loadUnrestAnalysis(); // Also refresh public safety flags data
        }, 1000);
      } else {
        throw new Error('Failed to refresh feeds');
      }
    } catch (err) {
      notificationStore.show({
        title: 'Refresh Failed',
        message: err instanceof Error ? err.message : 'Failed to refresh data sources',
        type: 'error'
      });
    } finally {
      setRefreshing(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    if (!dateString) return 'Never';
    
    try {
      // Backend sends naive timestamps - treat as UTC and add 'Z' suffix
      const utcDateString = dateString.includes('Z') || dateString.includes('+') 
        ? dateString 
        : dateString + 'Z';
      
      const date = new Date(utcDateString);
      if (isNaN(date.getTime())) {
        return 'Invalid Date';
      }
      
      // Format in London timezone (automatically handles BST/GMT)
      return date.toLocaleString('en-GB', {
        timeZone: 'Europe/London',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch (error) {
      console.error('Date formatting error:', error, 'for dateString:', dateString);
      return 'Invalid Date';
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      'healthy': GOVUK_CLASSES.tag.green,
      'operational': GOVUK_CLASSES.tag.green,
      'configured': GOVUK_CLASSES.tag.blue,
      'error': GOVUK_CLASSES.tag.red,
      'stale': GOVUK_CLASSES.tag.orange,
      'disabled': GOVUK_CLASSES.tag.grey,
      'unconfigured': GOVUK_CLASSES.tag.grey
    };
    return statusMap[status as keyof typeof statusMap] || GOVUK_CLASSES.tag.grey;
  };

  const getStatusDisplayText = (status: string) => {
    const displayMap = {
      'healthy': 'Healthy',
      'operational': 'Operational',
      'configured': 'Configured',
      'error': 'Error',
      'stale': 'Stale',
      'disabled': 'Disabled',
      'unconfigured': 'Unconfigured'
    };
    return displayMap[status as keyof typeof displayMap] || (status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown');
  };

  const getTierDisplayName = (tier: string) => {
    return tier === 'gov_primary' ? 'Government Primary' : 'Verified News';
  };

  const getDataClassificationTag = (classification: string) => {
    const classMap = {
      'official': GOVUK_CLASSES.tag.blue,
      'official_sensitive': GOVUK_CLASSES.tag.orange,
      'secret': GOVUK_CLASSES.tag.red
    };
    return classMap[classification as keyof typeof classMap] || GOVUK_CLASSES.tag.grey;
  };

  const getFilteredSources = () => {
    if (!feedsStatus || !feedsStatus.feeds) return [];
    
    let sources: SourceInfo[] = [];
    
    try {
      const govPrimary = Array.isArray(feedsStatus.feeds.gov_primary) ? feedsStatus.feeds.gov_primary : [];
      const newsVerified = Array.isArray(feedsStatus.feeds.news_verified) ? feedsStatus.feeds.news_verified : [];
      const allSources = [...govPrimary, ...newsVerified];
      
      if (selectedTier === 'all') {
        sources = allSources;
      } else if (selectedTier === 'gov_primary') {
        sources = govPrimary;
      } else if (selectedTier === 'news_verified') {
        sources = newsVerified;
      } else if (selectedTier === 'rss_feeds') {
        // Filter for RSS feeds (type: "rss")
        sources = allSources.filter(source => 
          source.name === 'BBC News London' || source.name === 'Sky News London'
        );
      } else if (selectedTier === 'api_endpoints') {
        // Filter for API endpoints (type: "api")  
        sources = allSources.filter(source => 
          source.name !== 'BBC News London' && source.name !== 'Sky News London'
        );
      }
    } catch (error) {
      console.error('Error filtering sources:', error);
      return [];
    }
    
    return sources;
  };

  const getRiskScoreTag = (score: number) => {
    if (score >= 7) return GOVUK_CLASSES.tag.red;
    if (score >= 4) return GOVUK_CLASSES.tag.orange;
    if (score >= 2) return GOVUK_CLASSES.tag.blue;
    return GOVUK_CLASSES.tag.green;
  };

  const getRiskLevel = (score: number) => {
    if (score >= 7) return 'High Risk';
    if (score >= 4) return 'Medium Risk';
    if (score >= 2) return 'Low Risk';
    return 'Minimal Risk';
  };

  const stripHtml = (html: string) => {
    if (!html) return '';
    // Remove HTML tags and decode HTML entities
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  };

  const getSourceType = (sourceName: string) => {
    // Determine source type based on name (since backend doesn't provide type field)
    if (sourceName === 'BBC News London' || sourceName === 'Sky News London') {
      return 'RSS';
    }
    return 'API';
  };

  const handleAddSource = async () => {
    if (!newSourceForm.name || !newSourceForm.url) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      // For now, just show success message since backend endpoint may not exist
      alert(`RSS feed "${newSourceForm.name}" would be added to the system.\n\nURL: ${newSourceForm.url}\nDescription: ${newSourceForm.description}`);
      
      // Reset form and close modal
      setNewSourceForm({
        name: '',
        url: '',
        description: '',
        type: 'rss'
      });
      setShowAddSourceModal(false);
      
      // Refresh feeds to show updated list
      handleRefreshFeeds();
    } catch (error) {
      console.error('Failed to add source:', error);
      alert('Failed to add source. Please try again.');
    }
  };

  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>
        
        {/* Page Header */}
        <span className="govuk-caption-xl">Data Management</span>
        <h1 className={GOVUK_CLASSES.heading.xl}>Data Sources & Feeds</h1>
        <p className={GOVUK_CLASSES.body.lead}>
          Monitor and manage government data sources used for evacuation planning intelligence
        </p>

        {/* System Status Overview */}
        {feedsStatus && (
          <div className="govuk-notification-banner" role="region" aria-labelledby="govuk-notification-banner-title">
            <div className="govuk-notification-banner__header">
              <h2 className="govuk-notification-banner__title" id="govuk-notification-banner-title">
                System Status
              </h2>
            </div>
            <div className="govuk-notification-banner__content">
              <p className={GOVUK_CLASSES.body.m}>
                <strong>{feedsStatus.healthy_sources} of {feedsStatus.total_sources} sources</strong> are operational. 
                Last refreshed: <strong>{formatDateTime(feedsStatus.last_global_refresh)}</strong>
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <div className="govuk-button-group">
            <button 
              className={`${GOVUK_CLASSES.button.primary} ${refreshing ? 'govuk-button--disabled' : ''}`}
              onClick={handleRefreshFeeds}
              disabled={refreshing}
            >
              {refreshing ? 'Refreshing...' : 'Refresh All Sources'}
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="govuk-tabs" data-module="govuk-tabs">
          <h2 className="govuk-tabs__title">Contents</h2>
          <ul className="govuk-tabs__list">
            <li className={`govuk-tabs__list-item ${activeTab === 'sources' ? 'govuk-tabs__list-item--selected' : ''}`}>
              <a 
                className="govuk-tabs__tab" 
                href="#sources"
                onClick={(e) => { 
                  e.preventDefault(); 
                  setActiveTab('sources');
                  setTimeout(() => {
                    document.getElementById('sources')?.scrollIntoView({ behavior: 'smooth' });
                  }, 100);
                }}
              >
                Data Sources
              </a>
            </li>
            <li className={`govuk-tabs__list-item ${activeTab === 'unrest' ? 'govuk-tabs__list-item--selected' : ''}`}>
              <a 
                className="govuk-tabs__tab" 
                href="#unrest"
                onClick={(e) => { 
                  e.preventDefault(); 
                  setActiveTab('unrest');
                  setTimeout(() => {
                    document.getElementById('unrest')?.scrollIntoView({ behavior: 'smooth' });
                  }, 100);
                }}
              >
                Public Safety Flags
                {unrestAnalysis && unrestAnalysis.simulation_candidates > 0 && (
                  <span className="govuk-tag govuk-tag--red" style={{ marginLeft: '8px', fontSize: '12px' }}>
                    {unrestAnalysis.simulation_candidates}
                  </span>
                )}
              </a>
            </li>
          </ul>

          {/* Sources Tab Content */}
          <div className={`govuk-tabs__panel ${activeTab === 'sources' ? '' : 'govuk-tabs__panel--hidden'}`} id="sources">
            <h2 className={`${GOVUK_CLASSES.heading.l} ${GOVUK_CLASSES.spacing.marginBottom[4]}`}>Data Sources ({feedsStatus?.total_sources || 0})</h2>
            <p className={GOVUK_CLASSES.body.m}>Government data sources and their current operational status</p>
            
            {/* Filter Options */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <fieldset className={GOVUK_CLASSES.form.fieldset}>
            <legend className={`${GOVUK_CLASSES.form.legend} ${GOVUK_CLASSES.heading.s}`}>
              Filter by source type
            </legend>
            <div className="govuk-radios govuk-radios--inline">
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="tier-all" 
                  name="tier-filter" 
                  type="radio" 
                  value="all"
                  checked={selectedTier === 'all'}
                  onChange={(e) => setSelectedTier(e.target.value as any)}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="tier-all">
                  All Sources
                </label>
              </div>
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="tier-gov" 
                  name="tier-filter" 
                  type="radio" 
                  value="gov_primary"
                  checked={selectedTier === 'gov_primary'}
                  onChange={(e) => setSelectedTier(e.target.value as any)}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="tier-gov">
                  Government Primary
                </label>
              </div>
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="tier-news" 
                  name="tier-filter" 
                  type="radio" 
                  value="news_verified"
                  checked={selectedTier === 'news_verified'}
                  onChange={(e) => setSelectedTier(e.target.value as any)}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="tier-news">
                  Verified News
                </label>
              </div>
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="tier-rss" 
                  name="tier-filter" 
                  type="radio" 
                  value="rss_feeds"
                  checked={selectedTier === 'rss_feeds'}
                  onChange={(e) => setSelectedTier(e.target.value as any)}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="tier-rss">
                  RSS Feeds
                </label>
              </div>
              <div className="govuk-radios__item">
                <input 
                  className="govuk-radios__input" 
                  id="tier-api" 
                  name="tier-filter" 
                  type="radio" 
                  value="api_endpoints"
                  checked={selectedTier === 'api_endpoints'}
                  onChange={(e) => setSelectedTier(e.target.value as any)}
                />
                <label className="govuk-label govuk-radios__label" htmlFor="tier-api">
                  API Endpoints
                </label>
              </div>
            </div>
          </fieldset>
        </div>

        {/* Loading State */}
        {loading && (
          <div className={GOVUK_CLASSES.insetText}>
            <p>Loading data source status...</p>
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

        {/* Sources Table */}
        {feedsStatus && !loading && (
          <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
            <h2 className={GOVUK_CLASSES.heading.m}>
              Data Sources ({getFilteredSources().length})
            </h2>
            
            <table className={GOVUK_CLASSES.table.container}>
              <caption className={GOVUK_CLASSES.table.caption}>
                Government data sources and their current operational status
              </caption>
              <thead className={GOVUK_CLASSES.table.head}>
                <tr className={GOVUK_CLASSES.table.row}>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Source</th>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Type</th>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Status</th>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Documents</th>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Last Updated</th>
                  <th scope="col" className={GOVUK_CLASSES.table.header}>Classification</th>
                </tr>
              </thead>
              <tbody className={GOVUK_CLASSES.table.body}>
                {getFilteredSources().map((source, index) => (
                  <tr key={index} className={GOVUK_CLASSES.table.row}>
                    <td className={GOVUK_CLASSES.table.cell}>
                      <div>
                        <strong>{source.name}</strong>
                        <div className="govuk-hint" style={{ marginTop: '5px' }}>
                          {source.description}
                        </div>
                        <span className={`${GOVUK_CLASSES.tag.base} ${source.tier === 'gov_primary' ? 'govuk-tag--blue' : 'govuk-tag--purple'}`}>
                          {getTierDisplayName(source.tier)}
                        </span>
                      </div>
                    </td>
                    <td className={GOVUK_CLASSES.table.cell}>
                      <span className={`${GOVUK_CLASSES.tag.base} ${getSourceType(source.name) === 'RSS' ? 'govuk-tag--green' : 'govuk-tag--blue'}`}>
                        {getSourceType(source.name)}
                      </span>
                    </td>
                    <td className={GOVUK_CLASSES.table.cell}>
                      <span className={getStatusTag(source.status)}>
                        {getStatusDisplayText(source.status)}
                      </span>
                      {source.last_error && (
                        <div className="govuk-error-message" style={{ marginTop: '5px' }}>
                          {source.last_error}
                        </div>
                      )}
                    </td>
                    <td className={GOVUK_CLASSES.table.cell}>
                      {source.documents_count.toLocaleString()}
                    </td>
                    <td className={GOVUK_CLASSES.table.cell}>
                      {source.last_updated ? formatDateTime(source.last_updated) : 'Never'}
                    </td>
                    <td className={GOVUK_CLASSES.table.cell}>
                      <span className={getDataClassificationTag(source.compliance?.data_classification || 'official')}>
                        {source.compliance?.data_classification ? source.compliance.data_classification.replace('_', ' ').toUpperCase() : 'OFFICIAL'}
                      </span>
                      <div className="govuk-hint" style={{ marginTop: '5px' }}>
                        Retention: {source.compliance?.retention_days || 365} days
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Data Compliance Section */}
        <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
          <h2 className={GOVUK_CLASSES.heading.m}>Data Compliance & Governance</h2>
          
          <div className="govuk-warning-text">
            <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
            <strong className="govuk-warning-text__text">
              <span className="govuk-warning-text__assistive">Warning: </span>
              All data sources must comply with UK GDPR and government data classification standards
            </strong>
          </div>

          <details className={GOVUK_CLASSES.details.container}>
            <summary className={GOVUK_CLASSES.details.summary}>
              <span className={GOVUK_CLASSES.details.text}>
                Data classification guidelines
              </span>
            </summary>
            <div className={GOVUK_CLASSES.details.text}>
              <ul className="govuk-list govuk-list--bullet">
                <li><strong>OFFICIAL</strong>: Routine business information that could cause minimal damage if compromised</li>
                <li><strong>OFFICIAL-SENSITIVE</strong>: Information that requires additional care in handling</li>
                <li><strong>SECRET</strong>: Very sensitive information that could cause serious damage if compromised</li>
              </ul>
              <p>All emergency planning data is classified according to the Government Security Classifications Policy.</p>
            </div>
          </details>

          <details className={GOVUK_CLASSES.details.container}>
            <summary className={GOVUK_CLASSES.details.summary}>
              <span className={GOVUK_CLASSES.details.text}>
                Data retention policies
              </span>
            </summary>
            <div className={GOVUK_CLASSES.details.text}>
              <ul className="govuk-list govuk-list--bullet">
                <li><strong>Government Primary Sources</strong>: 7 years (2,555 days) for audit and legal compliance</li>
                <li><strong>Verified News Sources</strong>: 1 year (365 days) for operational reference</li>
                <li><strong>Simulation Results</strong>: 10 years for policy development and lessons learned</li>
              </ul>
              <p>Retention periods comply with the Public Records Act 1958 and departmental record management policies.</p>
            </div>
          </details>
        </div>

        {/* Quick Actions */}
        <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
          <h2 className={GOVUK_CLASSES.heading.m}>Quick Actions</h2>
          <div className="govuk-button-group">
            <button 
              className={GOVUK_CLASSES.button.secondary}
              onClick={() => setShowAddSourceModal(true)}
            >
              Add New Source
            </button>
          </div>
        </div>
          </div>

          {/* Public Safety Flags Tab Content */}
          <div className={`govuk-tabs__panel ${activeTab === 'unrest' ? '' : 'govuk-tabs__panel--hidden'}`} id="unrest">
            <h2 className={`${GOVUK_CLASSES.heading.l} ${GOVUK_CLASSES.spacing.marginBottom[4]}`}>Public Safety Flags</h2>
            <p className={GOVUK_CLASSES.body.m}>Real-time monitoring of public safety and security flags from news sources</p>
            
            {/* Unrest Analysis Overview */}
            {unrestAnalysis && (
              <div className="govuk-notification-banner govuk-notification-banner--warning" role="region" aria-labelledby="unrest-banner-title">
                <div className="govuk-notification-banner__header">
                  <h2 className="govuk-notification-banner__title" id="unrest-banner-title">
                    Public Safety Flag Detection
                  </h2>
                </div>
                <div className="govuk-notification-banner__content">
                  <p className={GOVUK_CLASSES.body.m}>
                    <strong>{unrestAnalysis.unrest_articles} of {unrestAnalysis.total_articles} articles</strong> show public safety flag indicators.
                    <strong> {unrestAnalysis.simulation_candidates} articles</strong> require immediate simulation review.
                    {unrestAnalysis.highest_score > 0 && (
                      <> Highest risk score: <strong>{unrestAnalysis.highest_score.toFixed(1)}/10</strong></>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Loading State */}
            {loadingUnrest && (
              <div className={GOVUK_CLASSES.insetText}>
                <p>Loading public safety flags analysis...</p>
              </div>
            )}

            {/* Articles Table */}
            {unrestAnalysis && !loadingUnrest && (
              <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
                <h2 className={GOVUK_CLASSES.heading.m}>
                  Articles with Public Safety Flag Indicators ({unrestAnalysis.articles.length})
                </h2>
                
                {unrestAnalysis.articles.length === 0 ? (
                  <div className={GOVUK_CLASSES.insetText}>
                    <p>No articles with public safety flag indicators found in recent feeds.</p>
                  </div>
                ) : (
                  <table className={GOVUK_CLASSES.table.container}>
                    <caption className={GOVUK_CLASSES.table.caption}>
                      News articles analyzed for public safety and security flag indicators
                    </caption>
                    <thead className={GOVUK_CLASSES.table.head}>
                      <tr className={GOVUK_CLASSES.table.row}>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Article</th>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Risk Score</th>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Indicators</th>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Regions</th>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Simulation</th>
                        <th scope="col" className={GOVUK_CLASSES.table.header}>Published</th>
                      </tr>
                    </thead>
                    <tbody className={GOVUK_CLASSES.table.body}>
                      {unrestAnalysis.articles.map((article) => (
                        <tr key={article.id} className={GOVUK_CLASSES.table.row}>
                          <td className={GOVUK_CLASSES.table.cell}>
                            <div>
                              <strong>
                                <a href={article.link} target="_blank" rel="noopener noreferrer" className="govuk-link">
                                  {stripHtml(article.title)}
                                </a>
                              </strong>
                              <div className="govuk-hint" style={{ marginTop: '5px' }}>
                                {(() => {
                                  const cleanSummary = stripHtml(article.summary);
                                  return cleanSummary.length > 150 ? `${cleanSummary.substring(0, 150)}...` : cleanSummary;
                                })()}
                              </div>
                              <span className={`${GOVUK_CLASSES.tag.base} govuk-tag--blue`} style={{ marginTop: '5px' }}>
                                {article.source}
                              </span>
                            </div>
                          </td>
                          <td className={GOVUK_CLASSES.table.cell}>
                            <span className={getRiskScoreTag(article.civil_unrest_score)}>
                              {article.civil_unrest_score.toFixed(1)}/10
                            </span>
                            <div className="govuk-hint" style={{ marginTop: '5px' }}>
                              {getRiskLevel(article.civil_unrest_score)}
                            </div>
                          </td>
                          <td className={GOVUK_CLASSES.table.cell}>
                            <div style={{ maxWidth: '200px' }}>
                              {article.civil_unrest_indicators.slice(0, 3).map((indicator, index) => (
                                <span key={index} className={`${GOVUK_CLASSES.tag.base} govuk-tag--grey`} 
                                      style={{ marginRight: '4px', marginBottom: '4px', fontSize: '11px' }}>
                                  {indicator.replace(/^(High-risk|Medium-risk|Low-risk):\s*/, '')}
                                </span>
                              ))}
                              {article.civil_unrest_indicators.length > 3 && (
                                <div className="govuk-hint" style={{ marginTop: '5px' }}>
                                  +{article.civil_unrest_indicators.length - 3} more
                                </div>
                              )}
                            </div>
                          </td>
                          <td className={GOVUK_CLASSES.table.cell}>
                            {article.suggested_regions.length > 0 ? (
                              <div>
                                {article.suggested_regions.slice(0, 2).map((region, index) => (
                                  <span key={index} className={`${GOVUK_CLASSES.tag.base} govuk-tag--purple`} 
                                        style={{ marginRight: '4px', marginBottom: '4px', fontSize: '11px' }}>
                                    {region}
                                  </span>
                                ))}
                                {article.suggested_regions.length > 2 && (
                                  <div className="govuk-hint" style={{ marginTop: '5px' }}>
                                    +{article.suggested_regions.length - 2} more
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="govuk-hint">No specific regions</span>
                            )}
                          </td>
                          <td className={GOVUK_CLASSES.table.cell}>
                            {article.requires_simulation ? (
                              <div>
                                <span className={`${GOVUK_CLASSES.tag.base} govuk-tag--red`} style={{ display: 'block', marginBottom: '8px' }}>
                                  Required
                                </span>
                                <button
                                  className={GOVUK_CLASSES.button.primary}
                                  style={{ fontSize: '14px', padding: '5px 10px' }}
                                  onClick={async () => {
                                    try {
                                      const response = await fetch(`${API_CONFIG.baseUrl}/api/simulation-queue/add`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          article_id: article.id,
                                          article_title: stripHtml(article.title),
                                          article_url: article.link,
                                          priority: 'high'
                                        })
                                      });
                                      if (response.ok) {
                                        notificationStore.show({
                                          title: 'Added to Queue',
                                          message: 'Article added to simulation queue and processing will begin shortly',
                                          type: 'success'
                                        });
                                      } else {
                                        throw new Error('Failed to add to queue');
                                      }
                                    } catch (err) {
                                      notificationStore.show({
                                        title: 'Queue Error',
                                        message: 'Failed to add article to simulation queue',
                                        type: 'error'
                                      });
                                    }
                                  }}
                                >
                                  Add to Queue
                                </button>
                              </div>
                            ) : (
                              <span className={`${GOVUK_CLASSES.tag.base} govuk-tag--grey`}>
                                Not Required
                              </span>
                            )}
                          </td>
                          <td className={GOVUK_CLASSES.table.cell}>
                            {formatDateTime(article.published)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {/* Quick Actions for Public Safety Flags */}
                <div className={GOVUK_CLASSES.spacing.marginTop[6]}>
                  <h3 className={GOVUK_CLASSES.heading.s}>Quick Actions</h3>
                  <div className="govuk-button-group">
                    <button 
                      className={GOVUK_CLASSES.button.primary}
                      onClick={loadUnrestAnalysis}
                      disabled={loadingUnrest}
                    >
                      {loadingUnrest ? 'Refreshing...' : 'Refresh Analysis'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Risk Assessment Guidelines */}
            <div className={GOVUK_CLASSES.spacing.marginBottom[6]}>
              <h3 className={GOVUK_CLASSES.heading.s}>Risk Assessment Guidelines</h3>
              
              <details className={GOVUK_CLASSES.details.container}>
                <summary className={GOVUK_CLASSES.details.summary}>
                  <span className={GOVUK_CLASSES.details.text}>
                    Risk scoring methodology
                  </span>
                </summary>
                <div className={GOVUK_CLASSES.details.text}>
                  <ul className="govuk-list govuk-list--bullet">
                    <li><strong>High Risk (7-10)</strong>: Riots, violent protests, emergency declarations, martial law</li>
                    <li><strong>Medium Risk (4-6)</strong>: Large protests, strikes, confrontations, crowd control situations</li>
                    <li><strong>Low Risk (2-3)</strong>: Peaceful demonstrations, gatherings, minor disturbances</li>
                    <li><strong>Minimal Risk (0-1)</strong>: Routine events, meetings, vigils</li>
                  </ul>
                  <p>Scores are automatically boosted for London-specific content. Articles scoring 4.0+ in London areas trigger simulation review.</p>
                </div>
              </details>

              <details className={GOVUK_CLASSES.details.container}>
                <summary className={GOVUK_CLASSES.details.summary}>
                  <span className={GOVUK_CLASSES.details.text}>
                    Simulation trigger criteria
                  </span>
                </summary>
                <div className={GOVUK_CLASSES.details.text}>
                  <ul className="govuk-list govuk-list--bullet">
                    <li>Risk score of 4.0 or higher</li>
                    <li>London-specific geographic references</li>
                    <li>Keywords indicating potential for escalation</li>
                    <li>Multiple indicators suggesting coordinated activity</li>
                  </ul>
                  <p>Simulation candidates are automatically queued for review by emergency planning teams.</p>
                </div>
              </details>
            </div>
          </div>
        </div>

        {/* Add New Source Modal */}
        {showAddSourceModal && (
          <div className="govuk-modal-overlay" style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div className="govuk-modal" style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '4px',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto'
            }}>
              <h2 className={GOVUK_CLASSES.heading.l}>Add New RSS Feed</h2>
              <p className={GOVUK_CLASSES.body.m}>
                Add a new RSS feed to monitor for evacuation planning intelligence.
              </p>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="source-name">
                  <strong>Source Name</strong>
                </label>
                <input
                  className={GOVUK_CLASSES.form.input}
                  id="source-name"
                  type="text"
                  value={newSourceForm.name}
                  onChange={(e) => setNewSourceForm({...newSourceForm, name: e.target.value})}
                  placeholder="e.g. Guardian London News"
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="source-url">
                  <strong>RSS Feed URL</strong>
                </label>
                <input
                  className={GOVUK_CLASSES.form.input}
                  id="source-url"
                  type="url"
                  value={newSourceForm.url}
                  onChange={(e) => setNewSourceForm({...newSourceForm, url: e.target.value})}
                  placeholder="https://feeds.theguardian.com/theguardian/uk/london/rss"
                />
              </div>

              <div className={GOVUK_CLASSES.form.group}>
                <label className={GOVUK_CLASSES.form.label} htmlFor="source-description">
                  <strong>Description</strong>
                </label>
                <textarea
                  className={GOVUK_CLASSES.form.textarea}
                  id="source-description"
                  rows={3}
                  value={newSourceForm.description}
                  onChange={(e) => setNewSourceForm({...newSourceForm, description: e.target.value})}
                  placeholder="Brief description of this news source and its relevance to evacuation planning"
                />
              </div>

              <div className="govuk-button-group">
                <button 
                  className={GOVUK_CLASSES.button.primary}
                  onClick={handleAddSource}
                >
                  Add RSS Feed
                </button>
                <button 
                  className={GOVUK_CLASSES.button.secondary}
                  onClick={() => {
                    setShowAddSourceModal(false);
                    setNewSourceForm({
                      name: '',
                      url: '',
                      description: '',
                      type: 'rss'
                    });
                  }}
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

export default SourcesGovUK;
