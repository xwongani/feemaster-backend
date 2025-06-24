#!/usr/bin/env python3
"""
Start script for Fee Master Backend
Supports both development and production modes
"""

import os
import sys
import subprocess
from pathlib import Path

def check_uv_installed():
    """Check if uv is installed"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    print("🚀 Starting Fee Master Backend...")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    # Check environment
    is_production = os.getenv("RENDER", "false").lower() == "true" or os.getenv("PRODUCTION", "false").lower() == "true"
    
    if is_production:
        print("🏭 Production mode detected")
        # In production (Render), use gunicorn
        try:
            import gunicorn
            print("✅ Gunicorn available")
            
            # Get port from environment (Render sets PORT)
            port = os.getenv("PORT", "8000")
            
            print(f"🌐 Starting production server on port {port}...")
            subprocess.run([
                "gunicorn", 
                "app.main:app", 
                "--worker-class", "uvicorn.workers.UvicornWorker",
                "--bind", f"0.0.0.0:{port}",
                "--workers", "1",
                "--timeout", "120"
            ])
        except ImportError:
            print("❌ Gunicorn not available, falling back to uvicorn")
            subprocess.run([
                "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", os.getenv("PORT", "8000")
            ])
    else:
        print("🔧 Development mode")
        
        # Check if uv is available for development
        if check_uv_installed():
            print("✅ uv detected - using uv for development")
            print("🌐 Starting development server with uv...")
            print("📡 API will be available at: http://localhost:8000")
            print("📚 Documentation at: http://localhost:8000/docs")
            print("🔄 Auto-reload enabled for development")
            print()
            print("Press Ctrl+C to stop the server")
            print("-" * 45)
            
            try:
                subprocess.run([
                    "uv", "run", "uvicorn", 
                    "app.main:app", 
                    "--reload", 
                    "--host", "0.0.0.0", 
                    "--port", "8000"
                ])
            except KeyboardInterrupt:
                print("\n👋 Server stopped. Goodbye!")
        else:
            print("⚠️  uv not detected - using standard Python")
            print("🌐 Starting development server...")
            print("📡 API will be available at: http://localhost:8000")
            print("📚 Documentation at: http://localhost:8000/docs")
            print("🔄 Auto-reload enabled for development")
            print()
            print("Press Ctrl+C to stop the server")
            print("-" * 45)
            
            try:
                subprocess.run([
                    "uvicorn", 
                    "app.main:app", 
                    "--reload", 
                    "--host", "0.0.0.0", 
                    "--port", "8000"
                ])
            except KeyboardInterrupt:
                print("\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    main() 