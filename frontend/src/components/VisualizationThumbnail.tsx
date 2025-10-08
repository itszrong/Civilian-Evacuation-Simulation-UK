/**
 * Visualization Thumbnail Component
 * Displays a small preview of the evacuation simulation visualization
 */

import React, { useState, useEffect, useRef } from 'react';
import { API_CONFIG, API_ENDPOINTS } from '../config/api.js';

interface VisualizationThumbnailProps {
  runId: string;
  city: string;
  className?: string;
  style?: React.CSSProperties;
}

const VisualizationThumbnail: React.FC<VisualizationThumbnailProps> = ({
  runId,
  city,
  className = '',
  style = {}
}) => {
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVisualization = async () => {
      try {
        setLoading(true);
        setError(null);

        // Use the same API pattern as the existing visualization components
        const visualisationUrl = `${API_CONFIG.baseUrl}${API_ENDPOINTS.simulation.visualisation(city)}`;
        console.log(`🖼️ Fetching thumbnail HTML from: ${visualisationUrl}`);
        
        const response = await fetch(visualisationUrl);
        
        if (response.ok) {
          const data = await response.json();
          console.log('📊 Thumbnail data received:', {
            hasInteractiveMapHtml: !!data.interactive_map_html,
            simulationEngine: data.simulation_engine,
            dataKeys: Object.keys(data)
          });
          
          // Look for the HTML content in the response
          if (data.interactive_map_html) {
            console.log('🔍 Original HTML sample:', data.interactive_map_html.substring(0, 500));
            console.log('🔍 HTML contains controls:', data.interactive_map_html.includes('leaflet-control'));
            console.log('🔍 HTML contains zoom:', data.interactive_map_html.includes('zoom'));
            console.log('🔍 HTML contains attribution:', data.interactive_map_html.includes('attribution'));
            setHtmlContent(data.interactive_map_html);
            return;
          }
          
          // Fallback: try to get from run data if available
          try {
            const runResponse = await fetch(`${API_CONFIG.baseUrl}/api/runs/${runId}`);
            if (runResponse.ok) {
              const runData = await runResponse.json();
              
              // Look for HTML content in scenarios
              if (runData.scenarios && runData.scenarios.length > 0) {
                for (const scenario of runData.scenarios) {
                  if (scenario.simulation_data && scenario.simulation_data.interactive_map_html) {
                    setHtmlContent(scenario.simulation_data.interactive_map_html);
                    return;
                  }
                }
              }
            }
          } catch (runError) {
            console.warn('Run data fallback failed:', runError);
          }
          
          setError('No visualization HTML available');
        } else {
          console.warn('Visualization API failed:', response.status, response.statusText);
          setError('Failed to load visualization');
        }
      } catch (err) {
        console.error('Error fetching visualization:', err);
        setError('Failed to load visualization');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately when component mounts (no lazy loading)
    if (runId && city && !htmlContent) {
      fetchVisualization();
    }
  }, [runId, city, htmlContent]);

  const defaultStyle: React.CSSProperties = {
    width: '200px',
    height: '150px',
    objectFit: 'cover',
    borderRadius: '4px',
    border: '1px solid #b1b4b6',
    backgroundColor: '#f3f2f1',
    ...style
  };

  if (loading) {
    return (
      <div 
        className={`govuk-!-display-flex govuk-!-align-items-center govuk-!-justify-content-center ${className}`}
        style={{
          ...defaultStyle,
          backgroundColor: '#f3f2f1',
          color: '#626a6e'
        }}
      >
        <div className="govuk-!-text-align-centre">
          <div style={{ fontSize: '12px' }}>Loading...</div>
        </div>
      </div>
    );
  }

  if (error || !htmlContent) {
    return (
      <div 
        className={`govuk-!-display-flex govuk-!-align-items-center govuk-!-justify-content-center ${className}`}
        style={{
          ...defaultStyle,
          backgroundColor: '#f3f2f1',
          color: '#626a6e'
        }}
      >
        <div className="govuk-!-text-align-centre">
          <div style={{ fontSize: '12px', marginBottom: '4px' }}>📊</div>
          <div style={{ fontSize: '10px' }}>No preview</div>
        </div>
      </div>
    );
  }

  // Aggressively scrub ALL Leaflet content while preserving map data
  const cleanHtmlContent = htmlContent ? (() => {
    let cleaned = htmlContent;
    
    console.log('🧹 Starting aggressive Leaflet scrubbing...');
    
    // Remove ALL elements with "leaflet" in class names or IDs
    cleaned = cleaned.replace(/<[^>]*class="[^"]*leaflet[^"]*"[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    cleaned = cleaned.replace(/<[^>]*id="[^"]*leaflet[^"]*"[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    
    // Remove any script tags that mention leaflet
    cleaned = cleaned.replace(/<script[^>]*>[\s\S]*?leaflet[\s\S]*?<\/script>/gi, '');
    
    // Remove any CSS that mentions leaflet
    cleaned = cleaned.replace(/<style[^>]*>[\s\S]*?leaflet[\s\S]*?<\/style>/gi, '');
    
    // Remove any links to leaflet CSS
    cleaned = cleaned.replace(/<link[^>]*leaflet[^>]*>/gi, '');
    
    // Remove attribution text completely
    cleaned = cleaned.replace(/Leaflet.*?contributors/gi, '');
    cleaned = cleaned.replace(/OpenStreetMap.*?contributors/gi, '');
    cleaned = cleaned.replace(/©.*?OpenStreetMap/gi, '');
    
    // Remove any remaining control-related elements
    cleaned = cleaned.replace(/<[^>]*class="[^"]*control[^"]*"[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    cleaned = cleaned.replace(/<[^>]*class="[^"]*zoom[^"]*"[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    cleaned = cleaned.replace(/<[^>]*class="[^"]*attribution[^"]*"[^>]*>[\s\S]*?<\/[^>]*>/gi, '');
    
    // Add enhanced CSS and JavaScript for aggressive control removal
    cleaned = cleaned.replace('</head>', `
      <style>
        body { 
          margin: 0 !important; 
          padding: 0 !important; 
          overflow: hidden !important;
          background: #f8f9fa !important;
        }
        
        /* Aggressively hide ALL Leaflet controls with maximum specificity */
        .leaflet-control-container,
        .leaflet-control-zoom,
        .leaflet-control-layers,
        .leaflet-control-attribution,
        .leaflet-bar,
        .leaflet-control,
        [class*="leaflet-control"],
        [class*="leaflet-bar"],
        [class*="leaflet-zoom"],
        [class*="leaflet-attribution"],
        [class*="leaflet-layer"],
        [id*="leaflet-control"],
        [id*="leaflet-zoom"],
        [id*="leaflet-attribution"],
        [id*="leaflet-layer"],
        [class*="control"],
        [class*="zoom"],
        [class*="attribution"],
        [class*="layer"] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          width: 0 !important;
          height: 0 !important;
          pointer-events: none !important;
          position: absolute !important;
          left: -9999px !important;
        }
        
        /* Ensure map container fills space */
        div[id*="map"], .folium-map {
          width: 100% !important;
          height: 100% !important;
          border: none !important;
        }
        
        /* Clean up any remaining text */
        *:before, *:after {
          content: none !important;
        }
        
        /* Hide any anchor tags that might be controls */
        .leaflet-control-container a,
        [class*="leaflet"] a,
        .leaflet-bar a {
          display: none !important;
          visibility: hidden !important;
        }
      </style>
      <script>
        // Aggressive control removal after map loads
        (function() {
          function removeControls() {
            // Remove all control containers
            const controlSelectors = [
              '.leaflet-control-container',
              '.leaflet-control-zoom',
              '.leaflet-control-layers',
              '.leaflet-control-attribution',
              '.leaflet-bar',
              '.leaflet-control',
              '[class*="leaflet-control"]',
              '[class*="leaflet-bar"]',
              '[class*="leaflet-zoom"]',
              '[class*="leaflet-attribution"]',
              '[class*="leaflet-layer"]'
            ];
            
            controlSelectors.forEach(selector => {
              try {
                document.querySelectorAll(selector).forEach(el => {
                  if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                  }
                });
              } catch (e) {
                console.log('Failed to remove:', selector, e);
              }
            });
            
            // Remove any elements with control-related classes
            document.querySelectorAll('[class]').forEach(el => {
              const className = el.className.toString().toLowerCase();
              if (className.includes('control') || 
                  className.includes('zoom') || 
                  className.includes('layer') || 
                  className.includes('attribution')) {
                if (el.parentNode) {
                  el.parentNode.removeChild(el);
                }
              }
            });
          }
          
          // Run immediately
          removeControls();
          
          // Run after DOM is ready
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', removeControls);
          }
          
          // Run after a short delay to catch dynamically added controls
          setTimeout(removeControls, 100);
          setTimeout(removeControls, 500);
          setTimeout(removeControls, 1000);
          
          // Use MutationObserver to catch any controls added later
          const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
              mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1) { // Element node
                  const el = node;
                  const className = el.className ? el.className.toString().toLowerCase() : '';
                  if (className.includes('leaflet-control') || 
                      className.includes('leaflet-zoom') || 
                      className.includes('leaflet-layer') || 
                      className.includes('leaflet-bar') ||
                      className.includes('control') ||
                      className.includes('zoom') ||
                      className.includes('attribution')) {
                    if (el.parentNode) {
                      el.parentNode.removeChild(el);
                    }
                  }
                }
              });
            });
          });
          
          // Start observing the document body
          if (document.body) {
            observer.observe(document.body, {
              childList: true,
              subtree: true
            });
          } else {
            document.addEventListener('DOMContentLoaded', () => {
              observer.observe(document.body, {
                childList: true,
                subtree: true
              });
            });
          }
        })();
      </script>
      </head>`);
    
    console.log('🧹 After scrubbing - HTML length:', cleaned.length);
    console.log('🧹 Contains "leaflet":', cleaned.toLowerCase().includes('leaflet'));
    console.log('🧹 Contains "control":', cleaned.toLowerCase().includes('control'));
    console.log('🧹 Contains "zoom":', cleaned.toLowerCase().includes('zoom'));
    
    return cleaned;
  })() : htmlContent;

  // Try to create a simple static visualization instead of using the full Leaflet HTML
  const createSimpleVisualization = () => {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { 
            margin: 0; 
            padding: 0; 
            background: #f0f8ff; 
            font-family: Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
          }
          .simple-map {
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #e8f4f8 25%, transparent 25%), 
                        linear-gradient(-45deg, #e8f4f8 25%, transparent 25%), 
                        linear-gradient(45deg, transparent 75%, #e8f4f8 75%), 
                        linear-gradient(-45deg, transparent 75%, #e8f4f8 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .city-label {
            background: rgba(29, 112, 184, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
          }
          .route-lines {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
          }
          .route {
            stroke: #d73027;
            stroke-width: 2;
            fill: none;
            opacity: 0.7;
          }
        </style>
      </head>
      <body>
        <div class="simple-map">
          <svg class="route-lines" viewBox="0 0 200 150">
            <!-- Simple evacuation route visualization -->
            <path class="route" d="M20,75 Q60,30 100,75 Q140,120 180,75" />
            <path class="route" d="M20,50 Q100,20 180,50" />
            <path class="route" d="M20,100 Q100,130 180,100" />
            <circle cx="20" cy="75" r="3" fill="#d73027" />
            <circle cx="180" cy="75" r="4" fill="#2166ac" />
          </svg>
          <div class="city-label">${city.charAt(0).toUpperCase() + city.slice(1)} Evacuation Routes</div>
        </div>
      </body>
      </html>
    `;
  };

  const finalContent = htmlContent ? cleanHtmlContent : createSimpleVisualization();
  console.log('🎨 Using visualization type:', htmlContent ? 'Leaflet (cleaned)' : 'Simple SVG');

  return (
    <iframe
      srcDoc={finalContent}
      className={className}
      style={{
        ...defaultStyle,
        border: '1px solid #b1b4b6',
        borderRadius: '4px'
      }}
      title={`${city} evacuation visualization`}
      sandbox="allow-scripts allow-same-origin"
      onError={() => setError('Visualization failed to load')}
    />
  );
};

export default VisualizationThumbnail;
