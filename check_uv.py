#!/usr/bin/env python3
"""
Check uv setup for Fee Master Backend
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🔍 Checking uv setup for Fee Master Backend...")
    print("=" * 50)
    
    # Check if uv is installed
    if check_uv_installed():
        print("✅ uv is installed")
        
        # Get uv version
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        print(f"   Version: {result.stdout.strip()}")
    else:
        print("❌ uv is not installed")
        print("   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Not in the backend directory")
        print("   Please run this script from the backend directory")
        return False
    
    print("✅ In the correct directory")
    
    # Check for pyproject.toml
    if os.path.exists("pyproject.toml"):
        print("✅ pyproject.toml found")
    else:
        print("⚠️  pyproject.toml not found (will use requirements.txt)")
    
    # Check for requirements.txt
    if os.path.exists("requirements.txt"):
        print("✅ requirements.txt found")
    else:
        print("❌ requirements.txt not found")
        return False
    
    # Check for .env file
    if os.path.exists(".env"):
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found (run setup_supabase.py)")
    
    # Check virtual environment
    if os.path.exists(".venv") or os.path.exists("venv"):
        print("✅ Virtual environment exists")
        
        # Test if dependencies can be imported
        try:
            result = subprocess.run([
                "uv", "run", "python", "-c", 
                "import fastapi, uvicorn, supabase; print('All core dependencies available')"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Core dependencies are available")
            else:
                print("⚠️  Core dependencies need to be installed")
                print("   Run: uv pip install -e . or uv pip install -r requirements.txt")
        except Exception as e:
            print(f"⚠️  Could not check dependencies: {e}")
    else:
        print("⚠️  Virtual environment not found")
        print("   Run: uv venv to create one")
    
    print("\n🚀 Quick start commands:")
    print("   Setup: uv run setup_supabase.py")
    print("   Start: uv run start.py")
    print("   Dependencies: uv pip install -e .")
    print("   Server: uv run uvicorn app.main:app --reload")
    
    return True

def check_uv_installed():
    """Check if uv is installed"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
 