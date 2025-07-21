#!/usr/bin/env python3
"""
Frontend Server Startup Script

Simple HTTP server to serve the frontend files on localhost:3000
for local development and testing.

Usage:
    python start_frontend.py
    
    Then open http://localhost:3000 for the frontend
"""
import http.server
import socketserver
import os
from pathlib import Path

def start_frontend_server():
    """Start a simple HTTP server to serve frontend files"""
    
    # Change to frontend directory
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    PORT = 3000
    
    # Create server
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌐 Frontend server running on http://localhost:{PORT}")
        print(f"📁 Serving files from: {frontend_dir}")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Frontend server stopped")

if __name__ == "__main__":
    start_frontend_server() 