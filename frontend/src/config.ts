// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/api/health`,
  metrics: `${API_BASE_URL}/api/metrics`,
  runs: `${API_BASE_URL}/api/runs`,
  search: `${API_BASE_URL}/api/search`,
  feeds: `${API_BASE_URL}/api/feeds`,
  artifacts: `${API_BASE_URL}/api/artifacts`,
};
