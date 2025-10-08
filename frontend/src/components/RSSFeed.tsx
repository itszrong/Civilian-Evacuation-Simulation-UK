/**
 * RSS Feed Display Component
 * Shows breaking news from ingested RSS feeds
 */

import React, { useState, useEffect } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG } from '../config/api';

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  link: string;
  published: string;
  source: string;
  category: string;
  priority: number;
  ingested_at: string;
}

const RSSFeed: React.FC = () => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetchArticles();
    fetchStats();
    const interval = setInterval(() => {
      fetchArticles();
      fetchStats();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchArticles = async () => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/rss/articles?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setArticles(data);
      }
    } catch (error) {
      console.error('Failed to fetch RSS articles:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}/api/rss/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch RSS stats:', error);
    }
  };

  const getPriorityBadge = (priority: number) => {
    if (priority >= 9) return 'govuk-tag govuk-tag--red';
    if (priority >= 7) return 'govuk-tag govuk-tag--orange';
    return 'govuk-tag govuk-tag--grey';
  };

  if (loading) {
    return <div>Loading news feed...</div>;
  }

  return (
    <div>
      <h2 className={GOVUK_CLASSES.heading.l}>Breaking News & Intelligence</h2>

      {stats && (
        <div className="govuk-inset-text">
          <strong>{stats.total_articles}</strong> articles from <strong>{stats.sources}</strong> sources
          {stats.last_updated && (
            <> · Last updated: {new Date(stats.last_updated).toLocaleTimeString()}</>
          )}
        </div>
      )}

      <div className="govuk-grid-row">
        {articles.map((article) => (
          <div key={article.id} className="govuk-grid-column-full" style={{ marginBottom: '20px' }}>
            <div className={`${GOVUK_CLASSES.panel} govuk-panel--confirmation`}
                 style={{ backgroundColor: '#f3f2f1', padding: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <h3 className={GOVUK_CLASSES.heading.s} style={{ marginBottom: '5px', flex: 1 }}>
                  <a href={article.link} target="_blank" rel="noopener noreferrer" className="govuk-link">
                    {article.title}
                  </a>
                </h3>
                <span className={getPriorityBadge(article.priority)}>
                  P{article.priority}
                </span>
              </div>

              <p className={GOVUK_CLASSES.body.s} style={{ marginBottom: '10px' }}>
                {article.summary.substring(0, 200)}...
              </p>

              <div className="govuk-body-xs" style={{ color: '#505a5f' }}>
                <strong>{article.source}</strong> · {article.category} ·
                {new Date(article.published).toLocaleDateString()} {new Date(article.published).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
      </div>

      {articles.length === 0 && (
        <div className="govuk-warning-text">
          <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
          <strong className="govuk-warning-text__text">
            <span className="govuk-warning-text__assistive">Warning: </span>
            No RSS articles available. Start the RSS ingestion service.
          </strong>
        </div>
      )}
    </div>
  );
};

export default RSSFeed;
