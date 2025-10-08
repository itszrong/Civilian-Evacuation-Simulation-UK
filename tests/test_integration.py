#!/usr/bin/env python3
"""
Integration test script for Civilian Evacuation Planning Tool
Tests the frontend-backend API integration
"""

import requests
import json
import time

# Test configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def test_backend_health():
    """Test backend health endpoint"""
    print("🏥 Testing backend health...")
    try:
        response = requests.get(f"{BACKEND_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend healthy: {data['service']} v{data['version']}")
            return True
        else:
            print(f"❌ Backend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_cities_endpoint():
    """Test simulation cities endpoint"""
    print("\n🏙️ Testing cities endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/simulation/cities")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cities available: {data['cities']}")
            print(f"   Default city: {data['default']}")
            return True
        else:
            print(f"❌ Cities endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cities endpoint error: {e}")
        return False

def test_evacuation_planning():
    """Test evacuation planning workflow"""
    print("\n🚨 Testing evacuation planning workflow...")
    
    # Prepare test data matching frontend format
    test_data = {
        "intent": {
            "objective": "minimise_clearance_time_and_improve_fairness",
            "city": "london",
            "constraints": {
                "max_scenarios": 2,  # Small number for testing
                "compute_budget_minutes": 1,  # Quick test
                "must_protect_pois": ["StThomasHospital", "KingsCollegeHospital"]
            },
            "preferences": {
                "clearance_weight": 0.5,
                "fairness_weight": 0.35,
                "robustness_weight": 0.15
            },
            "hypotheses": ["Westminster cordon 2h", "Two Thames bridges closed"],
            "freshness_days": 7,
            "tiers": ["gov_primary"]
        },
        "city": "london"
    }
    
    try:
        print("📡 Starting evacuation planning run...")
        response = requests.post(
            f"{BACKEND_URL}/api/runs",
            json=test_data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Run started successfully")
            print("📊 Streaming events:")
            
            # Parse SSE stream
            event_count = 0
            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                        print(f"   🎯 Event: {event_type}")
                        event_count += 1
                    elif line.startswith("data: "):
                        try:
                            data = json.loads(line[6:].strip())
                            if 'run_id' in data:
                                print(f"   📋 Run ID: {data['run_id']}")
                            if 'status' in data:
                                print(f"   📈 Status: {data['status']}")
                            if 'num_scenarios' in data:
                                print(f"   🎲 Scenarios: {data['num_scenarios']}")
                        except json.JSONDecodeError:
                            pass
                
                # Limit output for testing
                if event_count >= 5:
                    break
            
            print(f"✅ Processed {event_count} events")
            return True
        else:
            print(f"❌ Planning run failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Raw error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Planning run error: {e}")
        return False

def test_frontend_health():
    """Test frontend health"""
    print("\n🌐 Testing frontend health...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            if "Civilian Evacuation Planning Tool" in response.text:
                print("✅ Frontend healthy and serving GOV.UK interface")
                return True
            else:
                print("⚠️ Frontend serving but content unexpected")
                return False
        else:
            print(f"❌ Frontend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend connection failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🔬 Civilian Evacuation Planning Tool - Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Cities Endpoint", test_cities_endpoint), 
        ("Evacuation Planning", test_evacuation_planning),
        ("Frontend Health", test_frontend_health)
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All systems operational! Ready for government deployment.")
    else:
        print("⚠️ Some issues detected. Check the logs above.")
    
    return passed == len(tests)

if __name__ == "__main__":
    main()
