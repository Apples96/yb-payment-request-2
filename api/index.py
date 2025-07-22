"""
API Entry Point for Vercel Deployment

This module serves as the entry point for Vercel serverless functions.
It wraps the FastAPI application to work with Vercel's function format.
"""

import sys
import os

# Add the project root to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.main import app
    # Export the FastAPI app for Vercel
    # Vercel will automatically handle the ASGI interface
    handler = app
except Exception as e:
    # Create a simple error handler if import fails
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    handler = FastAPI()
    
    @handler.get("/")
    async def error_info():
        return JSONResponse({"error": f"Import failed: {str(e)}"})
    
    @handler.get("/api/{path:path}")
    async def api_error(path: str):
        return JSONResponse({"error": f"Import failed: {str(e)}"})
    
    @handler.post("/api/{path:path}")
    async def api_error_post(path: str):
        return JSONResponse({"error": f"Import failed: {str(e)}"})
    
    @handler.put("/api/{path:path}")
    async def api_error_put(path: str):
        return JSONResponse({"error": f"Import failed: {str(e)}"})
    
    @handler.delete("/api/{path:path}")
    async def api_error_delete(path: str):
        return JSONResponse({"error": f"Import failed: {str(e)}"})

# Also export as app for compatibility
app = handler 