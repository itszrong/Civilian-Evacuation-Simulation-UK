/**
 * Centralized API configuration for the Primary Care Triage System frontend
 * Supports switching between different environments (local, dev, staging, production)
 */

// Environment configuration
const ENVIRONMENTS = {
  local: {
    baseUrl: 'http://localhost:8000',
    name: 'Local Development'
  },
  dev: {
    baseUrl: process.env.REACT_APP_VERCEL_URL ? `https://${process.env.REACT_APP_VERCEL_URL}/api` : 'http://localhost:8000',
    name: 'Development'
  },
  staging: {
    baseUrl: process.env.REACT_APP_VERCEL_URL ? `https://${process.env.REACT_APP_VERCEL_URL}/api` : 'http://localhost:8000',
    name: 'Staging'
  },
  production: {
    baseUrl: process.env.REACT_APP_VERCEL_URL ? `https://${process.env.REACT_APP_VERCEL_URL}/api` : '/api',
    name: 'Production'
  }
};

// Get current environment from environment variable or default to local
const getCurrentEnvironment = () => {
  // Auto-detect Vercel deployment
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return ENVIRONMENTS.production;
  }
  
  const env = process.env.REACT_APP_API_ENV || 'local';
  return ENVIRONMENTS[env] || ENVIRONMENTS.local;
};

// Current environment configuration
const currentEnv = getCurrentEnvironment();

// Allow override of API URL via environment variable
const getBaseUrl = () => {
  // Highest priority: explicit environment override
  if (process.env.REACT_APP_API_URL && process.env.REACT_APP_API_URL.trim()) {
    return process.env.REACT_APP_API_URL.trim();
  }

  // Auto-detect Vercel deployment and use relative API URLs (same-origin)
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return '/api';
  }

  // Development mode - use direct backend URL
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';  // Direct backend connection
  }

  return currentEnv.baseUrl;
};

// API configuration object
export const API_CONFIG = {
  baseUrl: getBaseUrl(),
  environment: currentEnv.name,
  timeout: parseInt(process.env.REACT_APP_AUTH_TIMEOUT) || 30000, // 30 seconds
  retries: 3
};

// API endpoints organized by feature
export const API_ENDPOINTS = {
  // Authentication endpoints
  auth: {
    login: '/auth/login',
    refresh: '/auth/refresh',
    me: '/auth/me',
    logout: '/auth/logout'
  },

  // Healthcare Triage endpoints
  triage: {
    patient: '/triage/patient',
    dashboard: '/triage/dashboard',
    outcomes: '/triage/outcomes'
  },

  // GP Data endpoints (Foundry OSDK)
  gp: {
    practices: '/gp/practices',
    demographics: '/gp/demographics',
    satisfaction: '/gp/satisfaction',
    patterns: '/gp/appointments/patterns',
    context: '/gp/context',
    status: '/gp/status'
  },

  // System endpoints
  system: {
    health: '/system/health',
    status: '/system/status',
    metrics: '/system/metrics'
  },

  // Simulation endpoints (now use real science algorithms by default)
  simulation: {
    cities: '/api/simulation/cities',
    run: (city) => `/api/simulation/${city}/run`,
    visualisation: (city) => `/api/simulation/${city}/visualisation`,
    status: (city) => `/api/simulation/${city}/status`,
    result: (city, runId) => `/api/simulation/${city}/history/${runId}`
  },

  // Evacuation planning endpoints
  evacuation: {
    runs: '/api/runs',
    run: (runId) => `/api/runs/${runId}`,
    list: '/api/runs'
  },

  // Metrics endpoints
  metrics: {
    dashboard: '/api/metrics',
    calculate: '/api/metrics/calculate',
    calculateMultiple: '/api/metrics/calculate-multiple',
    runInfo: (runId) => `/api/metrics/runs/${runId}/info`,
    examples: '/api/metrics/examples',
    cache: '/api/metrics/cache'
  },

  // Agentic AI endpoints
  agentic: {
    generateMetrics: '/api/agentic/metrics/generate',
    generateScenario: '/api/agentic/scenarios/generate',
    optimizeMetrics: '/api/agentic/metrics/optimize',
    comparisonStudy: '/api/agentic/scenarios/comparison-study',
    analysisPackage: '/api/agentic/analysis-package',
    executeAnalysis: '/api/agentic/execute-analysis',
    generateRealisticScenarios: '/api/agentic/generate-realistic-scenarios',
    runResult: (runId) => `/api/agentic/run-result/${runId}`,
    examples: '/api/agentic/examples',
    capabilities: '/api/agentic/capabilities',
    health: '/api/agentic/health'
  }
};

// Utility function to build full URL
export const buildUrl = (endpoint) => {
  return `${API_CONFIG.baseUrl}${endpoint}`;
};

// Utility function to create URL with query parameters
export const buildUrlWithParams = (endpoint, params = {}) => {
  const url = new URL(buildUrl(endpoint));
  Object.keys(params).forEach(key => {
    if (params[key] !== undefined && params[key] !== null) {
      url.searchParams.append(key, params[key]);
    }
  });
  return url.toString();
};

// Default headers
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json'
};

// Headers with authentication
export const getAuthHeaders = (token) => ({
  ...DEFAULT_HEADERS,
  'Authorization': `Bearer ${token}`
});

// HTTP methods enum
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  DELETE: 'DELETE',
  PATCH: 'PATCH'
};

// Common request configurations
export const REQUEST_CONFIG = {
  // Standard GET request
  get: (token = null) => ({
    method: HTTP_METHODS.GET,
    headers: token ? getAuthHeaders(token) : DEFAULT_HEADERS
  }),

  // Standard POST request
  post: (data, token = null) => ({
    method: HTTP_METHODS.POST,
    headers: token ? getAuthHeaders(token) : DEFAULT_HEADERS,
    body: JSON.stringify(data)
  }),

  // Standard PUT request
  put: (data, token = null) => ({
    method: HTTP_METHODS.PUT,
    headers: token ? getAuthHeaders(token) : DEFAULT_HEADERS,
    body: JSON.stringify(data)
  }),

  // Standard DELETE request
  delete: (token = null) => ({
    method: HTTP_METHODS.DELETE,
    headers: token ? getAuthHeaders(token) : DEFAULT_HEADERS
  })
};

// Error handling utility
export const handleApiError = async (response) => {
  if (!response.ok) {
    let errorMessage = 'An error occurred';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (e) {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }
  return response;
};

// Enhanced fetch with error handling and retries
export const apiRequest = async (endpoint, config = {}, retries = API_CONFIG.retries) => {
  const url = buildUrl(endpoint);
  
  try {
    const response = await fetch(url, {
      ...config,
      timeout: API_CONFIG.timeout
    });
    
    await handleApiError(response);
    return response.json();
  } catch (error) {
    if (retries > 0 && !error.message.includes('401') && !error.message.includes('403')) {
      // Retry for non-auth errors
      console.warn(`API request failed, retrying... (${retries} attempts left)`, error.message);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      return apiRequest(endpoint, config, retries - 1);
    }
    throw error;
  }
};

// Development helpers
export const debugApi = () => {
  console.log('API Configuration:', {
    environment: API_CONFIG.environment,
    baseUrl: API_CONFIG.baseUrl,
    endpoints: API_ENDPOINTS
  });
};

// Export environment check utilities
export const isLocal = () => currentEnv === ENVIRONMENTS.local;
export const isDev = () => currentEnv === ENVIRONMENTS.dev;
export const isProduction = () => currentEnv === ENVIRONMENTS.production;

// Console log current environment for debugging
console.log(`🌐 API Environment: ${API_CONFIG.environment} (${API_CONFIG.baseUrl})`);
console.log(`🌍 Current hostname: ${typeof window !== 'undefined' ? window.location.hostname : 'server-side'}`);
console.log(`🔧 Node ENV: ${process.env.NODE_ENV}`);

export default {
  API_CONFIG,
  API_ENDPOINTS,
  buildUrl,
  buildUrlWithParams,
  REQUEST_CONFIG,
  apiRequest,
  getAuthHeaders,
  debugApi
};
