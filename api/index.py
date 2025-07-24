"""
API Entry Point for Vercel Deployment

This module serves as the entry point for Vercel serverless functions.
It wraps the FastAPI application to work with Vercel's function format.
"""

from .main import app

# Export the FastAPI app for Vercel
# For ASGI applications (FastAPI), Vercel expects the app to be exported as 'app'
# This allows Vercel to handle the ASGI interface automatically