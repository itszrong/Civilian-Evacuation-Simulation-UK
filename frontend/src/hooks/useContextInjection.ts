/**
 * Context Injection Hooks
 * Automatically captures component data and injects it into global page context
 */

import { useEffect, useCallback } from 'react';
import { usePageContext } from '../contexts/PageContextProvider';

// Generic hook for any component to inject its data
export const useContextInjection = (
  pageName: string,
  data: Record<string, any>,
  options: {
    tab?: string;
    userRole?: string;
    permissions?: string[];
    uiState?: Record<string, any>;
  } = {}
) => {
  const { updateContext } = usePageContext();

  useEffect(() => {
    updateContext({
      currentPage: pageName,
      currentTab: options.tab,
      data,
      userRole: options.userRole,
      permissions: options.permissions,
      uiState: options.uiState || {}
    });
  }, [pageName, data, options.tab, options.userRole, options.permissions, options.uiState, updateContext]);
};

// Specific hook for Sources page
export const useSourcesContextInjection = (
  feedsStatus: any,
  unrestAnalysis: any,
  simulationQueue: any,
  activeTab: string,
  selectedTier: string,
  loading: boolean,
  error: string | null,
  userRole?: string
) => {
  const { updateContext } = usePageContext();

  const contextData = {
    feedsStatus,
    unrestAnalysis,
    simulationQueue,
    // Derived data for easier chat consumption
    totalSources: feedsStatus?.total_sources || 0,
    healthySources: feedsStatus?.healthy_sources || 0,
    lastRefresh: feedsStatus?.last_global_refresh,
    unrestArticles: unrestAnalysis?.unrest_articles || 0,
    simulationCandidates: unrestAnalysis?.simulation_candidates || 0,
    highestRiskScore: unrestAnalysis?.highest_score || 0,
    queueLength: simulationQueue?.length || 0
  };

  const uiState = {
    loading,
    error,
    selectedFilters: { tier: selectedTier },
    activeTab
  };

  useEffect(() => {
    updateContext({
      currentPage: 'Data Sources & Feeds',
      currentTab: activeTab,
      data: contextData,
      uiState,
      userRole
    });
  }, [feedsStatus, unrestAnalysis, simulationQueue, activeTab, selectedTier, loading, error, userRole, updateContext]);
};

// Hook for Dashboard page
export const useDashboardContextInjection = (
  metrics: any,
  recentRuns: any,
  systemHealth: any,
  loading: boolean,
  error: string | null,
  userRole?: string
) => {
  const { updateContext } = usePageContext();

  const contextData = {
    dashboardMetrics: metrics,
    recentRuns,
    systemHealth,
    // Derived data
    totalRuns: metrics?.total_runs || 0,
    averageEvacuationTime: metrics?.average_evacuation_time,
    successRate: metrics?.success_rate,
    systemStatus: systemHealth?.status
  };

  const uiState = {
    loading,
    error
  };

  useEffect(() => {
    updateContext({
      currentPage: 'Emergency Planning Dashboard',
      data: contextData,
      uiState,
      userRole
    });
  }, [metrics, recentRuns, systemHealth, loading, error, userRole, updateContext]);
};

// Hook for Results page
export const useResultsContextInjection = (
  simulationResults: any[],
  selectedRun: any,
  visualizationData: any,
  filters: any,
  loading: boolean,
  error: string | null,
  userRole?: string
) => {
  const { updateContext } = usePageContext();

  const contextData = {
    simulationResults,
    selectedRun,
    visualizationData,
    // Derived data
    totalResults: simulationResults?.length || 0,
    selectedRunId: selectedRun?.id,
    selectedRunStatus: selectedRun?.status,
    selectedRunMetrics: selectedRun?.metrics
  };

  const uiState = {
    loading,
    error,
    selectedFilters: filters,
    selectedRun: selectedRun?.id
  };

  useEffect(() => {
    updateContext({
      currentPage: 'Simulation Results',
      data: contextData,
      uiState,
      userRole
    });
  }, [simulationResults, selectedRun, visualizationData, filters, loading, error, userRole]); // updateContext is stable, don't include it
};

// Hook for Agentic Planner page
export const useAgenticContextInjection = (
  scenarios: any[],
  metrics: any[],
  analysisResults: any,
  activeScenario: any,
  loading: boolean,
  error: string | null,
  userRole?: string
) => {
  const { updateContext } = usePageContext();

  const contextData = {
    scenarios,
    metrics,
    analysisResults,
    activeScenario,
    // Derived data
    totalScenarios: scenarios?.length || 0,
    totalMetrics: metrics?.length || 0,
    activeScenarioId: activeScenario?.id
  };

  const uiState = {
    loading,
    error,
    activeScenario: activeScenario?.id
  };

  useEffect(() => {
    updateContext({
      currentPage: 'Agentic Emergency Planner',
      data: contextData,
      uiState,
      userRole
    });
  }, [scenarios, metrics, analysisResults, activeScenario, loading, error, userRole, updateContext]);
};

// Hook for chat components to get current context
export const useChatContext = () => {
  const { getContextForChat, context } = usePageContext();
  
  const getFormattedContext = useCallback(() => {
    return getContextForChat();
  }, [getContextForChat]);

  const hasContext = useCallback(() => {
    return context !== null && Object.keys(context.data).length > 0;
  }, [context]);

  return {
    getFormattedContext,
    hasContext,
    currentPage: context?.currentPage,
    currentTab: context?.currentTab
  };
};

export default {
  useContextInjection,
  useSourcesContextInjection,
  useDashboardContextInjection,
  useResultsContextInjection,
  useAgenticContextInjection,
  useChatContext
};
