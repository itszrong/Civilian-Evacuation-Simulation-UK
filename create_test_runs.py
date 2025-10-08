#!/usr/bin/env python3
"""
Script to create test runs with visualization data for testing the frontend.
"""

import asyncio
import requests
import time

async def create_test_runs():
    """Create test runs for different cities."""
    base_url = "http://localhost:8000"
    cities = ["westminster", "camden", "hackney"]
    
    print("🚀 Creating test runs with REAL evacuation simulation data...")
    
    for city in cities:
        print(f"\n📍 Creating REAL evacuation simulation for {city}...")
        print("   This may take a moment as we run actual evacuation algorithms...")
        
        try:
            # Create a complete run with REAL scenarios and visualization
            url = f"{base_url}/api/simulation/{city}/visualisation?create_complete=true"
            response = requests.get(url, timeout=120)  # Longer timeout for real simulation
            
            if response.status_code == 200:
                data = response.json()
                run_id = data.get('run_id')
                scenarios = data.get('scenarios', 0)
                print(f"✅ Created REAL run {run_id} for {city} with {scenarios} scenarios")
                print(f"   Status: {data.get('status')}")
                print(f"   Simulation Engine: {data.get('simulation_engine', 'unknown')}")
                print(f"   Has visualization: {data.get('has_visualization', False)}")
                print(f"   A* Routes: {len(data.get('astar_routes', []))}")
                print(f"   Random Walks: {data.get('random_walks', {}).get('num_walks', 0)}")
                print(f"   Interactive Map: {'Yes' if data.get('interactive_map_html') else 'No'}")
            else:
                print(f"❌ Failed to create run for {city}: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating run for {city}: {e}")
        
        # Small delay between requests
        time.sleep(1)
    
    print("\n🎉 REAL evacuation simulation runs created!")
    print("You can now check the Results tab to see the completed runs with:")
    print("  • Real evacuation scenarios with actual algorithms")
    print("  • Interactive Folium maps with OSMnx street networks")
    print("  • A* optimal evacuation routes")
    print("  • Random walk pedestrian behavior simulations")
    print("  • Real metrics from evacuation science calculations")

if __name__ == "__main__":
    asyncio.run(create_test_runs())
