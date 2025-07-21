from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class WorkflowStatus(str, Enum):
    CREATED = "created"
    GENERATING = "generating"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowCreateRequest(BaseModel):
    description: str = Field(..., description="Natural language description of the workflow")
    name: Optional[str] = Field(None, description="Optional name for the workflow")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for code generation")

class WorkflowExecuteRequest(BaseModel):
    user_input: str = Field(..., description="Input data to process through the workflow")
    attached_file_ids: Optional[List[int]] = Field(None, description="List of file IDs attached to this query")

class WorkflowResponse(BaseModel):
    id: str = Field(..., description="Unique workflow identifier")
    name: Optional[str] = Field(None, description="Workflow name")
    description: str = Field(..., description="Workflow description")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    generated_code: Optional[str] = Field(None, description="Generated Python code")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class WorkflowExecutionResponse(BaseModel):
    workflow_id: str = Field(..., description="Workflow identifier")
    execution_id: str = Field(..., description="Unique execution identifier")
    result: Optional[str] = Field(None, description="Execution result")
    status: str = Field(..., description="Execution status")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Execution start timestamp")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FileUploadResponse(BaseModel):
    id: int = Field(..., description="File ID in Paradigm")
    filename: str = Field(..., description="Original filename")
    bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    created_at: int = Field(..., description="Creation timestamp")
    purpose: str = Field(..., description="File purpose")

class FileInfoResponse(BaseModel):
    id: int = Field(..., description="File ID")
    filename: str = Field(..., description="Filename")
    status: str = Field(..., description="Processing status")
    created_at: int = Field(..., description="Creation timestamp")
    purpose: str = Field(..., description="File purpose")
    content: Optional[str] = Field(None, description="File content if requested")

class FileQuestionRequest(BaseModel):
    question: str = Field(..., description="Question to ask about the file")

class FileQuestionResponse(BaseModel):
    response: str = Field(..., description="Answer to the question")
    chunks: List[Dict[str, Any]] = Field(..., description="Relevant document chunks")

class WorkflowWithFilesRequest(BaseModel):
    description: str = Field(..., description="Natural language description of the workflow")
    name: Optional[str] = Field(None, description="Optional name for the workflow")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for code generation")
    uploaded_file_ids: Optional[List[int]] = Field(None, description="List of uploaded file IDs to use in workflow")

class WorkflowFeedbackRequest(BaseModel):
    execution_result: str = Field(..., description="The result of running the workflow code")
    user_feedback: str = Field(..., description="User's feedback about what went wrong or what should be improved")