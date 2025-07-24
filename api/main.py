"""
Main FastAPI Application for Workflow Automation System

This is the core FastAPI application that provides REST API endpoints for:
- Creating workflows from natural language descriptions
- Executing workflows with user input and file attachments
- Managing file uploads and processing
- Handling workflow feedback and regeneration

Key Features:
    - AI-powered workflow generation using Anthropic Claude
    - Document processing via LightOn Paradigm API
    - File upload and management
    - Real-time workflow execution with timeout handling
    - Comprehensive CORS support for web frontends
    - Error handling and logging

API Endpoints:
    - POST /workflows - Create new workflow
    - GET /workflows/{id} - Get workflow details
    - POST /workflows/{id}/execute - Execute workflow
    - POST /files/upload - Upload files for processing
    - File management endpoints for questioning and deletion
    
The application supports cross-domain deployment with multiple frontend origins
and provides comprehensive API documentation via FastAPI's automatic OpenAPI integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from .config import settings
from .models import (
    WorkflowCreateRequest,
    WorkflowExecuteRequest,
    WorkflowResponse,
    WorkflowExecutionResponse,
    ErrorResponse,
    FileUploadResponse,
    FileInfoResponse,
    FileQuestionRequest,
    FileQuestionResponse,
    WorkflowWithFilesRequest,
    WorkflowFeedbackRequest
)
from .workflow.generator import workflow_generator
from .workflow.executor import workflow_executor
from .workflow.models import Workflow, WorkflowExecution, ExecutionStatus
from .api_clients import paradigm_client  # Updated import

# Configure logging based on debug settings
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

# API key validation helpers
def validate_anthropic_api_key():
    """
    Validate that Anthropic API key is available.
    
    Returns:
        bool: True if API key is available
        
    Raises:
        HTTPException: 503 if API key is missing
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable."
        )
    return True

def validate_lighton_api_key():
    """
    Validate that LightOn API key is available.
    
    Returns:
        bool: True if API key is available
        
    Raises:
        HTTPException: 503 if API key is missing
    """
    if not settings.lighton_api_key:
        raise HTTPException(
            status_code=503,
            detail="LightOn API key not configured. Please set LIGHTON_API_KEY environment variable."
        )
    return True

# Create FastAPI app with comprehensive metadata
app = FastAPI(
    title="Workflow Automation API",
    description="API for creating and executing automated workflows using AI",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware for cross-domain frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://127.0.0.1:3000",
        "https://scaffold-ai-test2.vercel.app",  # Production frontend
        "https://scaffold-ai-test2-milo-rignells-projects.vercel.app",  # Your current deployment
        "https://scaffold-ai-test2-fi4dvy1xl-milo-rignells-projects.vercel.app",
        "https://scaffold-ai-test2-tawny.vercel.app",  # Your other deployment
        "https://scaffold-ai-test2-git-main-milo-rignells-projects.vercel.app/",
        "https://*.vercel.app",  # All Vercel deployments
        "https://*.netlify.app",  # Netlify deployments
        "https://*.github.io",   # GitHub Pages
        "https://*.surge.sh",    # Surge deployments
        "https://*.firebaseapp.com"  # Firebase hosting
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """
    Health check endpoint.
    
    Provides basic service information and status for monitoring.
    Used by deployment platforms and monitoring systems to verify service health.
    
    Returns:
        dict: Service metadata including version, status, and timestamp
    """
    return {
        "message": "Workflow Automation API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/workflows", response_model=WorkflowResponse, tags=["Workflows"])
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a new workflow from a natural language description.
    
    This endpoint uses AI to generate executable Python code from a natural
    language workflow description. The generated code integrates with both
    Anthropic and LightOn Paradigm APIs for document processing and analysis.
    
    Args:
        request: Workflow creation request containing description, optional name, and context
        
    Returns:
        WorkflowResponse: Complete workflow details including generated code
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if workflow generation fails
        
    Example:
        POST /workflows
        {
            \"description\": \"Search documents about AI, then analyze findings\",
            \"name\": \"AI Research Workflow\"
        }
    """
    # Validate required API keys
    validate_anthropic_api_key()
    
    try:
        logger.info(f"Creating workflow: {request.description[:100]}...")
        
        # Generate the workflow
        workflow = await workflow_generator.generate_workflow(
            description=request.description,
            name=request.name,
            context=request.context
        )
        
        # Store the workflow in the executor
        workflow_executor.store_workflow(workflow)
        
        logger.info(f"Workflow created successfully: {workflow.id}")
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            generated_code=workflow.generated_code,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            error=workflow.error
        )
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )

@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["Workflows"])
async def get_workflow(workflow_id: str):
    """
    Retrieve details of a specific workflow by ID.
    
    Returns complete workflow information including generated code,
    current status, and metadata. Used to check workflow status
    and retrieve generated code for inspection.
    
    Args:
        workflow_id: Unique identifier of the workflow to retrieve
        
    Returns:
        WorkflowResponse: Complete workflow details
        
    Raises:
        HTTPException: 404 if workflow not found, 500 for other errors
    """
    try:
        workflow = workflow_executor.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            generated_code=workflow.generated_code,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            error=workflow.error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow: {str(e)}"
        )

@app.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse, tags=["Execution"])
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """
    Execute a workflow with user input and optional file attachments.
    
    Runs the generated workflow code with the provided user input.
    Supports file attachments that can be processed within the workflow.
    Execution is performed in a secure, isolated environment with timeout protection.
    
    Args:
        workflow_id: ID of the workflow to execute
        request: Execution request with user input and optional file IDs
        
    Returns:
        WorkflowExecutionResponse: Execution results with status and timing
        
    Raises:
        HTTPException: 400 for validation errors, 500 for execution failures
        
    Note:
        Execution timeout is configured via settings.max_execution_time (default: 5 minutes)
    """
    try:
        logger.info(f"Executing workflow {workflow_id} with input: {request.user_input[:100]}...")
        
        # Execute the workflow
        execution = await workflow_executor.execute_workflow(workflow_id, request.user_input, request.attached_file_ids)
        
        logger.info(f"Workflow execution completed: {execution.id} (status: {execution.status})")
        
        return WorkflowExecutionResponse(
            workflow_id=execution.workflow_id,
            execution_id=execution.id,
            result=execution.result,
            status=execution.status.value,
            execution_time=execution.execution_time,
            error=execution.error,
            created_at=execution.created_at
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute workflow: {str(e)}"
        )

@app.get("/workflows/{workflow_id}/executions/{execution_id}", response_model=WorkflowExecutionResponse, tags=["Execution"])
async def get_execution(workflow_id: str, execution_id: str):
    """
    Retrieve details of a specific workflow execution.
    
    Returns execution results, status, timing information, and any errors
    that occurred during execution. Used for monitoring and debugging
    workflow executions.
    
    Args:
        workflow_id: ID of the parent workflow
        execution_id: Unique identifier of the execution to retrieve
        
    Returns:
        WorkflowExecutionResponse: Complete execution details
        
    Raises:
        HTTPException: 404 if execution not found, 400 if execution doesn't belong to workflow
    """
    try:
        execution = workflow_executor.get_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {execution_id} not found"
            )
        
        if execution.workflow_id != workflow_id:
            raise HTTPException(
                status_code=400,
                detail=f"Execution {execution_id} does not belong to workflow {workflow_id}"
            )
        
        return WorkflowExecutionResponse(
            workflow_id=execution.workflow_id,
            execution_id=execution.id,
            result=execution.result,
            status=execution.status.value,
            execution_time=execution.execution_time,
            error=execution.error,
            created_at=execution.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution: {str(e)}"
        )

# File upload and management endpoints

@app.post("/files/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_file(
    file: UploadFile = File(...),
    collection_type: str = Form("private"),
    workspace_id: Optional[int] = Form(None)
):
    """
    Upload a file to Paradigm for document processing and analysis.
    
    Files are automatically processed, indexed, and made available for use
    in workflows. Supports various document formats and collection types
    for organizing files within different scopes.
    
    Args:
        file: The file to upload (multipart/form-data)
        collection_type: Collection scope - 'private', 'company', or 'workspace'
        workspace_id: Required if collection_type is 'workspace'
        
    Returns:
        FileUploadResponse: File metadata including ID, size, and processing status
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if upload fails
        
    Note:
        Files are processed asynchronously and may take time to become fully searchable
    """
    # Validate required API keys
    validate_lighton_api_key()
    
    try:
        logger.info(f"Uploading file: {file.filename}")
        
        # Read file content
        file_content = await file.read()
        
        # Upload to Paradigm
        result = await paradigm_client.upload_file(
            file_content=file_content,
            filename=file.filename,
            collection_type=collection_type,
            workspace_id=workspace_id
        )
        
        logger.info(f"File uploaded successfully: {result.get('id')}")
        
        return FileUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@app.get("/files/{file_id}", response_model=FileInfoResponse, tags=["Files"])
async def get_file_info(file_id: int, include_content: bool = False):
    """
    Retrieve metadata and optionally content of an uploaded file.
    
    Provides file information including processing status, size, and creation time.
    Can optionally include the full file content for inspection.
    
    Args:
        file_id: Unique identifier of the file
        include_content: Whether to include file content in response
        
    Returns:
        FileInfoResponse: File metadata and optionally content
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if retrieval fails
    """
    # Validate required API keys
    validate_lighton_api_key()
    
    try:
        result = await paradigm_client.get_file_info(file_id, include_content)
        return FileInfoResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to get file info for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file info: {str(e)}"
        )

@app.post("/files/{file_id}/ask", response_model=FileQuestionResponse, tags=["Files"])
async def ask_question_about_file(file_id: int, request: FileQuestionRequest):
    """
    Ask a natural language question about a specific uploaded file.
    
    Uses AI to analyze the file content and provide answers to user questions.
    Returns both the answer and relevant document chunks for transparency.
    
    Args:
        file_id: ID of the file to question
        request: Question request containing the natural language query
        
    Returns:
        FileQuestionResponse: AI-generated answer with supporting document chunks
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if question processing fails
    """
    # Validate required API keys
    validate_lighton_api_key()
    
    try:
        result = await paradigm_client.ask_question_about_file(file_id, request.question)
        return FileQuestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to ask question about file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ask question: {str(e)}"
        )

@app.delete("/files/{file_id}", tags=["Files"])
async def delete_file(file_id: int):
    """
    Delete an uploaded file from the system.
    
    Permanently removes the file and all associated metadata from Paradigm.
    The file will no longer be available for workflows or questioning.
    
    Args:
        file_id: ID of the file to delete
        
    Returns:
        dict: Success status and confirmation message
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if deletion fails
        
    Warning:
        This operation is irreversible
    """
    # Validate required API keys
    validate_lighton_api_key()
    
    try:
        success = await paradigm_client.delete_file(file_id)
        return {"success": success, "message": f"File {file_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )

@app.post("/workflows-with-files", response_model=WorkflowResponse, tags=["Workflows"])
async def create_workflow_with_files(request: WorkflowWithFilesRequest):
    """
    Create a workflow that has access to specific uploaded files.
    
    Generates workflow code that can process and analyze the specified
    uploaded files. The file IDs are embedded in the workflow context
    so the generated code can reference them directly.
    
    Args:
        request: Workflow creation request with file IDs to attach
        
    Returns:
        WorkflowResponse: Complete workflow details with file access capabilities
        
    Raises:
        HTTPException: 503 if API keys are missing, 500 if workflow generation fails
        
    Note:
        Generated workflow will have access to global 'attached_file_ids' variable
    """
    # Validate required API keys
    validate_anthropic_api_key()
    
    try:
        logger.info(f"Creating workflow with files: {request.uploaded_file_ids}")
        
        # Add file IDs to context
        context = request.context or {}
        if request.uploaded_file_ids:
            context["uploaded_file_ids"] = request.uploaded_file_ids
            context["use_uploaded_files"] = True
        
        # Generate the workflow
        workflow = await workflow_generator.generate_workflow(
            description=request.description,
            name=request.name,
            context=context
        )
        
        # Store the workflow in the executor
        workflow_executor.store_workflow(workflow)
        
        logger.info(f"Workflow with files created successfully: {workflow.id}")
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            generated_code=workflow.generated_code,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            error=workflow.error
        )
        
    except Exception as e:
        logger.error(f"Failed to create workflow with files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow with files: {str(e)}"
        )

@app.post("/workflows/{workflow_id}/regenerate-with-feedback", response_model=WorkflowResponse, tags=["Workflows"])
async def regenerate_workflow_with_feedback(workflow_id: str, request: WorkflowFeedbackRequest = Body(...)):
    """
    Improve workflow code based on execution results and user feedback.
    
    Takes the original workflow description, execution results, and user feedback
    to generate improved code that addresses identified issues. Uses AI to
    understand what went wrong and how to fix it.
    
    Args:
        workflow_id: ID of the workflow to improve
        request: Feedback request with execution results and improvement suggestions
        
    Returns:
        WorkflowResponse: Updated workflow with improved generated code
        
    Raises:
        HTTPException: 404 if workflow not found, 503 if API keys are missing, 500 if regeneration fails
        
    Example Use Case:
        - User executes workflow and gets unexpected results
        - User provides feedback: "The search query was too broad, be more specific"
        - System regenerates code with more targeted search logic
    """
    # Validate required API keys
    validate_anthropic_api_key()
    
    workflow = workflow_executor.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        improved_code = await workflow_generator.regenerate_with_feedback(
            workflow=workflow,
            execution_result=request.execution_result,
            user_feedback=request.user_feedback
        )
        workflow.generated_code = improved_code
        workflow.update_status("ready")
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            generated_code=workflow.generated_code,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            error=workflow.error
        )
    except Exception as e:
        workflow.update_status("failed", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to regenerate workflow: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    
    Catches all unhandled exceptions and returns a consistent error response.
    In debug mode, includes detailed error information for troubleshooting.
    In production mode, returns generic error messages to avoid information leakage.
    
    Args:
        request: The HTTP request that caused the exception
        exc: The unhandled exception
        
    Returns:
        ErrorResponse: Standardized error response with timestamp
        
    Note:
        All exceptions are logged for monitoring and debugging purposes
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    return ErrorResponse(
        error="Internal server error",
        details=str(exc) if settings.debug else None,
        timestamp=datetime.utcnow()
    )

# Development server entry point
if __name__ == "__main__":
    import uvicorn
    # Run the development server with auto-reload in debug mode
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )