/**
 * City-Specific Visualisation Component
 * Displays evacuation visualisations for UK cities using OSMnx street networks
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Title,
  Text,
  Grid,
  Group,
  Badge,
  Stack,
  Paper,
  Button,
  Select,
  Alert
} from '@mantine/core';
import {
  IconMapPin,
  IconRefresh,
  IconDownload,
  IconInfoCircle,
  IconPlayerPlay,
  IconCheck,
  IconAlertTriangle,
  IconMaximize,
  IconMinimize,
  IconExternalLink
} from '@tabler/icons-react';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';

interface CityVisualisationProps {
  city: string;
  simulationData?: any;
  onCityChange?: (city: string) => void;
}

const CitySpecificVisualisation: React.FC<CityVisualisationProps> = ({
  city,
  simulationData,
  onCityChange
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<{
    message: string;
    runId?: string;
    type: 'idle' | 'kicked-off' | 'running' | 'completed' | 'error';
  }>({ message: '', type: 'idle' });
  const [visualisationData, setVisualisationData] = useState<any>(null);
  const [cityStatus, setCityStatus] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'network' | 'grid'>('network');
  const [availableCities, setAvailableCities] = useState<{value: string, label: string}[]>([
    { value: 'westminster', label: 'Westminster' },
    { value: 'manhattan', label: 'Manhattan' }
  ]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Handle ESC key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    if (isFullscreen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isFullscreen]);

  // Render network graph visualisation (shared between London and Manhattan)
  const renderNetworkGridView = (cityPrefix: string = '') => {
    if (!visualisationData?.network_graph) return null;

    const { nodes, edges, bounds } = visualisationData.network_graph;
    const xRange = bounds.max_x - bounds.min_x;
    const yRange = bounds.max_y - bounds.min_y;
    
    // Normalize coordinates to fit in 0-100 viewBox
    const normalizeX = (x: number) => ((x - bounds.min_x) / xRange) * 100;
    const normalizeY = (y: number) => (1 - (y - bounds.min_y) / yRange) * 100; // Flip Y axis
    
    // Limit edges and nodes for cleaner visualization
    const maxEdges = 2000;  // Reduced for cleaner display
    let displayEdges = edges;
    if (edges.length > maxEdges) {
      // Use systematic sampling for better distribution
      const step = Math.ceil(edges.length / maxEdges);
      displayEdges = edges.filter((_, index) => index % step === 0);
    }
    
    // Limit nodes for cleaner visualization
    const maxNodes = 1000;  // Reduced for cleaner display
    let displayNodes = nodes;
    if (nodes.length > maxNodes) {
      // Use systematic sampling for better distribution
      const step = Math.ceil(nodes.length / maxNodes);
      displayNodes = nodes.filter((_, index) => index % step === 0);
    }
    
    const containerStyle = isFullscreen 
      ? { 
          position: 'fixed' as const, 
          top: 0, 
          left: 0, 
          width: '100vw', 
          height: '100vh', 
          zIndex: 9999, 
          backgroundColor: '#f8f9fa' 
        }
      : { 
          height: '400px', 
          width: '100%', 
          position: 'relative' as const, 
          backgroundColor: '#f8f9fa' 
        };

    return (
      <div style={containerStyle}>
        {/* Controls */}
        <div style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 10 }}>
          <Group gap="xs">
            <Button
              size="xs"
              variant="light"
              onClick={(e) => {
                const svg = e.currentTarget.parentElement?.parentElement?.parentElement?.querySelector('svg');
                if (svg) {
                  svg.setAttribute('viewBox', '0 0 100 100');
                }
              }}
            >
              Reset Zoom
            </Button>
            <Button
              size="xs"
              variant="light"
              leftSection={isFullscreen ? <IconMinimize size={14} /> : <IconMaximize size={14} />}
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            </Button>
          </Group>
        </div>
        <svg 
          width="100%" 
          height="100%" 
          viewBox="0 0 100 100" 
          style={{ 
            border: '1px solid #ccc',
            cursor: 'grab'
          }}
          onWheel={(e) => {
            e.preventDefault();
            const svg = e.currentTarget;
            const rect = svg.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width * 100;
            const y = (e.clientY - rect.top) / rect.height * 100;
            
            const currentViewBox = svg.getAttribute('viewBox')?.split(' ').map(Number) || [0, 0, 100, 100];
            const [vx, vy, vw, vh] = currentViewBox;
            
            const zoomFactor = e.deltaY > 0 ? 1.2 : 0.8;
            const newWidth = vw * zoomFactor;
            const newHeight = vh * zoomFactor;
            
            // Keep zoom centered on mouse position
            const newX = x - (x - vx) * zoomFactor;
            const newY = y - (y - vy) * zoomFactor;
            
            svg.setAttribute('viewBox', `${newX} ${newY} ${newWidth} ${newHeight}`);
          }}
          onMouseDown={(e) => {
            const svg = e.currentTarget;
            svg.style.cursor = 'grabbing';
            
            const startPoint = { x: e.clientX, y: e.clientY };
            const currentViewBox = svg.getAttribute('viewBox')?.split(' ').map(Number) || [0, 0, 100, 100];
            const [startVx, startVy, vw, vh] = currentViewBox;
            
            const handleMouseMove = (moveEvent: MouseEvent) => {
              const dx = (moveEvent.clientX - startPoint.x) / svg.getBoundingClientRect().width * vw;
              const dy = (moveEvent.clientY - startPoint.y) / svg.getBoundingClientRect().height * vh;
              
              svg.setAttribute('viewBox', `${startVx - dx} ${startVy - dy} ${vw} ${vh}`);
            };
            
            const handleMouseUp = () => {
              svg.style.cursor = 'grab';
              document.removeEventListener('mousemove', handleMouseMove);
              document.removeEventListener('mouseup', handleMouseUp);
            };
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
          }}>
          {/* Street Network Edges */}
          {displayEdges.map((edge: any, edgeIndex: number) => {
            const sourceNode = nodes.find((n: any) => n.id === edge.source);
            const targetNode = nodes.find((n: any) => n.id === edge.target);
            
            if (!sourceNode || !targetNode) return null;
            
            return (
              <line
                key={`${cityPrefix}edge-${edgeIndex}`}
                x1={normalizeX(sourceNode.x)}
                y1={normalizeY(sourceNode.y)}
                x2={normalizeX(targetNode.x)}
                y2={normalizeY(targetNode.y)}
                stroke="#888"
                strokeWidth="0.1"
                opacity="0.6"
              />
            );
          })}
          
          {/* Street Network Nodes */}
          {displayNodes.map((node: any, nodeIndex: number) => (
            <circle
              key={`${cityPrefix}node-${nodeIndex}`}
              cx={normalizeX(node.x)}
              cy={normalizeY(node.y)}
              r="0.3"
              fill="#666"
              opacity="0.7"
            />
          ))}
          
          {/* A* Routes Overlay */}
          {visualisationData.astar_routes && visualisationData.astar_routes.map((route: any, routeIndex: number) => {
            if (!route.coordinates || route.coordinates.length < 2) return null;
            
            const normalizedCoords = route.coordinates.map((coord: number[]) => [
              normalizeX(coord[0]),
              normalizeY(coord[1])
            ]);
            
            const pathData = normalizedCoords.map((coord, i) => 
              `${i === 0 ? 'M' : 'L'} ${coord[0]} ${coord[1]}`
            ).join(' ');
            
            return (
              <g key={`${cityPrefix}astar-${routeIndex}`}>
                <path
                  d={pathData}
                  fill="none"
                  stroke="#0088FE"
                  strokeWidth="1.2"
                  opacity="1.0"
                />
                {/* Start point */}
                <circle
                  cx={normalizedCoords[0][0]}
                  cy={normalizedCoords[0][1]}
                  r="1"
                  fill="#0088FE"
                />
                {/* End point */}
                <circle
                  cx={normalizedCoords[normalizedCoords.length - 1][0]}
                  cy={normalizedCoords[normalizedCoords.length - 1][1]}
                  r="1"
                  fill="#FF8042"
                />
              </g>
            );
          })}
          
          {/* Biased Random Walk Density Points Overlay */}
          {visualisationData.random_walks && visualisationData.random_walks.density_data && (
            <>
              {visualisationData.random_walks.density_data.x.map((x: number, i: number) => {
                const y = visualisationData.random_walks.density_data.y[i];
                if (x === undefined || y === undefined) return null;
                
                return (
                  <circle
                    key={`${cityPrefix}walk-${i}`}
                    cx={normalizeX(x)}
                    cy={normalizeY(y)}
                    r="1.0"
                    fill="#00C49F"
                    opacity="0.9"
                  />
                );
              })}
            </>
          )}
          
          {/* Legend */}
          <g transform="translate(5, 5)">
            <rect x="0" y="0" width="30" height="25" fill="white" fillOpacity="0.9" stroke="#ccc" strokeWidth="0.2"/>
            <line x1="3" y1="5" x2="8" y2="5" stroke="#555" strokeWidth="0.4"/>
            <text x="10" y="6.5" fontSize="2.5" fill="#333">Street Network</text>
            <circle cx="3" cy="10" r="1" fill="#0088FE"/>
            <text x="6" y="11.5" fontSize="2.5" fill="#333">A* Routes</text>
            <circle cx="3" cy="15" r="1" fill="#00C49F"/>
            <text x="6" y="16.5" fontSize="2.5" fill="#333">Random Walk</text>
            <circle cx="3" cy="20" r="1" fill="#FF8042"/>
            <text x="6" y="21.5" fontSize="2.5" fill="#333">Exit Points</text>
          </g>
        </svg>
      </div>
    );
  };

  const loadCityVisualisation = async () => {
    setIsLoading(true);
    console.log(`🏙️ Loading real science visualisation for city: ${city}`);
    try {
      // PHASE 2 FIX: Prioritize real science simulation data
      let visualisationData = null;
      let dataSource = 'none';
      
      // Priority 1: Check for cached real science data
      if ((window as any).citySimulationData?.simulation_engine === 'real_evacuation_science') {
        console.log('✅ Priority 1: Using cached real science data');
        visualisationData = (window as any).citySimulationData;
        dataSource = 'cached_real';
      }
      
      // Priority 2: Load fresh real science data from API
      if (!visualisationData) {
        const visualisationUrl = `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(city)}`;
        console.log(`📡 Priority 2: Fetching real science data: ${visualisationUrl}`);
        
        // Add longer timeout for real science simulations
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes
        
        const visualisationResponse = await fetch(visualisationUrl, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (visualisationResponse.ok) {
          const data = await visualisationResponse.json();
          console.log(`✅ Real science data loaded for ${city}:`, {
            astar_routes: data.astar_routes?.length || 0,
            random_walks: data.random_walks?.num_walks || 0,
            network_graph: data.network_graph?.nodes?.length || 0,
            real_metrics: !!data.calculated_metrics,
            simulation_engine: data.simulation_engine,
            algorithm_features: data.algorithm_features
          });
          
          // Only use data if it's from real science simulation
          if (data.simulation_engine === 'real_evacuation_science') {
            visualisationData = data;
            dataSource = 'api_real';
            // Cache the real science data
            (window as any).citySimulationData = data;
          } else {
            console.log('⚠️ Data is not from real science simulation, generating new...');
          }
        } else if (visualisationResponse.status === 404) {
          console.log(`📦 No cached data for ${city}, will generate real science simulation...`);
        } else {
          const errorText = await visualisationResponse.text();
          console.error(`❌ Visualisation response not ok: ${visualisationResponse.status}`, errorText);
        }
      }
      
      // Priority 3: Don't auto-generate - let user decide
      if (!visualisationData) {
        console.log(`ℹ️ No visualization data available for ${city} - user should run simulation manually`);
        setError('No simulation data available. Please run a new simulation.');
        setIsLoading(false);
        return;
      }
      
      setVisualisationData(visualisationData);
      console.log(`🎉 Final real science data set for ${city}:`, { source: dataSource });

      // Load status
      const statusResponse = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.status(city)}`);
      if (statusResponse.ok) {
        const status = await statusResponse.json();
        setCityStatus(status);
      }
    } catch (error) {
      console.error('Failed to load real science visualisation:', error);
      if (error.name === 'AbortError') {
        console.log('⏰ Request timed out - simulation is taking longer than expected');
        alert('Simulation is taking longer than expected. Please try a smaller borough like Westminster or Camden.');
      } else {
        console.error('❌ Visualization error:', error);
        alert(`Failed to load visualization: ${error.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (city) {
      loadCityVisualisation();
    }
  }, [city]);

  // Load available cities
  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.cities}`);
        if (response.ok) {
          const data = await response.json();
          const cityOptions = data.cities.map((cityName: string) => ({
            value: cityName,
            label: cityName.charAt(0).toUpperCase() + cityName.slice(1)
          }));
          setAvailableCities(cityOptions);
        }
      } catch (error) {
        console.error('Failed to fetch cities:', error);
        // Keep default cities on error
      }
    };

    fetchCities();
  }, []);

  const runSimulation = async () => {
    setIsRunning(true);
    setRunStatus({ message: 'Kicking off simulation...', type: 'kicked-off' });

    try {
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.run(city)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          num_simulations: city === 'manhattan' ? 30 : 10,
          num_routes: city === 'london' ? 8 : 5,
          scenario_config: {}
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`🚀 Simulation started for ${city}, run_id: ${result.run_id}`);

        // Show "kicked off" status with run ID
        setRunStatus({
          message: `✅ Simulation kicked off! Run ID: ${result.run_id}`,
          runId: result.run_id,
          type: 'kicked-off'
        });

        // After 2 seconds, change to "running" status
        setTimeout(() => {
          setRunStatus({
            message: `Running simulation... (Run ID: ${result.run_id})`,
            runId: result.run_id,
            type: 'running'
          });
        }, 2000);

        // Poll for completion
        const pollInterval = setInterval(async () => {
          try {
            const vizResponse = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(city)}`);
            if (vizResponse.ok) {
              const data = await vizResponse.json();
              if (data.status === 'completed' || data.visualisation_image) {
                console.log(`✅ Simulation completed for ${city}`);
                setVisualisationData(data);
                setIsRunning(false);
                setRunStatus({
                  message: `✅ Simulation completed! Run ID: ${result.run_id}`,
                  runId: result.run_id,
                  type: 'completed'
                });
                clearInterval(pollInterval);

                // Clear success message after 10 seconds
                setTimeout(() => {
                  setRunStatus({ message: '', type: 'idle' });
                }, 10000);
              }
            }
          } catch (error) {
            console.error('Polling error:', error);
          }
        }, 3000);

        // Timeout after 60 seconds
        setTimeout(() => {
          clearInterval(pollInterval);
          if (runStatus.type === 'running') {
            setIsRunning(false);
            setRunStatus({
              message: `⚠️ Simulation may still be running. Check the Runs tab for updates.`,
              runId: result.run_id,
              type: 'error'
            });
          }
        }, 60000);
      } else {
        const errorText = await response.text();
        setRunStatus({
          message: `❌ Failed to start simulation: ${errorText}`,
          type: 'error'
        });
        setIsRunning(false);
      }
    } catch (error) {
      console.error('Failed to run simulation:', error);
      setRunStatus({
        message: `❌ Failed to start simulation: ${error.message}`,
        type: 'error'
      });
      setIsRunning(false);
    }
  };

  const renderLondonVisualisation = () => (
    <Grid>
      <Grid.Col span={12}>
        <Card withBorder>
          <Card.Section p="md">
            <Group justify="space-between" style={{ flexWrap: 'wrap', gap: '1rem' }}>
              <Title order={4}>London Street Network Evacuation Routes</Title>
              <Group style={{ flexWrap: 'wrap' }}>
                <Button
                  size="sm"
                  variant={viewMode === 'network' ? 'filled' : 'outline'}
                  onClick={() => setViewMode('network')}
                  style={{ minWidth: '100px' }}
                >
                  Street View
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === 'grid' ? 'filled' : 'outline'}
                  onClick={() => setViewMode('grid')}
                  style={{ minWidth: '100px' }}
                >
                  Grid View
                </Button>
                <Badge color="blue" size="lg">OSMnx Network</Badge>
              </Group>
            </Group>
          </Card.Section>
          <Card.Section p="md">
            {isLoading ? (
              <Paper p="xl" style={{ height: '400px', backgroundColor: '#f8f9fa' }}>
                <Stack align="center" justify="center" style={{ height: '100%' }}>
                  <IconRefresh size={48} color="#666" className="animate-spin" />
                  <Text c="dimmed">Loading London street network...</Text>
                  <Text size="xs" c="dimmed">Extracting OSMnx graph data</Text>
                </Stack>
              </Paper>
            ) : viewMode === 'grid' ? (
              visualisationData?.network_graph ? 
                renderNetworkGridView('london-') 
                : (
                  <Paper p="xl" style={{ height: '400px', backgroundColor: '#f8f9fa' }}>
                    <Stack align="center" justify="center" style={{ height: '100%' }}>
                      <IconMapPin size={48} color="#666" />
                      <Text c="dimmed">Grid view requires network graph data</Text>
                      <Text size="xs" c="dimmed">Run simulation to generate street network</Text>
                    </Stack>
                  </Paper>
                )
            ) : visualisationData?.interactive_map_html ? (
              <div style={{ position: 'relative', height: '400px', width: '100%' }}>
                {/* Map Fullscreen Button - positioned to avoid layer controls */}
                <div style={{ 
                  position: 'absolute', 
                  bottom: '10px', 
                  left: '10px', 
                  zIndex: 1000,
                  pointerEvents: 'auto'
                }}>
                  <Button
                    size="xs"
                    variant="filled"
                    color="blue"
                    leftSection={isFullscreen ? <IconMinimize size={14} /> : <IconMaximize size={14} />}
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    style={{ 
                      boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                      border: '1px solid #fff'
                    }}
                  >
                    {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
                  </Button>
                </div>
                <div 
                  dangerouslySetInnerHTML={{ 
                    __html: visualisationData.interactive_map_html 
                  }}
                  style={{ 
                    height: isFullscreen ? '100vh' : '400px', 
                    width: isFullscreen ? '100vw' : '100%',
                    position: isFullscreen ? 'fixed' : 'relative',
                    top: isFullscreen ? 0 : 'auto',
                    left: isFullscreen ? 0 : 'auto',
                    zIndex: isFullscreen ? 9998 : 'auto',
                    backgroundColor: '#fff'
                  }}
                />
                {/* Fullscreen Exit Button - only visible in fullscreen */}
                {isFullscreen && (
                  <div style={{ 
                    position: 'fixed', 
                    top: '20px', 
                    right: '20px', 
                    zIndex: 10000,
                    pointerEvents: 'auto'
                  }}>
                    <Button
                      size="sm"
                      variant="filled"
                      color="red"
                      leftSection={<IconMinimize size={16} />}
                      onClick={() => setIsFullscreen(false)}
                      style={{ 
                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                        border: '2px solid #fff'
                      }}
                    >
                      Exit Fullscreen
                    </Button>
                  </div>
                )}
              </div>
            ) : visualisationData?.routes_data ? (
              <Paper p="md" style={{ height: '400px', backgroundColor: '#f0f8ff' }}>
                <Stack gap="sm">
                  <Text fw={600}>London Evacuation Routes Generated</Text>
                  <Text size="sm">
                    ✅ {visualisationData.routes_data.num_successful_routes} evacuation routes
                  </Text>
                  <Text size="sm">
                    📍 {visualisationData.routes_data.total_network_nodes} network nodes
                  </Text>
                  <Text size="sm">
                    🗺️ Coverage: {visualisationData.routes_data.network_bounds ? 'Full London network' : 'Loading...'}
                  </Text>
                  <Text size="xs" c="dimmed">Interactive Folium map will be generated</Text>
                  {visualisationData && (
                    <Text size="xs" c="dimmed">
                      Debug: {JSON.stringify(Object.keys(visualisationData))}
                    </Text>
                  )}
                </Stack>
              </Paper>
            ) : (
              <Paper p="xl" style={{ height: '400px', backgroundColor: '#f8f9fa' }}>
                <Stack align="center" justify="center" style={{ height: '100%' }}>
                  <IconMapPin size={48} color="#666" />
                  <Text c="dimmed">
                    {isRunning || runStatus.type === 'running' || runStatus.type === 'kicked-off'
                      ? 'Simulation running - visualization will appear when complete'
                      : isLoading
                      ? 'Loading visualization data...'
                      : visualisationData
                      ? 'Click Refresh to reload visualization'
                      : 'No data yet - click Run to start simulation'}
                  </Text>
                  <Text size="xs" c="dimmed">Real-time A* pathfinding on OSM data</Text>
                </Stack>
              </Paper>
            )}
          </Card.Section>
        </Card>
      </Grid.Col>

      <Grid.Col span={6}>
        <Card withBorder>
          <Card.Section p="md">
            <Title order={4}>Network Statistics</Title>
          </Card.Section>
          <Card.Section p="md">
            <Stack gap="sm">
              <Group justify="space-between">
                <Text>Total Network Nodes</Text>
                <Text fw={600}>{visualisationData?.metrics?.total_network_nodes || 0}</Text>
              </Group>
              <Group justify="space-between">
                <Text>Successful Routes</Text>
                <Text fw={600}>{visualisationData?.metrics?.num_successful_routes || 0}</Text>
              </Group>
              <Group justify="space-between">
                <Text>Network Coverage</Text>
                <Text fw={600}>{visualisationData?.metrics?.network_coverage || 'Loading...'}</Text>
              </Group>
            </Stack>
          </Card.Section>
        </Card>
      </Grid.Col>

      <Grid.Col span={6}>
        <Card withBorder>
          <Card.Section p="md">
            <Title order={4}>Route Analysis</Title>
          </Card.Section>
          <Card.Section p="md">
            <Text size="sm" c="dimmed">
              Real London street network extracted using OSMnx. Routes calculated using A* 
              pathfinding algorithm with traffic-aware weighting. Displays actual evacuation 
              paths from City of London to boundary exit points.
            </Text>
          </Card.Section>
        </Card>
      </Grid.Col>
    </Grid>
  );


  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <div>
          <Title order={3}>
            {city.charAt(0).toUpperCase() + city.slice(1).replace(/_/g, ' ')} Network Analysis
          </Title>
          <Text c="dimmed">
            Real street network evacuation routing with OSMnx
          </Text>
        </div>
        
        <Group>
          {cityStatus && (
            <Badge 
              color={cityStatus.supported ? 'green' : 'red'} 
              leftSection={cityStatus.supported ? <IconCheck size={12} /> : <IconAlertTriangle size={12} />}
            >
              {cityStatus.supported ? 'Available' : 'Unavailable'}
            </Badge>
          )}
          {onCityChange && (
            <Select
              value={city}
              onChange={(value) => onCityChange(value || 'westminster')}
              data={availableCities}
              size="sm"
            />
          )}
          <Button
            variant="filled"
            size="sm"
            leftSection={<IconPlayerPlay size={16} />}
            onClick={runSimulation}
            loading={isRunning}
            disabled={isLoading}
          >
            Run Simulation
          </Button>
          {visualisationData?.run_id && (
            <Button
              variant="light"
              size="sm"
              leftSection={<IconExternalLink size={16} />}
              onClick={() => window.open(`/results/${visualisationData.run_id}`, '_blank')}
            >
              View Results
            </Button>
          )}
          <Button
            variant="light"
            size="sm"
            leftSection={<IconRefresh size={16} />}
            onClick={loadCityVisualisation}
            loading={isLoading}
            disabled={isRunning}
          >
            Refresh
          </Button>
        </Group>
      </Group>

      {/* Simulation Status Alert */}
      {runStatus.message && (
        <Alert
          icon={
            runStatus.type === 'completed' ? <IconCheck size={16} /> :
            runStatus.type === 'error' ? <IconAlertTriangle size={16} /> :
            <IconInfoCircle size={16} />
          }
          title={
            runStatus.type === 'kicked-off' ? 'Simulation Started' :
            runStatus.type === 'running' ? 'Simulation Running' :
            runStatus.type === 'completed' ? 'Simulation Completed' :
            runStatus.type === 'error' ? 'Error' :
            'Status'
          }
          color={
            runStatus.type === 'completed' ? 'green' :
            runStatus.type === 'error' ? 'red' :
            runStatus.type === 'running' ? 'blue' :
            'cyan'
          }
          withCloseButton
          onClose={() => setRunStatus({ message: '', type: 'idle' })}
          style={{ marginBottom: '1rem' }}
        >
          <Stack gap="xs">
            <Text size="sm">{runStatus.message}</Text>
            {runStatus.runId && runStatus.type !== 'error' && (
              <Group gap="xs">
                <Button
                  size="xs"
                  variant="light"
                  leftSection={<IconExternalLink size={14} />}
                  onClick={() => window.open(`/results/${runStatus.runId}`, '_blank')}
                >
                  View in Runs Tab
                </Button>
              </Group>
            )}
          </Stack>
        </Alert>
      )}

      {renderLondonVisualisation()}

      {/* 🔬 Real Science Metrics Display */}
      {visualisationData?.real_metrics && (
        <Card withBorder>
          <Card.Section p="md">
            <Group justify="space-between" align="center">
              <Title order={4}>🔬 Real Science Metrics</Title>
              <Badge color="blue" variant="light">
                {visualisationData.simulation_engine || 'Real Evacuation Science'}
              </Badge>
            </Group>
          </Card.Section>
          <Card.Section p="md">
            <Grid>
              <Grid.Col span={6}>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text>Clearance Time (P50)</Text>
                    <Text fw={600} c="blue">{visualisationData.real_metrics.clearance_time_p50?.toFixed(1) || 0} min</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text>Clearance Time (P95)</Text>
                    <Text fw={600} c="blue">{visualisationData.real_metrics.clearance_time_p95?.toFixed(1) || 0} min</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text>Total Evacuated</Text>
                    <Text fw={600} c="green">{visualisationData.real_metrics.total_evacuated || 0} people</Text>
                  </Group>
                </Stack>
              </Grid.Col>
              <Grid.Col span={6}>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text>Behavioral Realism</Text>
                    <Text fw={600} c="green">{(visualisationData.real_metrics.behavioral_realism_score * 100)?.toFixed(0) || 0}%</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text>Bottlenecks Identified</Text>
                    <Text fw={600} c="orange">{visualisationData.real_metrics.bottleneck_count || 0}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text>Route Efficiency</Text>
                    <Text fw={600} c="purple">{(visualisationData.real_metrics.route_efficiency * 100)?.toFixed(0) || 0}%</Text>
                  </Group>
                </Stack>
              </Grid.Col>
            </Grid>
            
            {visualisationData.algorithm_transformation && (
              <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light" mt="md">
                <Text size="sm">
                  <strong>Algorithm Enhancements:</strong><br />
                  • A*: {visualisationData.algorithm_transformation.astar_enhancement}<br />
                  • Random Walk: {visualisationData.algorithm_transformation.random_walk_enhancement}<br />
                  • Metrics: {visualisationData.algorithm_transformation.metrics_enhancement}
                </Text>
              </Alert>
            )}
          </Card.Section>
        </Card>
      )}

      <Alert 
        icon={<IconInfoCircle size={16} />} 
        title="Simulation Methods" 
        color="blue" 
        variant="light"
      >
        <Text size="sm">
          {cityStatus?.capabilities ? (
            <>
              <strong>Network Type:</strong> {cityStatus.capabilities.network_type}<br />
              <strong>Algorithm:</strong> {cityStatus.capabilities.routing_algorithm}<br />
              {cityStatus.capabilities.behavioral_modeling && (
                <><strong>Behavioral Modeling:</strong> {cityStatus.capabilities.behavioral_modeling}<br /></>
              )}
              <strong>Data Source:</strong> {cityStatus.capabilities.data_source}<br />
              <strong>Features:</strong> {cityStatus.capabilities.features?.join(', ')}<br />
              <strong>Visualisations:</strong> {cityStatus.capabilities.visualisation_types?.join(', ')}
            </>
          ) : (
            <>
              The visualisations use real OpenStreetMap data via OSMnx for authentic street network analysis.
              Routes computed using A* pathfinding with capacity constraints.
            </>
          )}
        </Text>
      </Alert>
    </Stack>
  );
};

export default CitySpecificVisualisation;
