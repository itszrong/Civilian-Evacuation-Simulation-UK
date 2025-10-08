#!/usr/bin/env python3
"""
Basic setup test for London Evacuation Planning Tool

This script tests that the core system components are properly configured
and can start up without errors.
"""

import sys
import os
import subprocess
import time
import requests
from pathlib import Path

def test_backend_imports():
    """Test that key backend dependencies can be imported."""
    print("🧪 Testing backend imports...")
    
    try:
        import fastapi
        import pydantic
        import uvicorn
        print("✅ FastAPI dependencies imported successfully")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    try:
        import networkx
        print("✅ NetworkX imported successfully")
    except ImportError as e:
        print(f"⚠️  NetworkX import failed: {e} (needed for simulation)")
    
    try:
        import structlog
        print("✅ Structured logging imported successfully")
    except ImportError as e:
        print(f"⚠️  Structlog import failed: {e}")
    
    return True

def test_frontend_setup():
    """Test that frontend dependencies are installed."""
    print("🧪 Testing frontend setup...")
    
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("❌ Frontend directory not found")
        return False
    
    node_modules = frontend_path / "node_modules"
    if not node_modules.exists():
        print("❌ Node modules not installed. Run: cd frontend && npm install")
        return False
    
    package_json = frontend_path / "package.json"
    if not package_json.exists():
        print("❌ package.json not found in frontend")
        return False
    
    print("✅ Frontend setup looks good")
    return True

def test_config_files():
    """Test that required configuration files exist."""
    print("🧪 Testing configuration files...")
    
    backend_path = Path("backend")
    required_files = [
        backend_path / "main.py",
        backend_path / "core" / "config.py",
        backend_path / "models" / "schemas.py",
        backend_path / "requirements.txt",
        Path("configs") / "sources.yml",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required configuration files found")
    return True

def test_backend_startup():
    """Test that the backend can start up."""
    print("🧪 Testing backend startup...")
    
    # Change to backend directory
    backend_path = Path("backend")
    if not backend_path.exists():
        print("❌ Backend directory not found")
        return False
    
    try:
        # Try to start the backend in the background
        env = os.environ.copy()
        env['PORT'] = '8001'  # Use different port for testing
        
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=backend_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Backend failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
        
        # Try to make a request to health endpoint
        try:
            response = requests.get("http://localhost:8001/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend startup successful")
                success = True
            else:
                print(f"❌ Health check failed with status {response.status_code}")
                success = False
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to backend: {e}")
            success = False
        
        # Clean up - terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return success
        
    except Exception as e:
        print(f"❌ Backend startup test failed: {e}")
        return False

def main():
    """Run all basic setup tests."""
    print("🌍 London Evacuation Planning Tool - Basic Setup Test")
    print("=" * 60)
    
    tests = [
        ("Backend Imports", test_backend_imports),
        ("Frontend Setup", test_frontend_setup),
        ("Config Files", test_config_files),
        ("Backend Startup", test_backend_startup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🧪 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! The system is ready to use.")
        print("\n🚀 Next steps:")
        print("  1. Configure API keys in .env file")
        print("  2. Run 'make dev' to start both backend and frontend")
        print("  3. Visit http://localhost:3000 to use the application")
        return True
    else:
        print("❌ Some tests failed. Please check the setup.")
        print("\n🔧 Troubleshooting:")
        print("  1. Run 'make setup' to install dependencies")
        print("  2. Check that all required files are present")
        print("  3. Verify Python and Node.js are properly installed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
