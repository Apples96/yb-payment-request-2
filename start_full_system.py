#!/usr/bin/env python3
"""
Start both backend and frontend together
"""
import subprocess
import time
import os
import signal
import sys
from pathlib import Path

def start_full_system():
    """Start both FastAPI backend and frontend server"""
    
    backend_process = None
    frontend_process = None
    
    try:
        print("🚀 Starting Workflow Automation System...")
        print("=" * 50)
        
        # Start FastAPI backend
        print("📡 Starting FastAPI backend on http://localhost:8000...")
        backend_process = subprocess.Popen([
            sys.executable, "-m", "app.main"
        ], cwd=Path(__file__).parent)
        
        # Wait a moment for backend to start
        time.sleep(3)
        
        # Start frontend server
        print("🌐 Starting frontend server on http://localhost:3000...")
        frontend_process = subprocess.Popen([
            sys.executable, "start_frontend.py"
        ], cwd=Path(__file__).parent)
        
        print("\n✅ Both servers are running!")
        print("🔗 Open http://localhost:3000 in your browser")
        print("📡 API docs available at http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop both servers")
        
        # Wait for interrupt
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping servers...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        # Clean up processes
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        
        print("👋 All servers stopped")

if __name__ == "__main__":
    start_full_system()