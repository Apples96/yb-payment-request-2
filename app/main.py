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

# Configure logging
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Workflow Automation API",
    description="API for creating and executing automated workflows using AI",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://scaffold-ai-test2.vercel.app",
        "https://*.vercel.app",
        "https://*.netlify.app",
        "https://*.github.io",
        "https://*.surge.sh",
        "https://*.firebaseapp.com"
    ],  # Frontend origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    try:
        settings.validate()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        raise e

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "Workflow Automation API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/workflows", response_model=WorkflowResponse, tags=["Workflows"])
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a new workflow from a natural language description
    """
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
    Get details of a specific workflow
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
    Execute a workflow with user input
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
    Get details of a specific workflow execution
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

# File upload endpoints

@app.post("/files/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_file(
    file: UploadFile = File(...),
    collection_type: str = Form("private"),
    workspace_id: Optional[int] = Form(None)
):
    """
    Upload a file to Paradigm for use in workflows
    """
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
    Get information about an uploaded file
    """
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
    Ask a question about a specific uploaded file
    """
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
    Delete an uploaded file
    """
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
    Create a workflow that can use uploaded files
    """
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
    Regenerate workflow code using execution result and user feedback
    """
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
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return ErrorResponse(
        error="Internal server error",
        details=str(exc) if settings.debug else None,
        timestamp=datetime.utcnow()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )