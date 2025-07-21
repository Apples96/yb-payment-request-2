"""
API Entry Point for Vercel Deployment

This module serves as the entry point for Vercel serverless functions.
It imports and exposes the FastAPI application from the main app module.

Usage:
    - Used by Vercel to serve the application in a serverless environment
    - Routes all requests to the main FastAPI app instance
"""

from app.main import app

# This is the entry point for Vercel serverless functions
# The app is imported from the main FastAPI application 