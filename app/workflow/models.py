from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import uuid

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: str = ""
    generated_code: Optional[str] = None
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    def update_status(self, status: str, error: Optional[str] = None):
        """Update workflow status and timestamp"""
        self.status = status
        self.updated_at = datetime.utcnow()
        if error:
            self.error = error

@dataclass
class WorkflowExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    user_input: str = ""
    result: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    execution_time: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def mark_completed(self, result: str, execution_time: float):
        """Mark execution as completed with result"""
        self.result = result
        self.status = ExecutionStatus.COMPLETED
        self.execution_time = execution_time
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, error: str, execution_time: Optional[float] = None):
        """Mark execution as failed with error"""
        self.error = error
        self.status = ExecutionStatus.FAILED
        self.execution_time = execution_time
        self.completed_at = datetime.utcnow()

@dataclass
class CodeGenerationContext:
    """Context for code generation"""
    available_tools: List[str] = field(default_factory=lambda: ["paradigm_search", "chat_completion"])
    max_steps: int = 50
    timeout_seconds: int = 300
    additional_context: Optional[Dict[str, Any]] = None