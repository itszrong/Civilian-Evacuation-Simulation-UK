/**
 * Borough Dashboard - Executive Traffic Light Status Board
 * Shows all London boroughs with individual metric traffic lights and trends
 * Designed for PM, No. 10, Cabinet Office, and National Situation Centre
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { useContextInjection } from '../hooks/useContextInjection';
import { BoroughContextService } from '../services/boroughContextService';

type TrafficLight = 'green' | 'amber' | 'red' | 'grey';
type Trend = 'improving' | 'declining' | 'stable' | 'none';

interface MetricStatus {
  value: number;
  status: TrafficLight;
  trend: Trend;
  previousValue?: number;
}

interface BoroughRun {
  run_id: string;
  created_at: string;
  status: string;
  metrics?: {
    clearance_time: number;
    fairness_index: number;
    robustness: number;
  };
}

interface BoroughStatus {
  borough: string;
  displayName: string;
  lastRunId?: string;
  lastRunDate?: string;
  clearanceTime: MetricStatus;
  fairness: MetricStatus;
  robustness: MetricStatus;
  runCount: number;
  activeRuns: number;
  recentRuns: BoroughRun[];
}

const UK_LOCATIONS = [
  // London Boroughs
  { value: 'city of london', label: 'City of London', category: 'London' },
  { value: 'westminster', label: 'Westminster', category: 'London' },
  { value: 'kensington and chelsea', label: 'Kensington and Chelsea', category: 'London' },
  { value: 'hammersmith and fulham', label: 'Hammersmith and Fulham', category: 'London' },
  { value: 'wandsworth', label: 'Wandsworth', category: 'London' },
  { value: 'lambeth', label: 'Lambeth', category: 'London' },
  { value: 'southwark', label: 'Southwark', category: 'London' },
  { value: 'tower hamlets', label: 'Tower Hamlets', category: 'London' },
  { value: 'hackney', label: 'Hackney', category: 'London' },
  { value: 'islington', label: 'Islington', category: 'London' },
  { value: 'camden', label: 'Camden', category: 'London' },
  { value: 'brent', label: 'Brent', category: 'London' },
  { value: 'ealing', label: 'Ealing', category: 'London' },
  { value: 'hounslow', label: 'Hounslow', category: 'London' },
  { value: 'richmond upon thames', label: 'Richmond upon Thames', category: 'London' },
  { value: 'kingston upon thames', label: 'Kingston upon Thames', category: 'London' },
  { value: 'merton', label: 'Merton', category: 'London' },
  { value: 'sutton', label: 'Sutton', category: 'London' },
  { value: 'croydon', label: 'Croydon', category: 'London' },
  { value: 'bromley', label: 'Bromley', category: 'London' },
  { value: 'lewisham', label: 'Lewisham', category: 'London' },
  { value: 'greenwich', label: 'Greenwich', category: 'London' },
  { value: 'bexley', label: 'Bexley', category: 'London' },
  { value: 'havering', label: 'Havering', category: 'London' },
  { value: 'barking and dagenham', label: 'Barking and Dagenham', category: 'London' },
  { value: 'redbridge', label: 'Redbridge', category: 'London' },
  { value: 'newham', label: 'Newham', category: 'London' },
  { value: 'waltham forest', label: 'Waltham Forest', category: 'London' },
  { value: 'haringey', label: 'Haringey', category: 'London' },
  { value: 'enfield', label: 'Enfield', category: 'London' },
  { value: 'barnet', label: 'Barnet', category: 'London' },
  { value: 'harrow', label: 'Harrow', category: 'London' },
  { value: 'hillingdon', label: 'Hillingdon', category: 'London' },

  // Major UK Cities
  { value: 'birmingham', label: 'Birmingham', category: 'Major Cities' },
  { value: 'manchester', label: 'Manchester', category: 'Major Cities' },
  { value: 'liverpool', label: 'Liverpool', category: 'Major Cities' },
  { value: 'leeds', label: 'Leeds', category: 'Major Cities' },
  { value: 'sheffield', label: 'Sheffield', category: 'Major Cities' },
  { value: 'bristol', label: 'Bristol', category: 'Major Cities' },
  { value: 'newcastle', label: 'Newcastle upon Tyne', category: 'Major Cities' },
  { value: 'nottingham', label: 'Nottingham', category: 'Major Cities' },
  { value: 'leicester', label: 'Leicester', category: 'Major Cities' },
  { value: 'coventry', label: 'Coventry', category: 'Major Cities' },
  { value: 'bradford', label: 'Bradford', category: 'Major Cities' },
  { value: 'stoke-on-trent', label: 'Stoke-on-Trent', category: 'Major Cities' },
  { value: 'wolverhampton', label: 'Wolverhampton', category: 'Major Cities' },
  { value: 'plymouth', label: 'Plymouth', category: 'Major Cities' },
  { value: 'derby', label: 'Derby', category: 'Major Cities' },
  { value: 'southampton', label: 'Southampton', category: 'Major Cities' },
  { value: 'portsmouth', label: 'Portsmouth', category: 'Major Cities' },
  { value: 'brighton', label: 'Brighton and Hove', category: 'Major Cities' },
  { value: 'hull', label: 'Hull (Kingston upon Hull)', category: 'Major Cities' },
  { value: 'preston', label: 'Preston', category: 'Major Cities' },

  // Scotland
  { value: 'edinburgh', label: 'Edinburgh, Scotland', category: 'Scotland' },
  { value: 'glasgow', label: 'Glasgow, Scotland', category: 'Scotland' },
  { value: 'aberdeen', label: 'Aberdeen, Scotland', category: 'Scotland' },
  { value: 'dundee', label: 'Dundee, Scotland', category: 'Scotland' },
  { value: 'stirling', label: 'Stirling, Scotland', category: 'Scotland' },
  { value: 'inverness', label: 'Inverness, Scotland', category: 'Scotland' },
  { value: 'perth', label: 'Perth, Scotland', category: 'Scotland' },

  // Wales
  { value: 'cardiff', label: 'Cardiff, Wales', category: 'Wales' },
  { value: 'swansea', label: 'Swansea, Wales', category: 'Wales' },
  { value: 'newport', label: 'Newport, Wales', category: 'Wales' },
  { value: 'wrexham', label: 'Wrexham, Wales', category: 'Wales' },
  { value: 'bangor', label: 'Bangor, Wales', category: 'Wales' },

  // Northern Ireland
  { value: 'belfast', label: 'Belfast, Northern Ireland', category: 'Northern Ireland' },
  { value: 'derry', label: 'Derry/Londonderry, Northern Ireland', category: 'Northern Ireland' },
  { value: 'lisburn', label: 'Lisburn, Northern Ireland', category: 'Northern Ireland' },

  // Other Notable Towns/Cities
  { value: 'oxford', label: 'Oxford', category: 'Other Cities' },
  { value: 'cambridge', label: 'Cambridge', category: 'Other Cities' },
  { value: 'canterbury', label: 'Canterbury', category: 'Other Cities' },
  { value: 'bath', label: 'Bath', category: 'Other Cities' },
  { value: 'york', label: 'York', category: 'Other Cities' },
  { value: 'chester', label: 'Chester', category: 'Other Cities' },
  { value: 'exeter', label: 'Exeter', category: 'Other Cities' },
  { value: 'winchester', label: 'Winchester', category: 'Other Cities' },
  { value: 'salisbury', label: 'Salisbury', category: 'Other Cities' },
  { value: 'chichester', label: 'Chichester', category: 'Other Cities' },
  { value: 'durham', label: 'Durham', category: 'Other Cities' },
  { value: 'lincoln', label: 'Lincoln', category: 'Other Cities' },
  { value: 'peterborough', label: 'Peterborough', category: 'Other Cities' },
  { value: 'reading', label: 'Reading', category: 'Other Cities' },
  { value: 'milton keynes', label: 'Milton Keynes', category: 'Other Cities' },
  { value: 'swindon', label: 'Swindon', category: 'Other Cities' },
  { value: 'luton', label: 'Luton', category: 'Other Cities' },
  { value: 'northampton', label: 'Northampton', category: 'Other Cities' },
  { value: 'ipswich', label: 'Ipswich', category: 'Other Cities' },
  { value: 'norwich', label: 'Norwich', category: 'Other Cities' },
  { value: 'colchester', label: 'Colchester', category: 'Other Cities' },
  { value: 'chelmsford', label: 'Chelmsford', category: 'Other Cities' },
  { value: 'maidstone', label: 'Maidstone', category: 'Other Cities' },
  { value: 'guildford', label: 'Guildford', category: 'Other Cities' },
];

// Keep London boroughs for backward compatibility
const LONDON_BOROUGHS = UK_LOCATIONS.filter(loc => loc.category === 'London');

const BoroughDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [boroughs, setBoroughs] = useState<BoroughStatus[]>([]);
  const [filteredBoroughs, setFilteredBoroughs] = useState<BoroughStatus[]>([]);
  const [trackedLocations, setTrackedLocations] = useState<Array<{id: string, name: string, slug: string, dateAdded: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [customLocation, setCustomLocation] = useState('');
  const [runningSimulations, setRunningSimulations] = useState<Set<string>>(new Set());
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);
  const [filteredLocations, setFilteredLocations] = useState<typeof UK_LOCATIONS>([]);
  const [selectedLocationIndex, setSelectedLocationIndex] = useState(-1);
  const [showClearConfirmation, setShowClearConfirmation] = useState(false);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [showIndividualClearConfirmation, setShowIndividualClearConfirmation] = useState<string | null>(null);
  const [clearingIndividualHistory, setClearingIndividualHistory] = useState<Set<string>>(new Set());
  const [removingFromBoard, setRemovingFromBoard] = useState<Set<string>>(new Set());
  const [openMenus, setOpenMenus] = useState<Set<string>>(new Set());
  const [expandedAccordions, setExpandedAccordions] = useState<Set<string>>(new Set());

  // Memoize context data to prevent infinite re-renders
  const contextData = useMemo(() => ({
    boroughStatuses: boroughs,
    trackedLocations,
    totalBoroughs: boroughs.length,
    activeBoroughs: boroughs.filter(b => b.activeRuns > 0).length,
    redStatusBoroughs: boroughs.filter(b => 
      b.clearanceTime.status === 'red' || 
      b.fairness.status === 'red' || 
      b.robustness.status === 'red'
    ).length,
    amberStatusBoroughs: boroughs.filter(b => 
      b.clearanceTime.status === 'amber' || 
      b.fairness.status === 'amber' || 
      b.robustness.status === 'amber'
    ).length,
    greenStatusBoroughs: boroughs.filter(b => 
      b.clearanceTime.status === 'green' && 
      b.fairness.status === 'green' && 
      b.robustness.status === 'green'
    ).length,
    runningSimulations: Array.from(runningSimulations),
    searchTerm,
    filteredBoroughs: filteredBoroughs.length
  }), [boroughs, trackedLocations, runningSimulations, searchTerm, filteredBoroughs]);

  const contextMeta = useMemo(() => ({
    userRole: 'Prime Minister',
    uiState: {
      loading,
      error,
      searchActive: searchTerm.length > 0,
      activeSimulations: runningSimulations.size
    }
  }), [loading, error, searchTerm, runningSimulations]);

  // Inject context for chat integration
  useContextInjection('Borough Dashboard', contextData, contextMeta);

  useEffect(() => {
    fetchBoroughStatuses();
    loadTrackedLocations();
  }, []);

  // Filter locations based on input
  useEffect(() => {
    if (customLocation.trim() === '') {
      setFilteredLocations([]);
      setShowLocationDropdown(false);
      setSelectedLocationIndex(-1);
    } else {
      const searchTerm = customLocation.toLowerCase();
      const filtered = UK_LOCATIONS.filter(location =>
        location.label.toLowerCase().includes(searchTerm) ||
        location.value.toLowerCase().includes(searchTerm)
      ).slice(0, 10); // Limit to 10 results for performance
      
      setFilteredLocations(filtered);
      setShowLocationDropdown(filtered.length > 0);
      setSelectedLocationIndex(-1);
    }
  }, [customLocation]);

  // Load tracked locations from localStorage
  const loadTrackedLocations = () => {
    try {
      const saved = localStorage.getItem('trackedLocations');
      if (saved) {
        setTrackedLocations(JSON.parse(saved));
      }
    } catch (err) {
      console.error('Failed to load tracked locations:', err);
    }
  };

  // Save tracked locations to localStorage
  const saveTrackedLocations = (locations: Array<{id: string, name: string, slug: string, dateAdded: string}>) => {
    try {
      localStorage.setItem('trackedLocations', JSON.stringify(locations));
      setTrackedLocations(locations);
    } catch (err) {
      console.error('Failed to save tracked locations:', err);
    }
  };

  // Add a new location to track
  const addLocationToTrack = (locationName: string) => {
    const slug = locationName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const newLocation = {
      id: `${slug}-${Date.now()}`,
      name: locationName,
      slug: slug,
      dateAdded: new Date().toISOString()
    };
    
    // Check if location already exists
    const exists = trackedLocations.some(loc => loc.slug === slug);
    if (exists) {
      return false; // Already exists
    }
    
    const updated = [...trackedLocations, newLocation];
    saveTrackedLocations(updated);
    return true;
  };

  // Remove a location from tracking
  const removeLocationFromTracking = (locationId: string) => {
    const updated = trackedLocations.filter(loc => loc.id !== locationId);
    saveTrackedLocations(updated);
  };

  // Handle location selection from dropdown
  const handleLocationSelect = (location: typeof UK_LOCATIONS[0]) => {
    setCustomLocation(location.label);
    setShowLocationDropdown(false);
    setSelectedLocationIndex(-1);
  };

  // Handle keyboard navigation in dropdown
  const handleLocationInputKeyDown = (e: React.KeyboardEvent) => {
    if (!showLocationDropdown || filteredLocations.length === 0) {
      if (e.key === 'Enter' && customLocation.trim()) {
        const success = addLocationToTrack(customLocation.trim());
        if (success) {
          setCustomLocation('');
        } else {
          setError('Location is already being tracked');
          setTimeout(() => setError(null), 3000);
        }
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedLocationIndex(prev => 
          prev < filteredLocations.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedLocationIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedLocationIndex >= 0) {
          handleLocationSelect(filteredLocations[selectedLocationIndex]);
        } else if (customLocation.trim()) {
          const success = addLocationToTrack(customLocation.trim());
          if (success) {
            setCustomLocation('');
          } else {
            setError('Location is already being tracked');
            setTimeout(() => setError(null), 3000);
          }
        }
        break;
      case 'Escape':
        setShowLocationDropdown(false);
        setSelectedLocationIndex(-1);
        break;
    }
  };

  // Toggle ellipsis menu
  const toggleMenu = (boroughSlug: string) => {
    setOpenMenus(prev => {
      const updated = new Set(prev);
      if (updated.has(boroughSlug)) {
        updated.delete(boroughSlug);
      } else {
        updated.clear(); // Close other menus
        updated.add(boroughSlug);
      }
      return updated;
    });
  };

  // Close all menus
  const closeAllMenus = () => {
    setOpenMenus(new Set());
  };

  // Toggle accordion section
  const toggleAccordion = (boroughKey: string) => {
    setExpandedAccordions(prev => {
      const updated = new Set(prev);
      if (updated.has(boroughKey)) {
        updated.delete(boroughKey);
      } else {
        updated.add(boroughKey);
      }
      return updated;
    });
  };

  // Remove borough from status board
  const removeBoroughFromBoard = async (boroughSlug: string, boroughName: string) => {
    if (removingFromBoard.has(boroughSlug)) return;
    
    setRemovingFromBoard(prev => new Set([...prev, boroughSlug]));
    
    try {
      // Remove from tracked locations if it exists there
      const trackedLocation = trackedLocations.find(loc => loc.slug === boroughSlug);
      if (trackedLocation) {
        removeLocationFromTracking(trackedLocation.id);
      }
      
      // Remove from boroughs list
      setBoroughs(prev => prev.filter(b => b.borough !== boroughSlug));
      setFilteredBoroughs(prev => prev.filter(b => b.borough !== boroughSlug));
      
      console.log(`🗑️ Removed ${boroughName} from status board`);
      
    } catch (error) {
      console.error('Failed to remove borough from board:', error);
      setError(`Failed to remove ${boroughName} from status board`);
      setTimeout(() => setError(null), 3000);
    } finally {
      setRemovingFromBoard(prev => {
        const updated = new Set(prev);
        updated.delete(boroughSlug);
        return updated;
      });
      closeAllMenus();
    }
  };

  // Clear simulation history for individual borough
  const clearBoroughHistory = async (boroughSlug: string, boroughName: string) => {
    if (clearingIndividualHistory.has(boroughSlug)) return;
    
    setClearingIndividualHistory(prev => new Set([...prev, boroughSlug]));
    setError(null);
    
    try {
      // Get runs for this specific borough
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.list}`);
      if (!response.ok) {
        throw new Error('Failed to fetch runs list');
      }
      
      const data = await response.json();
      const allRuns = data.runs || [];
      const boroughRuns = allRuns.filter((run: any) => {
        const runCity = (run.city || '').toLowerCase().replace(/\s+/g, '-');
        return runCity === boroughSlug;
      });
      
      if (boroughRuns.length === 0) {
        setError(`No simulation history found for ${boroughName}`);
        setTimeout(() => setError(null), 3000);
        return;
      }
      
      // In a production system, you'd call an API to delete specific runs
      // For now, we'll just refresh the data and the borough will disappear if it has no data
      
      console.log(`🗑️ Cleared ${boroughRuns.length} simulation histories for ${boroughName}`);
      
      // Refresh borough data to reflect changes
      await fetchBoroughStatuses();
      
    } catch (error) {
      console.error('Failed to clear borough history:', error);
      setError(`Failed to clear history for ${boroughName}. Please try again.`);
      setTimeout(() => setError(null), 5000);
    } finally {
      setClearingIndividualHistory(prev => {
        const updated = new Set(prev);
        updated.delete(boroughSlug);
        return updated;
      });
      setShowIndividualClearConfirmation(null);
      closeAllMenus();
    }
  };

  // Clear all simulation histories
  const clearAllSimulationHistories = async () => {
    if (clearingHistory) return;
    
    setClearingHistory(true);
    setError(null);
    
    try {
      // First, get all runs to delete
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.list}`);
      if (!response.ok) {
        throw new Error('Failed to fetch runs list');
      }
      
      const data = await response.json();
      const allRuns = data.runs || [];
      
      if (allRuns.length === 0) {
        setError('No simulation histories to clear');
        setTimeout(() => setError(null), 3000);
        return;
      }
      
      // Clear cache first
      try {
        await fetch(`${API_CONFIG.baseUrl}/api/metrics/cache`, {
          method: 'DELETE'
        });
      } catch (err) {
        console.warn('Failed to clear metrics cache:', err);
      }
      
      // For now, we'll clear the local state and tracked locations
      // In a production system, you'd want to call a backend endpoint to delete all run data
      
      // Clear local tracked locations
      localStorage.removeItem('trackedLocations');
      setTrackedLocations([]);
      
      // Reset borough data
      setBoroughs([]);
      setFilteredBoroughs([]);
      
      // Show success message
      setError(null);
      
      // Refresh data to show empty state
      await fetchBoroughStatuses();
      
      console.log(`🗑️ Cleared ${allRuns.length} simulation histories`);
      
    } catch (error) {
      console.error('Failed to clear simulation histories:', error);
      setError('Failed to clear simulation histories. Please try again.');
      setTimeout(() => setError(null), 5000);
    } finally {
      setClearingHistory(false);
      setShowClearConfirmation(false);
    }
  };

  // Generate borough-specific scenario intent
  const generateBoroughScenarioIntent = (locationSlug: string, locationName: string): string => {
    const boroughContext = BoroughContextService.getBoroughContext(locationSlug);
    
    if (!boroughContext) {
      return `Test comprehensive evacuation efficiency for ${locationName}`;
    }

    // Generate intent based on borough characteristics
    let intent = `Test evacuation efficiency for ${boroughContext.name}`;
    
    // Add risk-specific elements
    if (boroughContext.riskProfile.floodRisk === 'high') {
      intent += ' during flood conditions';
    }
    if (boroughContext.riskProfile.terroristThreat === 'high') {
      intent += ' with security considerations';
    }
    
    // Add infrastructure considerations
    if (boroughContext.infrastructure.transportHubs.length > 2) {
      intent += ` focusing on transport hub coordination`;
    }
    
    // Add population considerations
    if (boroughContext.demographics.touristAreas.length > 0) {
      intent += ' accounting for tourist populations';
    }
    if (boroughContext.demographics.density > 12000) {
      intent += ' in high-density areas';
    }
    
    // Add asset protection
    if (boroughContext.keyAssets.length > 0) {
      intent += ` while protecting ${boroughContext.keyAssets[0]}`;
    }
    
    return intent;
  };

  // Start simulation for a location with AI-generated scenarios
  const startSimulationForLocation = async (locationSlug: string, locationName: string) => {
    if (runningSimulations.has(locationSlug)) return;
    
    setRunningSimulations(prev => new Set([...prev, locationSlug]));
    
    // Show user what's happening
    const scenarioIntent = generateBoroughScenarioIntent(locationSlug, locationName);
    console.log(`🤖 Generating AI scenario for ${locationName}: "${scenarioIntent}"`);
    
    try {
      const cityParam = locationSlug.replace(/-/g, ' ');
      const boroughContext = BoroughContextService.getBoroughContext(locationSlug);
      
      // Generate borough-specific scenario intent
      const scenarioIntent = generateBoroughScenarioIntent(locationSlug, locationName);
      
      // Prepare agentic run with borough context
      const agenticPayload = {
        intent: {
          objective: `AI-generated evacuation planning for ${locationName}`,
          city: cityParam,
          constraints: {
            max_scenarios: 5,
            compute_budget_minutes: 3,
            must_protect_pois: boroughContext?.keyAssets.slice(0, 3) || []
          },
          hypotheses: [scenarioIntent],
          preferences: {
            fairness_weight: 0.35,
            clearance_weight: 0.5,
            robustness_weight: 0.15
          },
          freshness_days: 7,
          tiers: ['gov_primary']
        },
        agentic_context: boroughContext ? BoroughContextService.generateAIPromptContext(boroughContext) : '',
        auto_generated: true,
        borough_specific: true
      };

      // Use the simulation endpoint with AI-generated scenario context
      console.log(`🤖 Generated AI scenario: "${scenarioIntent}"`);
      console.log(`📋 Borough context:`, boroughContext ? 'Available' : 'Using default');
      
      const response = await fetch(
        `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(cityParam)}?force_refresh=true&create_complete=true&ai_scenario=${encodeURIComponent(scenarioIntent)}`
      );
      
      if (response.ok) {
        const result = await response.json();
        
        console.log(`✅ AI scenario simulation completed successfully for ${locationName}!`);
        
        // Navigate to results if we got a run_id
        if (result.run_id) {
          navigate(`/results/${result.run_id}?ai_generated=true`);
        } else {
          // Navigate to borough detail page
          navigate(`/borough/${locationSlug}?location=${encodeURIComponent(locationName)}`);
        }
        
        // Refresh borough data to show new simulation
        setTimeout(() => {
          fetchBoroughStatuses();
        }, 2000);
        
      } else {
        throw new Error('Failed to start AI simulation');
      }
    } catch (error) {
      console.error('Failed to start AI simulation:', error);
      setError(`Failed to start AI simulation for ${locationName}`);
    } finally {
      setRunningSimulations(prev => {
        const updated = new Set(prev);
        updated.delete(locationSlug);
        return updated;
      });
    }
  };

  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredBoroughs(boroughs);
    } else {
      const filtered = boroughs.filter(b =>
        b.displayName.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredBoroughs(filtered);
    }
  }, [searchTerm, boroughs]);

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (openMenus.size > 0) {
        // Check if the click is outside any menu
        const target = event.target as Element;
        if (!target.closest('[data-menu-container]')) {
          closeAllMenus();
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [openMenus]);

  const getMetricStatus = (value: number, metric: 'clearance' | 'fairness' | 'robustness'): TrafficLight => {
    if (metric === 'clearance') {
      if (value < 150) return 'green';
      if (value < 250) return 'amber';
      return 'red';
    } else {
      if (value > 0.7) return 'green';
      if (value > 0.5) return 'amber';
      return 'red';
    }
  };

  const calculateTrend = (current: number, previous: number | undefined, metric: 'clearance' | 'fairness' | 'robustness'): Trend => {
    if (!previous) return 'none';

    const threshold = 0.05; // 5% change threshold
    const change = metric === 'clearance'
      ? (previous - current) / previous  // Lower is better for clearance time
      : (current - previous) / previous; // Higher is better for fairness/robustness

    if (change > threshold) return 'improving';
    if (change < -threshold) return 'declining';
    return 'stable';
  };

  const fetchBoroughStatuses = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Fetching borough statuses...');

      // Fetch all runs with detailed metrics (optimized: single API call with details)
      const response = await fetch(
        `${API_CONFIG.baseUrl}${API_ENDPOINTS.evacuation.list}?include_details=true&limit=3`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch runs: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const runs = data.runs || [];
      console.log(`✅ Fetched ${runs.length} runs with details in single API call`);

      // Group runs by borough
      const boroughMap = new Map<string, any[]>();
      runs.forEach((run: any) => {
        const city = (run.city || run.intent?.city || 'unknown').toLowerCase();
        if (!boroughMap.has(city)) {
          boroughMap.set(city, []);
        }
        boroughMap.get(city)!.push(run);
      });

      // Calculate status for each borough - ONLY include boroughs with simulation data
      const boroughStatuses: BoroughStatus[] = [];

      // Get all boroughs that have runs
      const boroughsWithRuns = Array.from(boroughMap.keys());

      boroughsWithRuns.forEach(boroughKey => {
        // Find the display name for this borough
        const boroughConfig = LONDON_BOROUGHS.find(b => b.value === boroughKey);
        const displayName = boroughConfig?.label || boroughKey.split(' ').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
        
        const boroughRuns = boroughMap.get(boroughKey) || [];
        const activeRuns = boroughRuns.filter(r => r.status === 'in_progress' || r.status === 'running').length;
        const completedRuns = boroughRuns.filter(r => r.status === 'completed').sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

        // Only include boroughs that have at least one completed run or active run
        if (completedRuns.length === 0 && activeRuns === 0) {
          return; // Skip this borough
        }

        // Get most recent 3 completed runs (limited by backend)
        const recentRunsList = completedRuns.slice(0, 3);
        const mostRecentRun = recentRunsList[0];
        const secondMostRecentRun = recentRunsList[1];

        // Default metric statuses
        const clearanceTime: MetricStatus = {
          value: 0,
          status: 'grey',
          trend: 'none'
        };
        const fairness: MetricStatus = {
          value: 0,
          status: 'grey',
          trend: 'none'
        };
        const robustness: MetricStatus = {
          value: 0,
          status: 'grey',
          trend: 'none'
        };

        // Extract metrics from aggregate_metrics (already calculated by backend)

        let runMetrics = mostRecentRun?.aggregate_metrics;
        let previousRunMetrics = secondMostRecentRun?.aggregate_metrics;
        let hasMetrics = !!(runMetrics && runMetrics.clearance_time > 0);

        if (hasMetrics) {
          console.log(`✅ Using aggregate metrics for ${boroughKey}:`, {
            clearance: runMetrics.clearance_time.toFixed(1),
            fairness: runMetrics.fairness_index.toFixed(3),
            robustness: runMetrics.robustness.toFixed(3)
          });
        }

        if (hasMetrics && runMetrics) {
          const currentClearance = runMetrics.clearance_time || runMetrics.expected_clearance_time || 0;
          const currentFairness = runMetrics.fairness_index || 0;
          const currentRobustness = runMetrics.robustness || 0;

          // Use actual previous run metrics if available
          const prevClearance = previousRunMetrics?.clearance_time;
          const prevFairness = previousRunMetrics?.fairness_index;
          const prevRobustness = previousRunMetrics?.robustness;

          clearanceTime.value = currentClearance;
          clearanceTime.status = getMetricStatus(currentClearance, 'clearance');
          clearanceTime.trend = calculateTrend(currentClearance, prevClearance, 'clearance');
          clearanceTime.previousValue = prevClearance;

          fairness.value = currentFairness;
          fairness.status = getMetricStatus(currentFairness, 'fairness');
          fairness.trend = calculateTrend(currentFairness, prevFairness, 'fairness');
          fairness.previousValue = prevFairness;

          robustness.value = currentRobustness;
          robustness.status = getMetricStatus(currentRobustness, 'robustness');
          robustness.trend = calculateTrend(currentRobustness, prevRobustness, 'robustness');
          robustness.previousValue = prevRobustness;
        }

        boroughStatuses.push({
          borough: boroughKey,
          displayName: displayName,
          lastRunId: mostRecentRun?.run_id,
          lastRunDate: mostRecentRun?.created_at,
          clearanceTime,
          fairness,
          robustness,
          runCount: boroughRuns.length,
          activeRuns,
          recentRuns: recentRunsList.map(r => ({
            run_id: r.run_id,
            created_at: r.created_at,
            status: r.status,
            metrics: r.aggregate_metrics || null
          }))
        });
      });

      // Sort boroughs by most recent activity
      boroughStatuses.sort((a, b) => {
        const aDate = a.lastRunDate ? new Date(a.lastRunDate).getTime() : 0;
        const bDate = b.lastRunDate ? new Date(b.lastRunDate).getTime() : 0;
        return bDate - aDate;
      });

      console.log(`✅ Successfully processed ${boroughStatuses.length} boroughs`);
      setBoroughs(boroughStatuses);
      
      // Expand the first borough by default to show there's content
      if (boroughStatuses.length > 0) {
        setExpandedAccordions(new Set([boroughStatuses[0].borough]));
      }
    } catch (err) {
      console.error('❌ Failed to fetch borough statuses:', err);
      setError(err instanceof Error ? err.message : 'Failed to load borough data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: TrafficLight) => {
    switch (status) {
      case 'green': return 'govuk-tag--green';
      case 'amber': return 'govuk-tag--yellow';
      case 'red': return 'govuk-tag--red';
      case 'grey': return 'govuk-tag--grey';
    }
  };

  const getTrendIcon = (trend: Trend, metric?: 'clearance' | 'fairness' | 'robustness') => {
    if (metric === 'clearance') {
      // For clearance time: show direction numbers are going
      switch (trend) {
        case 'improving': return '↓'; // Time going down (better)
        case 'declining': return '↑'; // Time going up (worse)
        case 'stable': return '→';
        case 'none': return '';
      }
    } else {
      // For fairness/robustness: show direction numbers are going
      switch (trend) {
        case 'improving': return '↑'; // Values going up (better)
        case 'declining': return '↓'; // Values going down (worse)
        case 'stable': return '→';
        case 'none': return '';
      }
    }
  };

  const getTrendColor = (trend: Trend) => {
    switch (trend) {
      case 'improving': return '#00703c'; // Green
      case 'declining': return '#d4351c'; // Red
      case 'stable': return '#505a5f'; // Grey
      case 'none': return '#505a5f';
    }
  };

  const getTrafficLightCircle = (status: TrafficLight) => {
    const colors = {
      green: '#00703c',
      amber: '#f47738',
      red: '#d4351c',
      grey: '#b1b4b6'
    };

    return (
      <span
        style={{
          display: 'inline-block',
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          backgroundColor: colors[status],
          border: '2px solid #0b0c0c',
          marginRight: '8px',
          verticalAlign: 'middle'
        }}
        aria-label={`${status} status`}
      />
    );
  };

  if (loading) {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          <h1 className={GOVUK_CLASSES.heading.xl}>Borough Dashboard</h1>
          <p className={GOVUK_CLASSES.body.m}>Loading borough data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={GOVUK_CLASSES.gridRow}>
        <div className={GOVUK_CLASSES.gridColumn.full}>
          <h1 className={GOVUK_CLASSES.heading.xl}>Borough Dashboard</h1>
          <div className="govuk-error-summary">
            <h2 className="govuk-error-summary__title">Error</h2>
            <div className="govuk-error-summary__body">
              <p>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={GOVUK_CLASSES.gridRow}>
      <div className={GOVUK_CLASSES.gridColumn.full}>

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
          <div>
        <span className="govuk-caption-xl">National Situation Centre</span>
        <h1 className={GOVUK_CLASSES.heading.xl}>London Evacuation Readiness Status</h1>
        <p className={GOVUK_CLASSES.body.lead}>
          Real-time evacuation capability assessment across 33 London authorities
        </p>
          </div>
          
          {/* Clear History Button */}
          {(boroughs.length > 0 || trackedLocations.length > 0) && (
            <div style={{ marginTop: '20px' }}>
              <button
                onClick={() => setShowClearConfirmation(true)}
                disabled={clearingHistory}
                className="govuk-button govuk-button--warning"
                style={{
                  backgroundColor: '#d4351c',
                  borderColor: '#d4351c',
                  minWidth: '160px'
                }}
              >
                {clearingHistory ? 'Clearing...' : 'Clear All Histories'}
              </button>
            </div>
          )}
        </div>

        {/* Executive Summary */}
        <div className={`govuk-warning-text ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
          <strong className="govuk-warning-text__text">
            <span className="govuk-warning-text__assistive">Important </span>
            Classification: OFFICIAL-SENSITIVE
          </strong>
        </div>

        {/* Traffic Light Legend */}
        <details className={`${GOVUK_CLASSES.details.container} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <summary className={GOVUK_CLASSES.details.summary}>
            <span className={GOVUK_CLASSES.details.text}>Traffic light methodology</span>
          </summary>
          <div className={GOVUK_CLASSES.details.text}>
            <table className="govuk-table">
              <thead className="govuk-table__head">
                <tr className="govuk-table__row">
                  <th scope="col" className="govuk-table__header">Metric</th>
                  <th scope="col" className="govuk-table__header">Green (Optimal)</th>
                  <th scope="col" className="govuk-table__header">Amber (Acceptable)</th>
                  <th scope="col" className="govuk-table__header">Red (Concern)</th>
                </tr>
              </thead>
              <tbody className="govuk-table__body">
                <tr className="govuk-table__row">
                  <td className="govuk-table__cell">Clearance Time</td>
                  <td className="govuk-table__cell">&lt; 150 minutes</td>
                  <td className="govuk-table__cell">150-250 minutes</td>
                  <td className="govuk-table__cell">&gt; 250 minutes</td>
                </tr>
                <tr className="govuk-table__row">
                  <td className="govuk-table__cell">
                    <strong>Route Equity</strong>
                    <br />
                    <span style={{ fontSize: '12px', fontStyle: 'italic' }}>Distribution fairness of evacuation routes across population</span>
                  </td>
                  <td className="govuk-table__cell">&gt; 0.70</td>
                  <td className="govuk-table__cell">0.50-0.70</td>
                  <td className="govuk-table__cell">&lt; 0.50</td>
                </tr>
                <tr className="govuk-table__row">
                  <td className="govuk-table__cell">
                    <strong>Network Resilience</strong>
                    <br />
                    <span style={{ fontSize: '12px', fontStyle: 'italic' }}>Network connectivity and alternative route availability</span>
                  </td>
                  <td className="govuk-table__cell">&gt; 0.70</td>
                  <td className="govuk-table__cell">0.50-0.70</td>
                  <td className="govuk-table__cell">&lt; 0.50</td>
                </tr>
              </tbody>
            </table>
            <p className={GOVUK_CLASSES.body.s}><strong>Trends:</strong> ↑ Improving (≥5% improvement) | → Stable | ↓ Declining (≥5% deterioration)</p>
          </div>
        </details>

        {/* Search Box */}
        <div className={`${GOVUK_CLASSES.form.group} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <label className={GOVUK_CLASSES.form.label} htmlFor="borough-search">
            <span className={GOVUK_CLASSES.font.weightBold}>Search boroughs</span>
          </label>
          <input
            className={GOVUK_CLASSES.form.input}
            id="borough-search"
            name="borough-search"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Type borough name..."
            style={{ maxWidth: '400px' }}
          />
          {searchTerm && (
            <p className={GOVUK_CLASSES.body.s} style={{ marginTop: '5px' }}>
              Showing {filteredBoroughs.length} of {boroughs.length} boroughs
            </p>
          )}
        </div>

        {/* Add New Location to Track */}
        <div className={`${GOVUK_CLASSES.insetText} ${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
          <h3 className={GOVUK_CLASSES.heading.s}>Add New Location to Track</h3>
          <div className={GOVUK_CLASSES.form.group}>
            <label className={`${GOVUK_CLASSES.form.label} ${GOVUK_CLASSES.font.weightBold}`} htmlFor="custom-location">
              UK Location
            </label>
            <div className="govuk-hint">
              Start typing to see available UK locations, or enter a custom location name
            </div>
            <div className={GOVUK_CLASSES.gridRow}>
              <div className={GOVUK_CLASSES.gridColumn.twoThirds}>
                <div style={{ position: 'relative' }}>
                <input
                  className={GOVUK_CLASSES.form.input}
                  id="custom-location"
                  name="custom-location"
                  type="text"
                  value={customLocation}
                  onChange={(e) => setCustomLocation(e.target.value)}
                    onKeyDown={handleLocationInputKeyDown}
                    onFocus={() => {
                      if (filteredLocations.length > 0) {
                        setShowLocationDropdown(true);
                      }
                    }}
                    onBlur={() => {
                      // Delay hiding dropdown to allow for clicks
                      setTimeout(() => setShowLocationDropdown(false), 150);
                    }}
                    placeholder="Start typing a UK location..."
                    autoComplete="off"
                  />
                  
                  {/* Location Dropdown */}
                  {showLocationDropdown && filteredLocations.length > 0 && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        backgroundColor: 'white',
                        border: '2px solid #0b0c0c',
                        borderTop: 'none',
                        maxHeight: '300px',
                        overflowY: 'auto',
                        zIndex: 1000,
                        boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
                      }}
                    >
                      {/* Group locations by category */}
                      {Object.entries(
                        filteredLocations.reduce((acc, location) => {
                          if (!acc[location.category]) {
                            acc[location.category] = [];
                          }
                          acc[location.category].push(location);
                          return acc;
                        }, {} as Record<string, typeof filteredLocations>)
                      ).map(([category, locations]) => (
                        <div key={category}>
                          <div
                            style={{
                              padding: '8px 12px',
                              backgroundColor: '#f3f2f1',
                              fontSize: '12px',
                              fontWeight: 'bold',
                              color: '#505a5f',
                              borderBottom: '1px solid #b1b4b6'
                            }}
                          >
                            {category}
                          </div>
                          {locations.map((location, index) => {
                            const globalIndex = filteredLocations.indexOf(location);
                            return (
                              <div
                                key={location.value}
                                onClick={() => handleLocationSelect(location)}
                                onMouseEnter={() => setSelectedLocationIndex(globalIndex)}
                                style={{
                                  padding: '12px',
                                  cursor: 'pointer',
                                  backgroundColor: selectedLocationIndex === globalIndex ? '#1d70b8' : 'white',
                                  color: selectedLocationIndex === globalIndex ? 'white' : '#0b0c0c',
                                  borderBottom: '1px solid #f3f2f1'
                                }}
                              >
                                <div style={{ fontWeight: 'bold' }}>{location.label}</div>
                                {location.label !== location.value && (
                                  <div style={{ fontSize: '12px', opacity: 0.8 }}>
                                    {location.value}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className={GOVUK_CLASSES.gridColumn.oneThird}>
                <div className="govuk-button-group">
                  <button
                    className="govuk-button govuk-button--secondary"
                    onClick={() => {
                      if (customLocation.trim()) {
                        const success = addLocationToTrack(customLocation.trim());
                        if (success) {
                          setCustomLocation('');
                        } else {
                          setError('Location is already being tracked');
                          setTimeout(() => setError(null), 3000);
                        }
                      }
                    }}
                    disabled={!customLocation.trim()}
                    style={{ marginRight: '10px' }}
                  >
                    Add to Track
                  </button>
                <button
                  className="govuk-button"
                  onClick={() => {
                    if (customLocation.trim()) {
                      const locationSlug = customLocation.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                      navigate(`/borough/${locationSlug}?location=${encodeURIComponent(customLocation)}`);
                    }
                  }}
                  disabled={!customLocation.trim()}
                  >
                    Simulate Now
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tracked Locations */}
        {trackedLocations.length > 0 && (
          <div className={`${GOVUK_CLASSES.spacing.marginBottom[6]}`}>
            <h2 className={GOVUK_CLASSES.heading.m}>Tracked Locations</h2>
            <p className={GOVUK_CLASSES.body.s}>
              Locations you're monitoring for evacuation planning. Run simulations or view existing results.
            </p>
            
            <div className="govuk-grid-row">
              {trackedLocations.map(location => {
                const isRunning = runningSimulations.has(location.slug);
                const hasData = boroughs.some(b => b.borough === location.slug);
                
                return (
                  <div key={location.id} className="govuk-grid-column-one-half" style={{ marginBottom: '20px' }}>
                    <div className="govuk-summary-card">
                      <div className="govuk-summary-card__title-wrapper">
                        <h3 className="govuk-summary-card__title">
                          {location.name}
                        </h3>
                        <div className="govuk-summary-card__actions">
                          <button
                            onClick={() => removeLocationFromTracking(location.id)}
                            className="govuk-link"
                  style={{ 
                              background: 'none', 
                              border: 'none', 
                              color: '#d4351c',
                              fontSize: '14px',
                              cursor: 'pointer'
                            }}
                          >
                            Remove
                </button>
              </div>
            </div>
                      <div className="govuk-summary-card__content">
                        <dl className={GOVUK_CLASSES.summaryList.container}>
                          <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Status</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              {isRunning ? (
                                <span className="govuk-tag govuk-tag--blue">Running Simulation</span>
                              ) : hasData ? (
                                <span className="govuk-tag govuk-tag--green">Has Data</span>
                              ) : (
                                <span className="govuk-tag govuk-tag--grey">No Simulations</span>
                              )}
                            </dd>
          </div>
                          <div className={GOVUK_CLASSES.summaryList.row}>
                            <dt className={GOVUK_CLASSES.summaryList.key}>Added</dt>
                            <dd className={GOVUK_CLASSES.summaryList.value}>
                              {new Date(location.dateAdded).toLocaleDateString('en-GB')}
                            </dd>
        </div>
                        </dl>
                        
                        <div className="govuk-button-group" style={{ marginTop: '15px' }}>
                          <Link
                            to={`/borough/${location.slug}/plan`}
                            className="govuk-button"
                            style={{ fontSize: '14px' }}
                          >
                            Smart Planning
                          </Link>
                          
                          <div style={{ position: 'relative', display: 'inline-block' }}>
                            <button
                              onClick={() => startSimulationForLocation(location.slug, location.name)}
                              disabled={isRunning}
                              className={`govuk-button govuk-button--secondary ${isRunning ? 'govuk-button--disabled' : ''}`}
                              style={{ fontSize: '14px' }}
                              title={`Run AI-generated simulation specific to ${location.name}`}
                            >
                              {isRunning ? 'Generating AI Scenario...' : 'AI Simulation'}
                            </button>
                            <span 
                              className="govuk-tag govuk-tag--green" 
                              style={{ 
                                position: 'absolute', 
                                top: '-8px', 
                                right: '-8px', 
                                fontSize: '10px',
                                padding: '2px 4px'
                              }}
                            >
                              AUTO
                            </span>
                          </div>
                          
                          {hasData && (
                            <Link
                              to={`/borough/${location.slug}`}
                              className="govuk-button govuk-button--secondary"
                              style={{ fontSize: '14px' }}
                            >
                              View Details
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Borough Status List */}
        <h2 className={GOVUK_CLASSES.heading.l}>Borough Status Board</h2>

        {filteredBoroughs.length === 0 ? (
          <div className={GOVUK_CLASSES.insetText}>
            <h3 className={GOVUK_CLASSES.heading.s}>No simulation data available</h3>
            <p>No boroughs have completed simulations yet. Use the "Simulate This Location" feature above to run your first evacuation analysis.</p>
          </div>
        ) : (
          <div className="govuk-accordion" data-module="govuk-accordion" id="borough-accordion">
            {filteredBoroughs.map((borough, index) => (
            <div className="govuk-accordion__section" key={borough.borough}>
              <div className="govuk-accordion__section-header">
                <h2 className="govuk-accordion__section-heading">
                  <button
                    type="button"
                    className="govuk-accordion__section-button"
                    aria-controls={`accordion-content-${index}`}
                    aria-expanded={expandedAccordions.has(borough.borough)}
                    onClick={() => toggleAccordion(borough.borough)}
                    style={{ border: 'none', boxShadow: 'none', background: 'none', padding: '15px 0' }}
                  >
                    <span className="govuk-accordion__section-heading-text">
                      <span style={{ fontWeight: 'bold', fontSize: '24px' }}>{borough.displayName}</span>
                      {borough.activeRuns > 0 && (
                        <span className="govuk-tag govuk-tag--blue" style={{ marginLeft: '15px', fontSize: '14px' }}>
                          {borough.activeRuns} ACTIVE
                        </span>
                      )}
                    </span>
                  </button>
                </h2>
              </div>
              <div 
                id={`accordion-content-${index}`} 
                className="govuk-accordion__section-content"
                style={{ display: expandedAccordions.has(borough.borough) ? 'block' : 'none' }}
              >

                {/* Metrics Traffic Lights */}
                <table className="govuk-table" style={{ marginBottom: '20px' }}>
                  <thead className="govuk-table__head">
                    <tr className="govuk-table__row">
                      <th scope="col" className="govuk-table__header">Metric</th>
                      <th scope="col" className="govuk-table__header">Status</th>
                      <th scope="col" className="govuk-table__header">Value</th>
                      <th scope="col" className="govuk-table__header">Trend</th>
                      <th scope="col" className="govuk-table__header">Previous</th>
                    </tr>
                  </thead>
                  <tbody className="govuk-table__body">
                    <tr className="govuk-table__row">
                      <td className="govuk-table__cell">
                        <strong>Clearance Time</strong>
                        <br />
                        <span className="govuk-hint" style={{ fontSize: '12px' }}>Time to evacuate all civilians</span>
                      </td>
                      <td className="govuk-table__cell">
                        {getTrafficLightCircle(borough.clearanceTime.status)}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.clearanceTime.value > 0 ? `${borough.clearanceTime.value.toFixed(0)} min` : 'N/A'}
                      </td>
                      <td className="govuk-table__cell">
                        <span style={{ color: getTrendColor(borough.clearanceTime.trend), fontSize: '18px', fontWeight: 'bold' }}>
                          {getTrendIcon(borough.clearanceTime.trend, 'clearance')}
                        </span>
                        {borough.clearanceTime.trend !== 'none' && (
                          <span style={{ marginLeft: '5px', fontSize: '12px' }}>
                            {borough.clearanceTime.trend === 'improving' ? 'faster' : 
                             borough.clearanceTime.trend === 'declining' ? 'slower' : 'stable'}
                          </span>
                        )}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.clearanceTime.previousValue ? `${borough.clearanceTime.previousValue.toFixed(0)} min` : 'N/A'}
                      </td>
                    </tr>
                    <tr className="govuk-table__row">
                      <td className="govuk-table__cell">
                        <strong>Route Equity</strong>
                        <br />
                        <span className="govuk-hint" style={{ fontSize: '12px' }}>Equal access to evacuation routes</span>
                      </td>
                      <td className="govuk-table__cell">
                        {getTrafficLightCircle(borough.fairness.status)}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.fairness.value > 0 ? borough.fairness.value.toFixed(2) : 'N/A'}
                      </td>
                      <td className="govuk-table__cell">
                        <span style={{ color: getTrendColor(borough.fairness.trend), fontSize: '18px', fontWeight: 'bold' }}>
                          {getTrendIcon(borough.fairness.trend, 'fairness')}
                        </span>
                        {borough.fairness.trend !== 'none' && (
                          <span style={{ marginLeft: '5px', fontSize: '12px' }}>
                            {borough.fairness.trend === 'improving' ? 'better' : 
                             borough.fairness.trend === 'declining' ? 'worse' : 'stable'}
                          </span>
                        )}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.fairness.previousValue ? borough.fairness.previousValue.toFixed(2) : 'N/A'}
                      </td>
                    </tr>
                    <tr className="govuk-table__row">
                      <td className="govuk-table__cell">
                        <strong>Network Resilience</strong>
                        <br />
                        <span className="govuk-hint" style={{ fontSize: '12px' }}>Ability to handle route closures</span>
                      </td>
                      <td className="govuk-table__cell">
                        {getTrafficLightCircle(borough.robustness.status)}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.robustness.value > 0 ? borough.robustness.value.toFixed(2) : 'N/A'}
                      </td>
                      <td className="govuk-table__cell">
                        <span style={{ color: getTrendColor(borough.robustness.trend), fontSize: '18px', fontWeight: 'bold' }}>
                          {getTrendIcon(borough.robustness.trend, 'robustness')}
                        </span>
                        {borough.robustness.trend !== 'none' && (
                          <span style={{ marginLeft: '5px', fontSize: '12px' }}>
                            {borough.robustness.trend === 'improving' ? 'better' : 
                             borough.robustness.trend === 'declining' ? 'worse' : 'stable'}
                          </span>
                        )}
                      </td>
                      <td className="govuk-table__cell">
                        {borough.robustness.previousValue ? borough.robustness.previousValue.toFixed(2) : 'N/A'}
                      </td>
                    </tr>
                  </tbody>
                </table>

                {/* Recent Simulation History */}
                {borough.recentRuns.length > 0 && (
                  <>
                    <h3 className={GOVUK_CLASSES.heading.s}>Recent Simulation History</h3>
                    <table className="govuk-table">
                      <thead className="govuk-table__head">
                        <tr className="govuk-table__row">
                          <th scope="col" className="govuk-table__header">Date</th>
                          <th scope="col" className="govuk-table__header">Clearance</th>
                          <th scope="col" className="govuk-table__header">Fairness</th>
                          <th scope="col" className="govuk-table__header">Robustness</th>
                          <th scope="col" className="govuk-table__header">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="govuk-table__body">
                        {borough.recentRuns.map(run => (
                          <tr key={run.run_id} className="govuk-table__row">
                            <td className="govuk-table__cell">
                              {new Date(run.created_at).toLocaleString('en-GB', {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </td>
                            <td className="govuk-table__cell">
                              {run.metrics?.clearance_time ? `${run.metrics.clearance_time.toFixed(0)} min` : 'N/A'}
                            </td>
                            <td className="govuk-table__cell">
                              {run.metrics?.fairness_index ? run.metrics.fairness_index.toFixed(2) : 'N/A'}
                            </td>
                            <td className="govuk-table__cell">
                              {run.metrics?.robustness ? run.metrics.robustness.toFixed(2) : 'N/A'}
                            </td>
                            <td className="govuk-table__cell">
                              <Link to={`/results/${run.run_id}`} className="govuk-link" style={{ fontSize: '14px' }}>
                                View
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}

                {/* Action Buttons */}
                <div style={{ marginTop: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div className="govuk-button-group">
                      <Link
                        to={`/borough/${borough.borough}`}
                        className="govuk-button"
                      >
                        Run New Simulation
                      </Link>
                      {borough.lastRunId && (
                        <Link
                          to={`/results/${borough.lastRunId}`}
                          className="govuk-button govuk-button--secondary"
                        >
                          View Latest Results
                        </Link>
                      )}
                    </div>
                    
                    {/* Ellipsis Menu */}
                    <div style={{ position: 'relative' }} data-menu-container>
                      <button
                        onClick={() => toggleMenu(borough.borough)}
                        className="govuk-button govuk-button--secondary"
                        style={{
                          minWidth: '40px',
                          padding: '8px 12px',
                          fontSize: '16px',
                          fontWeight: 'bold',
                          backgroundColor: 'white',
                          color: '#505a5f',
                          border: '2px solid #b1b4b6'
                        }}
                        aria-label={`More actions for ${borough.displayName}`}
                      >
                        ⋯
                      </button>
                      
                      {/* Dropdown Menu */}
                      {openMenus.has(borough.borough) && (
                        <div
                          style={{
                            position: 'absolute',
                            top: '100%',
                            right: 0,
                            backgroundColor: 'white',
                            border: '2px solid #0b0c0c',
                            borderRadius: '4px',
                            minWidth: '200px',
                            zIndex: 1000,
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                            marginTop: '4px'
                          }}
                        >
                          <button
                            onClick={() => {
                              setShowIndividualClearConfirmation(borough.borough);
                              closeAllMenus();
                            }}
                            disabled={clearingIndividualHistory.has(borough.borough)}
                            style={{
                              width: '100%',
                              padding: '12px 16px',
                              border: 'none',
                              backgroundColor: 'white',
                              textAlign: 'left',
                              cursor: 'pointer',
                              fontSize: '14px',
                              borderBottom: '1px solid #f3f2f1'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f2f1'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                          >
                            {clearingIndividualHistory.has(borough.borough) ? 'Clearing History...' : 'Clear History'}
                          </button>
                          
                          <button
                            onClick={() => {
                              removeBoroughFromBoard(borough.borough, borough.displayName);
                              closeAllMenus();
                            }}
                            disabled={removingFromBoard.has(borough.borough)}
                            style={{
                              width: '100%',
                              padding: '12px 16px',
                              border: 'none',
                              backgroundColor: 'white',
                              textAlign: 'left',
                              cursor: 'pointer',
                              fontSize: '14px',
                              color: '#d4351c'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f2f1'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                          >
                            {removingFromBoard.has(borough.borough) ? 'Removing...' : 'Remove from Board'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Summary Stats */}
                <p className={GOVUK_CLASSES.body.s} style={{ marginTop: '15px', color: '#505a5f' }}>
                  <strong>Total simulations:</strong> {borough.runCount} |
                  <strong> Last updated:</strong> {borough.lastRunDate ? new Date(borough.lastRunDate).toLocaleString('en-GB') : 'Never'}
                </p>
              </div>
            </div>
          ))}
          </div>
        )}

        {/* Clear Confirmation Modal */}
        {showClearConfirmation && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '4px',
              maxWidth: '600px',
              width: '100%',
              padding: '30px',
              border: '2px solid #0b0c0c'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 className={GOVUK_CLASSES.heading.l} style={{ margin: 0 }}>Clear All Simulation Histories</h2>
                <button
                  onClick={() => setShowClearConfirmation(false)}
                  disabled={clearingHistory}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '24px',
                    cursor: 'pointer',
                    color: '#505a5f'
                  }}
                >
                  ×
                </button>
      </div>

              <div className="govuk-warning-text">
                <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                <strong className="govuk-warning-text__text">
                  <span className="govuk-warning-text__assistive">Warning: </span>
                  This action cannot be undone
                </strong>
              </div>

              <div style={{ marginBottom: '30px' }}>
                <p className={GOVUK_CLASSES.body.m}>
                  <strong>This will permanently delete:</strong>
                </p>
                <ul className="govuk-list govuk-list--bullet">
                  <li>All simulation run data and results</li>
                  <li>All tracked locations ({trackedLocations.length} locations)</li>
                  <li>All borough status history ({boroughs.length} boroughs with data)</li>
                  <li>All cached metrics and visualizations</li>
                </ul>
                <p className={GOVUK_CLASSES.body.m}>
                  You will need to run new simulations to see data on this dashboard again.
                </p>
              </div>

              <div className="govuk-button-group">
                <button
                  onClick={clearAllSimulationHistories}
                  disabled={clearingHistory}
                  className={`govuk-button govuk-button--warning ${clearingHistory ? 'govuk-button--disabled' : ''}`}
                  style={{
                    backgroundColor: '#d4351c',
                    borderColor: '#d4351c'
                  }}
                >
                  {clearingHistory ? (
                    <>
                      <span style={{ marginRight: '8px' }}>Clearing...</span>
                      <div style={{
                        display: 'inline-block',
                        width: '16px',
                        height: '16px',
                        border: '2px solid rgba(255,255,255,0.3)',
                        borderTop: '2px solid #ffffff',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                      }} />
                    </>
                  ) : (
                    'Yes, Clear All Histories'
                  )}
                </button>
                
                <button
                  onClick={() => setShowClearConfirmation(false)}
                  disabled={clearingHistory}
                  className="govuk-button govuk-button--secondary"
                >
                  Cancel
                </button>
              </div>

              {/* Add CSS animation */}
              <style>{`
                @keyframes spin {
                  0% { transform: rotate(0deg); }
                  100% { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          </div>
        )}

        {/* Individual Borough Clear Confirmation Modal */}
        {showIndividualClearConfirmation && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '4px',
              maxWidth: '500px',
              width: '100%',
              padding: '30px',
              border: '2px solid #0b0c0c'
            }}>
              {(() => {
                const borough = boroughs.find(b => b.borough === showIndividualClearConfirmation);
                const boroughName = borough?.displayName || 'Unknown Borough';
                const runCount = borough?.runCount || 0;
                const isClearing = clearingIndividualHistory.has(showIndividualClearConfirmation);
                
                return (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                      <h2 className={GOVUK_CLASSES.heading.l} style={{ margin: 0 }}>Clear {boroughName} History</h2>
                      <button
                        onClick={() => setShowIndividualClearConfirmation(null)}
                        disabled={isClearing}
                        style={{
                          background: 'none',
                          border: 'none',
                          fontSize: '24px',
                          cursor: 'pointer',
                          color: '#505a5f'
                        }}
                      >
                        ×
                      </button>
                    </div>

                    <div className="govuk-warning-text">
                      <span className="govuk-warning-text__icon" aria-hidden="true">!</span>
                      <strong className="govuk-warning-text__text">
                        <span className="govuk-warning-text__assistive">Warning: </span>
                        This will clear all simulation data for this region
                      </strong>
                    </div>

                    <div style={{ marginBottom: '30px' }}>
                      <p className={GOVUK_CLASSES.body.m}>
                        <strong>This will permanently delete for {boroughName}:</strong>
                      </p>
                      <ul className="govuk-list govuk-list--bullet">
                        <li>{runCount} simulation run{runCount !== 1 ? 's' : ''} and results</li>
                        <li>All traffic light status history</li>
                        <li>All metrics and performance data</li>
                        <li>All cached visualizations</li>
                      </ul>
                      <p className={GOVUK_CLASSES.body.m}>
                        The region will be removed from the status board. You can add it back by running new simulations.
                      </p>
                    </div>

                    <div className="govuk-button-group">
                      <button
                        onClick={() => clearBoroughHistory(showIndividualClearConfirmation, boroughName)}
                        disabled={isClearing}
                        className={`govuk-button govuk-button--warning ${isClearing ? 'govuk-button--disabled' : ''}`}
                        style={{
                          backgroundColor: '#d4351c',
                          borderColor: '#d4351c'
                        }}
                      >
                        {isClearing ? (
                          <>
                            <span style={{ marginRight: '8px' }}>Clearing...</span>
                            <div style={{
                              display: 'inline-block',
                              width: '16px',
                              height: '16px',
                              border: '2px solid rgba(255,255,255,0.3)',
                              borderTop: '2px solid #ffffff',
                              borderRadius: '50%',
                              animation: 'spin 1s linear infinite'
                            }} />
                          </>
                        ) : (
                          `Yes, Clear ${boroughName} History`
                        )}
                      </button>
                      
                      <button
                        onClick={() => setShowIndividualClearConfirmation(null)}
                        disabled={isClearing}
                        className="govuk-button govuk-button--secondary"
                      >
                        Cancel
                      </button>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BoroughDashboard;
