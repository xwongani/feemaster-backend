#!/usr/bin/env python3
"""
Start script for Fee Master Backend using uv
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting Fee Master Backend with uv...")
    print("=" * 45)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    # Check if uv is installed
    if not check_uv_installed():
        print("❌ uv is not installed. Please install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   or visit: https://github.com/astral-sh/uv")
        sys.exit(1)
    
    print("✅ uv detected")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found")
        print("Please run setup_supabase.py first or create .env manually")
        sys.exit(1)
    
    # Check if virtual environment exists and dependencies are installed
    if not os.path.exists(".venv") and not os.path.exists("venv"):
        print("📦 Setting up virtual environment and installing dependencies...")
        try:
            # Create virtual environment
            subprocess.run(["uv", "venv", "--python", "3.8"], check=True)
            print("✅ Virtual environment created")
            
            # Install dependencies
            if os.path.exists("pyproject.toml"):
                subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
            else:
                subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during setup: {e}")
            sys.exit(1)
    else:
        # Check if key dependencies are available
        try:
            result = subprocess.run([
                "uv", "run", "python", "-c", 
                "import fastapi, uvicorn, supabase; print('Dependencies OK')"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print("📦 Installing/updating dependencies...")
                if os.path.exists("pyproject.toml"):
                    subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
                else:
                    subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], check=True)
                print("✅ Dependencies updated")
            else:
                print("✅ Dependencies verified")
                
        except subprocess.CalledProcessError:
            print("📦 Installing dependencies...")
            if os.path.exists("pyproject.toml"):
                subprocess.run(["uv", "pip", "install", "-e", "."])
            else:
                subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"])
    
    print("🌐 Starting FastAPI server with uv...")
    print("📡 API will be available at: http://localhost:8000")
    print("📚 Documentation at: http://localhost:8000/docs")
    print("🔄 Auto-reload enabled for development")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 45)
    
    try:
        # Start the server using uv run
        subprocess.run([
            "uv", "run", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
    except FileNotFoundError:
        print("❌ Error: Could not start server with uv")
        print("   Make sure uv is properly installed and in your PATH")

def check_uv_installed():
    """Check if uv is installed"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

if __name__ == "__main__":
    main() 