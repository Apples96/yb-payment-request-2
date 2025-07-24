"""
API Entry Point for Vercel Deployment

This module serves as the entry point for Vercel serverless functions.
It wraps the FastAPI application to work with Vercel's function format.
"""

from app.main import app

# Export the FastAPI app for Vercel
# Vercel will automatically handle the ASGI interface
handler = app