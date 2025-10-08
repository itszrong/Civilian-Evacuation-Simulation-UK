/**
 * Global Page Context Provider
 * Captures and manages current page data for chat context injection
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface PageContextData {
  // Page identification
  currentPage: string;
  currentTab?: string;
  timestamp: string;
  
  // Data context
  data: Record<string, any>;
  
  // UI state
  uiState: {
    loading?: boolean;
    error?: string | null;
    selectedFilters?: Record<string, any>;
    activeModals?: string[];
    userInteractions?: string[];
  };
  
  // User context
  userRole?: string;
  permissions?: string[];
}

interface PageContextValue {
  context: PageContextData | null;
  updateContext: (updates: Partial<PageContextData>) => void;
  setPageData: (pageName: string, data: Record<string, any>) => void;
  setUIState: (uiState: Partial<PageContextData['uiState']>) => void;
  getContextForChat: () => string;
  clearContext: () => void;
}

const PageContext = createContext<PageContextValue | undefined>(undefined);

export const usePageContext = () => {
  const context = useContext(PageContext);
  if (!context) {
    throw new Error('usePageContext must be used within a PageContextProvider');
  }
  return context;
};

interface PageContextProviderProps {
  children: React.ReactNode;
}

export const PageContextProvider: React.FC<PageContextProviderProps> = ({ children }) => {
  const [context, setContext] = useState<PageContextData | null>(null);

  const updateContext = useCallback((updates: Partial<PageContextData>) => {
    setContext(prev => {
      const newContext = prev ? {
        ...prev,
        ...updates,
        data: { ...prev.data, ...updates.data },
        uiState: { ...prev.uiState, ...updates.uiState }
      } : {
        currentPage: 'unknown',
        data: {},
        uiState: {},
        ...updates
      };

      // Only update timestamp if the data actually changed
      // Use shallow comparison instead of JSON.stringify to avoid "Invalid string length" errors
      // with large simulation data (can have 10 scenarios × 50k agents × 50 nodes = 25M values)
      const dataChanged = !prev ||
                          prev.currentPage !== newContext.currentPage ||
                          Object.keys(newContext.data || {}).length !== Object.keys(prev.data || {}).length ||
                          Object.keys(newContext.uiState || {}).length !== Object.keys(prev.uiState || {}).length;

      return {
        ...newContext,
        timestamp: dataChanged ? new Date().toISOString() : (prev?.timestamp || new Date().toISOString())
      };
    });
  }, []);

  const setPageData = useCallback((pageName: string, data: Record<string, any>) => {
    updateContext({
      currentPage: pageName,
      data,
      timestamp: new Date().toISOString()
    });
  }, [updateContext]);

  const setUIState = useCallback((uiState: Partial<PageContextData['uiState']>) => {
    updateContext({ uiState });
  }, [updateContext]);

  const getContextForChat = useCallback((): string => {
    if (!context) return 'No page context available';

    const contextSummary = {
      page: context.currentPage,
      tab: context.currentTab,
      timestamp: context.timestamp,
      dataKeys: Object.keys(context.data),
      uiState: context.uiState,
      userRole: context.userRole
    };

    // Create a comprehensive context string
    let contextString = `## Current Page Context\n\n`;
    contextString += `**Page**: ${context.currentPage}\n`;
    if (context.currentTab) contextString += `**Active Tab**: ${context.currentTab}\n`;
    contextString += `**Last Updated**: ${new Date(context.timestamp).toLocaleString()}\n`;
    if (context.userRole) contextString += `**User Role**: ${context.userRole}\n\n`;

    // Add UI State
    if (Object.keys(context.uiState).length > 0) {
      contextString += `### UI State\n`;
      if (context.uiState.loading) contextString += `- Loading: ${context.uiState.loading}\n`;
      if (context.uiState.error) contextString += `- Error: ${context.uiState.error}\n`;
      if (context.uiState.selectedFilters) {
        contextString += `- Active Filters: ${JSON.stringify(context.uiState.selectedFilters)}\n`;
      }
      if (context.uiState.activeModals?.length) {
        contextString += `- Open Modals: ${context.uiState.activeModals.join(', ')}\n`;
      }
      contextString += '\n';
    }

    // Add Data Context
    if (Object.keys(context.data).length > 0) {
      contextString += `### Available Data\n`;
      
      // Sources page specific data
      if (context.data.feedsStatus) {
        const feeds = context.data.feedsStatus;
        contextString += `**Data Sources**: ${feeds.healthy_sources}/${feeds.total_sources} operational\n`;
        contextString += `**Last Refresh**: ${feeds.last_global_refresh || 'Never'}\n`;
        
        if (feeds.feeds?.gov_primary?.length) {
          contextString += `**Government Sources**: ${feeds.feeds.gov_primary.length} configured\n`;
          feeds.feeds.gov_primary.forEach((source: any) => {
            contextString += `  - ${source.name}: ${source.status} (${source.documents_count} docs)\n`;
          });
        }
        
        if (feeds.feeds?.news_verified?.length) {
          contextString += `**News Sources**: ${feeds.feeds.news_verified.length} configured\n`;
          feeds.feeds.news_verified.forEach((source: any) => {
            contextString += `  - ${source.name}: ${source.status} (${source.documents_count} docs)\n`;
          });
        }
      }

      // Public safety incidents data
      if (context.data.unrestAnalysis) {
        const unrest = context.data.unrestAnalysis;
        contextString += `**Public Safety Incidents**: ${unrest.unrest_articles}/${unrest.total_articles} articles flagged\n`;
        contextString += `**Simulation Candidates**: ${unrest.simulation_candidates} requiring review\n`;
        if (unrest.highest_score > 0) {
          contextString += `**Highest Risk Score**: ${unrest.highest_score.toFixed(1)}/10\n`;
        }
        
        if (unrest.articles?.length > 0) {
          contextString += `**Recent High-Risk Articles**:\n`;
          unrest.articles.slice(0, 3).forEach((article: any) => {
            contextString += `  - "${article.title}" (Score: ${article.civil_unrest_score.toFixed(1)})\n`;
            if (article.suggested_regions?.length) {
              contextString += `    Regions: ${article.suggested_regions.join(', ')}\n`;
            }
          });
        }
      }

      // Simulation queue data
      if (context.data.simulationQueue) {
        const queue = context.data.simulationQueue;
        contextString += `**Simulation Queue**: ${queue.length} requests\n`;
        const statusCounts = queue.reduce((acc: any, req: any) => {
          acc[req.status] = (acc[req.status] || 0) + 1;
          return acc;
        }, {});
        Object.entries(statusCounts).forEach(([status, count]) => {
          contextString += `  - ${status}: ${count}\n`;
        });
      }

      // Dashboard data
      if (context.data.dashboardMetrics) {
        const metrics = context.data.dashboardMetrics;
        contextString += `**Dashboard Metrics**:\n`;
        if (metrics.totalRuns) contextString += `  - Total Simulations: ${metrics.totalRuns}\n`;
        if (metrics.averageEvacuationTime) contextString += `  - Avg Evacuation Time: ${metrics.averageEvacuationTime}min\n`;
        if (metrics.successRate) contextString += `  - Success Rate: ${metrics.successRate}%\n`;
      }

      // Results data
      if (context.data.simulationResults) {
        const results = context.data.simulationResults;
        contextString += `**Current Simulation Results**:\n`;
        if (results.length > 0) {
          contextString += `  - ${results.length} simulation runs available\n`;
          const latestRun = results[0];
          if (latestRun) {
            contextString += `  - Latest: ${latestRun.scenario_name || 'Unnamed'} (${latestRun.status})\n`;
            if (latestRun.metrics) {
              contextString += `    Evacuation Time: ${latestRun.metrics.evacuation_time_minutes}min\n`;
              contextString += `    Success Rate: ${latestRun.metrics.success_rate}%\n`;
            }
          }
        }
      }

      // Current visualization data
      if (context.data.visualizationData) {
        const viz = context.data.visualizationData;
        contextString += `**Current Visualization Data**:\n`;
        
        if (viz.scenario) {
          contextString += `  - **Active Scenario**: ${viz.scenario.config?.name || viz.scenario.config?.scenario_name || 'Unnamed Scenario'}\n`;
          contextString += `  - **Hazard Type**: ${viz.scenario.config?.hazard_type || 'Unknown'}\n`;
          contextString += `  - **Evacuation Direction**: ${viz.scenario.config?.evacuation_direction || 'Unknown'}\n`;
          contextString += `  - **Population Affected**: ${viz.scenario.config?.population_affected?.toLocaleString() || 'Unknown'}\n`;
        }
        
        if (viz.metrics) {
          contextString += `  - **Current Metrics**:\n`;
          contextString += `    • Clearance Time: ${viz.metrics.clearance_time || viz.metrics.clearance_time_p50 || 'N/A'} minutes\n`;
          contextString += `    • Fairness Index: ${viz.metrics.fairness_index || 'N/A'}\n`;
          contextString += `    • Robustness Score: ${viz.metrics.robustness || 'N/A'}\n`;
          contextString += `    • Evacuation Efficiency: ${viz.metrics.evacuation_efficiency || 'N/A'}%\n`;
        }
        
        if (viz.simulation_data) {
          const simData = viz.simulation_data;
          contextString += `  - **Simulation Data Available**:\n`;
          contextString += `    • Interactive Map: ${viz.hasInteractiveMap ? 'Yes' : 'No'}\n`;
          contextString += `    • A* Routes: ${simData.astar_routes?.length || 0}\n`;
          contextString += `    • Random Walks: ${simData.random_walks?.num_walks || 0}\n`;
          contextString += `    • Network Graph: ${simData.network_graph?.nodes?.length || 0} nodes\n`;
        }
      }
    }

    return contextString;
  }, [context]);

  const clearContext = useCallback(() => {
    setContext(null);
  }, []);

  const value: PageContextValue = {
    context,
    updateContext,
    setPageData,
    setUIState,
    getContextForChat,
    clearContext
  };

  return (
    <PageContext.Provider value={value}>
      {children}
    </PageContext.Provider>
  );
};

export default PageContextProvider;
