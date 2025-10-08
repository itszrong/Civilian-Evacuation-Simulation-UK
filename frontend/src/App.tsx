/**
 * Civilian Evacuation Planning Tool - Main App Component
 * Government Emergency Planning System
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Import GOV.UK styles and JavaScript
// GOV.UK CSS loaded via CDN in index.html to avoid asset path issues
import { initAll } from 'govuk-frontend';

// Import GOV.UK Layout and components
import Layout from './components/govuk/Layout';
import { NotificationContainer } from './components/govuk/Notification';
import GlobalChatButton from './components/GlobalChatButton';
import { PageContextProvider } from './contexts/PageContextProvider';

// Import page components (GOV.UK versions)
import Dashboard from './components/DashboardGovUK';
import PlanAndRun from './components/PlanAndRunGovUK';
import Results from './components/ResultsGovUK';
import Sources from './components/SourcesGovUK';
import BoroughDashboard from './components/BoroughDashboard';
import BoroughDetail from './components/BoroughDetail';
import SmartPlanningPage from './components/SmartPlanningPage';

import './App.css';

const App: React.FC = () => {
  // Initialize GOV.UK Frontend JavaScript components
  useEffect(() => {
    initAll();
  }, []);

  return (
    <PageContextProvider>
      <Router future={{ v7_relativeSplatPath: true }}>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/boroughs" element={<BoroughDashboard />} />
            <Route path="/borough/:boroughName" element={<BoroughDetail />} />
            <Route path="/borough/:boroughName/plan" element={<SmartPlanningPage />} />
            <Route path="/plan" element={<PlanAndRun />} />
            <Route path="/results" element={<Results />} />
            <Route path="/results/:runId" element={<Results />} />
            <Route path="/sources" element={<Sources />} />
          </Routes>
        </Layout>
        <NotificationContainer />
        <GlobalChatButton />
      </Router>
    </PageContextProvider>
  );
};

export default App;
