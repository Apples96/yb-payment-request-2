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
                            analysis_result = result.get("result") or result.get("detailed_analysis") or "Analysis completed"
                            return analysis_result
                        elif status.lower() in ["failed", "error"]:
                            raise Exception(f"Analysis failed: {status}")
                    elif response.status == 404:
                        # Analysis not ready yet, continue polling
                        pass
                    else:
                        raise Exception(f"Polling API error {response.status}: {await response.text()}")
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
        
        raise Exception("Analysis timed out")
    
    async def chat_completion(self, prompt: str, model: str = "alfred-4.2") -> str:
        endpoint = f"{self.base_url}/api/v2/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"Paradigm chat completion API error {response.status}: {await response.text()}")
    
    async def analyze_image(self, query: str, document_ids: List[str], model: str = None, private: bool = False) -> str:
        endpoint = f"{self.base_url}/api/v2/chat/image-analysis"
        payload = {
            "query": query,
            "document_ids": document_ids
        }
        if model:
            payload["model"] = model
        if private is not None:
            payload["private"] = private
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("answer", "No analysis result provided")
                else:
                    raise Exception(f"Image analysis API error {response.status}: {await response.text()}")

# Initialize clients
paradigm_client = ParadigmClient(LIGHTON_API_KEY, LIGHTON_BASE_URL)

async def execute_workflow(user_input: str) -> str:
    # Your workflow implementation here
    pass
```

IMPORTANT LIBRARY RESTRICTIONS:
- Only use built-in Python libraries (asyncio, json, logging, typing, re, etc.)
- Only use aiohttp for HTTP requests (already included in template)
- DO NOT import external libraries like nltk, requests, pandas, numpy, etc.
- For text processing, use built-in string methods and 're' module instead of nltk
- For sentence splitting, use simple regex: re.split(r'[.!?]+', text)

AVAILABLE API METHODS:
1. await paradigm_client.document_search(query: str, workspace_ids=None, file_ids=None, company_scope=True, private_scope=True, tool="DocumentSearch", private=False)
2. await paradigm_client.analyze_documents_with_polling(query: str, document_ids: List[str], model=None, private=False)
3. await paradigm_client.chat_completion(prompt: str, model: str = "Alfred 4.2")
4. await paradigm_client.analyze_image(query: str, document_ids: List[str], model=None, private=False) - Analyze images in documents with AI-powered visual analysis

WORKFLOW ACCESS TO ATTACHED FILES:
- Use global variable 'attached_file_ids: List[int]' when files are attached
- Pass these IDs to file_ids parameter in document_search (omit parameter if no files attached)
- For direct document analysis: attached_file_ids ARE the document IDs - use them directly
- Extract document IDs from search results for analysis ONLY when searching, not when using attached files

CORRECT FILE_IDS USAGE:
search_kwargs = {"query": query, "company_scope": True, "private_scope": True}
if 'attached_file_ids' in globals() and attached_file_ids:
    search_kwargs["file_ids"] = attached_file_ids
search_results = await paradigm_client.document_search(**search_kwargs)

CORRECT DOCUMENT_IDS EXTRACTION FOR ANALYSIS:
document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]  # Convert to strings
# OR for attached files: document_ids = [str(file_id) for file_id in attached_file_ids]

CORRECT TEXT PROCESSING (using built-in libraries):
import re
def split_sentences(text):
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

CORRECT SEARCH RESULT USAGE:
search_result = await paradigm_client.document_search(**search_kwargs)
# Use the AI-generated answer from search results
answer = search_result.get("answer", "No answer provided")
# Don't try to extract raw document content - use the answer field

INCORRECT (DON'T DO THIS):
file_ids=attached_file_ids if 'attached_file_ids' in globals() else None  # API doesn't accept None
document_ids = [doc["id"] for doc in search_results.get("documents", [])]  # Should convert to strings
import nltk  # External library not available
answer = search_result["documents"][0].get("content", "")  # Raw content extraction

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
                model="claude-3-5-sonnet-20241022",
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