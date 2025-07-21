import asyncio
import logging
import re
from typing import Optional, Dict, Any
from .models import Workflow
from anthropic import Anthropic
from ..config import settings

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)

    async def generate_workflow(
        self,
        description: str,
        name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Generate a workflow from a natural language description
        Args:
            description: Natural language description of the workflow
            name: Optional name for the workflow
            context: Additional context for code generation
        Returns:
            Workflow object with generated code
        """
        workflow = Workflow(
            name=name,
            description=description,
            context=context
        )
        
        try:
            workflow.update_status("generating")
            # Generate the code using Anthropic API
            generated_code = await self._generate_code(description, context)
            
            # Validate the generated code
            validation_result = await self._validate_code(generated_code)
            if not validation_result["valid"]:
                raise Exception(f"Generated code validation failed: {validation_result['error']}")
            
            workflow.generated_code = generated_code
            workflow.update_status("ready")
            return workflow
            
        except Exception as e:
            workflow.update_status("failed", str(e))
            raise e

    async def _generate_code(self, description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Python code from workflow description
        """
        system_prompt = """You are a Python code generator for workflow automation systems.

CRITICAL INSTRUCTIONS:
1. Generate ONLY executable Python code - no markdown, no explanations, no comments
2. The code must define: async def execute_workflow(user_input: str) -> str
3. Include ALL necessary imports and API client code directly in the workflow
4. Make the workflow completely self-contained and portable

REQUIRED STRUCTURE:
```python
import asyncio
import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any

# Configuration - replace with your actual values
LIGHTON_API_KEY = "your_api_key_here"
LIGHTON_BASE_URL = "https://api.lighton.ai"
ANTHROPIC_API_KEY = "your_anthropic_api_key_here"

logger = logging.getLogger(__name__)

class ParadigmClient:
    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def document_search(self, query: str, **kwargs) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/v2/chat/document-search"
        payload = {"query": query, **kwargs}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API error {response.status}: {await response.text()}")
    
    async def analyze_documents_with_polling(self, query: str, document_ids: List[int], **kwargs) -> str:
        # Start analysis
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis"
        payload = {"query": query, "document_ids": document_ids, **kwargs}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    chat_response_id = result.get("chat_response_id")
                else:
                    raise Exception(f"Analysis API error {response.status}: {await response.text()}")
        
        # Poll for results
        max_wait = 300  # 5 minutes
        poll_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            endpoint = f"{self.base_url}/api/v2/chat/document-analysis/{chat_response_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get("status", "")
                        if status.lower() in ["completed", "complete", "finished", "success"]:
                            return result.get("result", "Analysis completed")
                        elif status.lower() in ["failed", "error"]:
                            raise Exception(f"Analysis failed: {status}")
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
        
        raise Exception("Analysis timed out")

class AnthropicClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    async def chat_completion(self, prompt: str) -> str:
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    raise Exception(f"Anthropic API error {response.status}: {await response.text()}")

# Initialize clients
paradigm_client = ParadigmClient(LIGHTON_API_KEY, LIGHTON_BASE_URL)
anthropic_client = AnthropicClient(ANTHROPIC_API_KEY)

async def execute_workflow(user_input: str) -> str:
    # Your workflow implementation here
    pass
```

AVAILABLE API METHODS:
1. await paradigm_client.document_search(query: str, workspace_ids=None, file_ids=None, company_scope=True, private_scope=True, tool="DocumentSearch", private=False)
2. await paradigm_client.analyze_documents_with_polling(query: str, document_ids: List[int], model=None, private=False)
3. await anthropic_client.chat_completion(prompt: str)

WORKFLOW ACCESS TO ATTACHED FILES:
- Use global variable 'attached_file_ids: List[int]' when files are attached
- Pass these IDs to file_ids parameter in document_search
- Extract document IDs from search results for analysis

Generate the complete self-contained workflow code that implements the exact logic described."""
        
        enhanced_description = f"""
Workflow Description: {description}
Additional Context: {context or 'None'}

Generate a complete, self-contained workflow that:
1. Includes all necessary imports and API client classes
2. Implements the execute_workflow function with the exact logic described
3. Can be copy-pasted and run independently on any server
4. Handles the workflow requirements exactly as specified
"""
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,  # Increased for full code generation
                system=system_prompt,
                messages=[{"role": "user", "content": enhanced_description}]
            )
            
            code = response.content[0].text
            
            # Log the raw generated code for debugging
            logger.info("🔧 RAW GENERATED CODE:")
            logger.info("=" * 50)
            logger.info(code)
            logger.info("=" * 50)
            
            # Clean up the code - remove markdown formatting if present
            code = self._clean_generated_code(code)
            
            # Log the cleaned code for debugging
            logger.info("🔧 CLEANED GENERATED CODE:")
            logger.info("=" * 50)
            logger.info(code)
            logger.info("=" * 50)
            
            return code
            
        except Exception as e:
            raise Exception(f"Code generation failed: {str(e)}")

    async def regenerate_with_feedback(self, workflow: Workflow, execution_result: str, user_feedback: str) -> str:
        """
        Regenerate workflow code using feedback and execution result
        """
        prompt = f"""
ORIGINAL WORKFLOW DESCRIPTION:
{workflow.description}

ORIGINAL GENERATED CODE:
{workflow.generated_code}

EXECUTION RESULT:
{execution_result}

USER FEEDBACK:
{user_feedback}

INSTRUCTIONS:
Based on the original description, the code that was generated, the actual execution result, and the user's feedback, generate an improved version of the complete self-contained workflow code that addresses the issues identified. Include all imports, API clients, and the execute_workflow function. Only return the improved code, no explanations.
"""
        
        response = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        improved_code = response.content[0].text
        
        # Clean and validate as before
        improved_code = self._clean_generated_code(improved_code)
        validation_result = await self._validate_code(improved_code)
        
        if not validation_result["valid"]:
            raise Exception(f"Improved code validation failed: {validation_result['error']}")
            
        return improved_code

    def _clean_generated_code(self, code: str) -> str:
        """
        Clean up generated code by removing markdown formatting and ensuring proper structure
        """
        # Remove markdown code blocks
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Ensure execute_workflow is async
        if "def execute_workflow(" in code and "async def execute_workflow(" not in code:
            code = code.replace("def execute_workflow(", "async def execute_workflow(")
        
        return code

    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate that the generated code is syntactically correct and has required structure
        """
        try:
            # Check for syntax errors
            compile(code, '<string>', 'exec')
            
            # Check for required function
            if 'def execute_workflow(' not in code:
                return {"valid": False, "error": "Missing execute_workflow function"}
            
            # Check for async definition
            if 'async def execute_workflow(' not in code:
                return {"valid": False, "error": "execute_workflow must be async"}
            
            # Check for required imports
            required_imports = ['import asyncio', 'import aiohttp']
            for imp in required_imports:
                if imp not in code:
                    return {"valid": False, "error": f"Missing required import: {imp}"}
            
            return {"valid": True, "error": None}
            
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}


# Global generator instance
workflow_generator = WorkflowGenerator()