"""
Task Executors - Real autonomous task execution implementations

This module contains the actual execution logic for autonomous tasks.
No magical thinking - real implementations with proper error handling.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Import unified AI client for text generation tasks
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Standard result format for all task executors"""
    
    def __init__(self, 
                 success: bool, 
                 result_data: Dict[str, Any], 
                 execution_time: float,
                 error_message: Optional[str] = None):
        self.success = success
        self.result_data = result_data
        self.execution_time = execution_time
        self.error_message = error_message
        self.status = "completed" if success else "failed"


class BaseTaskExecutor:
    """Base class for all task executors with common functionality"""
    
    def __init__(self, max_execution_time: float = 30.0):
        self.max_execution_time = max_execution_time
        self.ai_client = None
    
    async def _get_ai_client(self):
        """Get AI client with lazy initialization"""
        if self.ai_client is None:
            self.ai_client = await get_unified_client()
        return self.ai_client
    
    async def execute(self, task_params: Dict[str, Any]) -> ExecutionResult:
        """Execute task with timeout and error handling"""
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_impl(task_params),
                timeout=self.max_execution_time
            )
            
            execution_time = time.time() - start_time
            return ExecutionResult(True, result, execution_time)
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Task execution timeout after {execution_time:.2f}s")
            return ExecutionResult(False, {}, execution_time, "Execution timeout")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task execution failed: {e}")
            return ExecutionResult(False, {}, execution_time, str(e))
    
    async def _execute_impl(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _execute_impl")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with robust handling of markdown blocks and extra text."""
        try:
            response = response.strip()
            
            # Method 1: Try direct JSON parsing first
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Method 2: Extract JSON from markdown code blocks
            if "```json" in response or "```" in response:
                # Find JSON within markdown code blocks
                start_markers = ["```json", "```"]
                end_marker = "```"
                
                for start_marker in start_markers:
                    start_idx = response.find(start_marker)
                    if start_idx >= 0:
                        # Find the opening brace after the marker
                        json_start = response.find('{', start_idx)
                        if json_start >= 0:
                            # Find the closing brace before the next ```
                            end_idx = response.find(end_marker, json_start)
                            if end_idx >= 0:
                                json_str = response[json_start:end_idx].strip()
                                try:
                                    return json.loads(json_str)
                                except json.JSONDecodeError:
                                    continue
            
            # Method 3: Find JSON by looking for opening and closing braces
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # If all methods fail, raise error
            raise json.JSONDecodeError("Could not parse JSON from response", response, 0)
            
        except Exception as e:
            raise json.JSONDecodeError(f"JSON parsing failed: {e}", response, 0)


class EmailDraftExecutor(BaseTaskExecutor):
    """Executor for drafting emails based on context"""
    
    async def _execute_impl(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Draft an email based on provided context"""
        
        # Validate required parameters
        recipient = task_params.get("recipient")
        context = task_params.get("context", "")
        email_content = task_params.get("email_content", "")
        
        if not recipient:
            raise ValueError("Email drafting requires 'recipient' parameter")
        
        # Build email drafting prompt
        draft_prompt = f"""
        Draft a professional email reply based on this context:
        
        Recipient: {recipient}
        Context: {context}
        Original email content: {email_content}
        
        Generate a professional, concise email response. Include:
        - Appropriate subject line
        - Professional greeting
        - Clear response to any questions/requests
        - Professional closing
        
        Return in JSON format:
        {{
            "subject": "Re: [subject]",
            "body": "Email body text",
            "tone": "professional|casual|urgent"
        }}
        """
        
        # Get AI client and generate draft
        ai_client = await self._get_ai_client()
        response = await ai_client.text_completion(
            messages=[{"role": "user", "content": draft_prompt}],
            max_tokens=500,
            temperature=0.1
        )
        
        # Parse JSON response
        try:
            draft_data = json.loads(response.strip())
            
            # Validate response structure
            required_fields = ["subject", "body", "tone"]
            if not all(field in draft_data for field in required_fields):
                raise ValueError("AI response missing required email fields")
            
            return {
                "task_type": "email_draft",
                "recipient": recipient,
                "subject": draft_data["subject"],
                "body": draft_data["body"], 
                "tone": draft_data["tone"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "word_count": len(draft_data["body"].split())
            }
            
        except json.JSONDecodeError as e:
            # Fallback: treat entire response as email body
            logger.warning(f"Failed to parse JSON response, using as plain text: {e}")
            return {
                "task_type": "email_draft",
                "recipient": recipient,
                "subject": f"Re: {context[:50]}",
                "body": response.strip(),
                "tone": "professional",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "word_count": len(response.strip().split()),
                "fallback_used": True
            }


class TextGenerationExecutor(BaseTaskExecutor):
    """Universal executor for ANY text generation task"""
    
    def __init__(self, max_execution_time: float = 30.0):
        super().__init__(max_execution_time)
    
    async def _execute_impl(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate any type of text based on the request"""
        
        task_type = params.get("task_type", "text generation")
        content = params.get("content", "")
        context = params.get("context", "")
        instructions = params.get("instructions", "")
        target_audience = params.get("target_audience", "general")
        tone = params.get("tone", "appropriate")
        
        # Build dynamic prompt based on what we're generating
        if "rewrite" in task_type.lower() or "improve" in task_type.lower():
            prompt = f"""Rewrite and improve this text:

Original text: {content}
Context: {context}
Instructions: {instructions}
Target audience: {target_audience}
Desired tone: {tone}

Provide the improved version:"""
        
        elif "message" in task_type.lower() or "text" in task_type.lower():
            prompt = f"""Write a {task_type} based on this context:

Context: {context}
Content to reference: {content}
Specific instructions: {instructions}
Target audience: {target_audience}
Desired tone: {tone}

Generate the text:"""
        
        else:
            # Generic text generation
            prompt = f"""Generate {task_type} based on:

Context: {context}
Content: {content}
Instructions: {instructions}
Audience: {target_audience}
Tone: {tone}

Create the requested content:"""

        try:
            # Get unified client (async function)
            client = await get_unified_client()
            response = await client.text_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return {
                "generated_text": response.strip(),
                "task_type": task_type,
                "word_count": len(response.split()),
                "character_count": len(response)
            }
                
        except Exception as e:
            raise Exception(f"Text generation failed: {e}")


class ResearchExecutor(BaseTaskExecutor):
    """Executor for research tasks using web search and compilation"""
    
    def __init__(self, max_execution_time: float = 45.0):
        super().__init__(max_execution_time)
        # Longer timeout for research tasks
    
    async def _execute_impl(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform research and compile results"""
        
        topic = task_params.get("topic")
        context = task_params.get("context", "")
        
        if not topic:
            raise ValueError("Research requires 'topic' parameter")
        
        # Build research prompt - CRITICAL: Must return ONLY JSON
        research_prompt = f"""You must research this topic and return ONLY valid JSON. No markdown, no explanation, no extra text.

Topic: {topic}
Context: {context}

Research this thoroughly and return EXACTLY this JSON structure with 3-5 detailed findings:

{{
    "topic": "{topic}",
    "key_findings": [
        "Specific finding 1 with details",
        "Specific finding 2 with details", 
        "Specific finding 3 with details",
        "Specific finding 4 with details",
        "Specific finding 5 with details"
    ],
    "details": "Comprehensive explanation with specific data, numbers, and facts",
    "recommendations": [
        "Actionable recommendation 1",
        "Actionable recommendation 2"
    ],
    "sources": [
        "Relevant source 1",
        "Relevant source 2"
    ]
}}

CRITICAL: Return ONLY the JSON object above. No markdown blocks, no explanations, no other text."""
        
        # Get AI client and perform research
        ai_client = await self._get_ai_client()
        response = await ai_client.text_completion(
            messages=[{"role": "user", "content": research_prompt}],
            max_tokens=800,
            temperature=0.2
        )
        
        # Parse JSON response with robust parsing (handle markdown blocks)
        try:
            research_data = self._parse_json_response(response)
            
            # Validate response structure
            required_fields = ["key_findings", "details"]
            if not all(field in research_data for field in required_fields):
                raise ValueError("AI response missing required research fields")
            
            # Validate research quality - must have at least 3 findings
            key_findings = research_data.get("key_findings", [])
            if len(key_findings) < 3:
                raise ValueError(f"Research quality insufficient: only {len(key_findings)} findings, need at least 3")
            
            return {
                "task_type": "research",
                "topic": topic,
                "key_findings": research_data.get("key_findings", []),
                "details": research_data.get("details", ""),
                "recommendations": research_data.get("recommendations", []),
                "sources": research_data.get("sources", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "finding_count": len(research_data.get("key_findings", []))
            }
            
        except json.JSONDecodeError as e:
            # NO MORE FAKE SUCCESS - fail properly when JSON parsing fails
            logger.error(f"Research executor failed: AI returned invalid JSON: {e}")
            logger.error(f"AI response was: {response[:500]}...")
            raise Exception(f"Research failed: AI returned invalid JSON format. Response: {response[:100]}...")


class DocumentCreationExecutor(BaseTaskExecutor):
    """Executor for creating documents, outlines, and structured content"""
    
    async def _execute_impl(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured document content"""
        
        document_type = task_params.get("document_type", "outline")
        topic = task_params.get("topic")
        context = task_params.get("context", "")
        
        if not topic:
            raise ValueError("Document creation requires 'topic' parameter")
        
        # Build document creation prompt
        if document_type == "outline":
            creation_prompt = f"""
            Create a detailed outline for: {topic}
            
            Context: {context}
            
            Generate a structured outline with:
            - Main sections (3-5 sections)
            - Subsections under each main section
            - Key points or topics to cover
            
            Return in JSON format:
            {{
                "title": "{topic}",
                "sections": [
                    {{
                        "title": "Section 1 Title",
                        "subsections": ["Subsection A", "Subsection B"],
                        "key_points": ["Point 1", "Point 2"]
                    }}
                ]
            }}
            """
        else:
            creation_prompt = f"""
            Create content for: {topic}
            Type: {document_type}
            Context: {context}
            
            Generate structured, useful content appropriate for the document type.
            
            Return in JSON format:
            {{
                "title": "{topic}",
                "content": "Main content text",
                "sections": ["section1", "section2"],
                "key_points": ["point1", "point2"]
            }}
            """
        
        # Get AI client and create document
        ai_client = await self._get_ai_client()
        response = await ai_client.text_completion(
            messages=[{"role": "user", "content": creation_prompt}],
            max_tokens=600,
            temperature=0.3
        )
        
        # Parse JSON response
        try:
            doc_data = json.loads(response.strip())
            
            return {
                "task_type": "document_creation",
                "document_type": document_type,
                "topic": topic,
                "title": doc_data.get("title", topic),
                "content": doc_data.get("content", ""),
                "sections": doc_data.get("sections", []),
                "key_points": doc_data.get("key_points", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "word_count": len(doc_data.get("content", "").split()) if doc_data.get("content") else 0
            }
            
        except json.JSONDecodeError as e:
            # Fallback: use response as content
            logger.warning(f"Failed to parse JSON response, using as content: {e}")
            return {
                "task_type": "document_creation",
                "document_type": document_type,
                "topic": topic,
                "title": topic,
                "content": response.strip(),
                "sections": [],
                "key_points": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "word_count": len(response.strip().split()),
                "fallback_used": True
            }


class DataOrganizerExecutor(BaseTaskExecutor):
    """Executor for organizing and structuring data"""
    
    async def _execute_impl(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Organize unstructured data into structured format"""
        
        data_content = task_params.get("data_content")
        organization_type = task_params.get("organization_type", "list")
        
        if not data_content:
            raise ValueError("Data organization requires 'data_content' parameter")
        
        # Build organization prompt - CRITICAL: Must return ONLY JSON
        organize_prompt = f"""You must organize this data and return ONLY valid JSON. No markdown, no explanation, no extra text.

Data to organize: {data_content}
Organization type: {organization_type}

Organize this data into logical categories and return EXACTLY this JSON structure:

{{
    "organized_data": {{
        "categories": [
            {{
                "name": "Category Name 1",
                "items": ["specific item 1", "specific item 2", "specific item 3"]
            }},
            {{
                "name": "Category Name 2", 
                "items": ["specific item 4", "specific item 5"]
            }}
        ],
        "summary": "Brief summary of how the data was organized and what categories were created"
    }}
}}

CRITICAL: Return ONLY the JSON object above. No markdown blocks, no explanations, no other text."""
        
        # Get AI client and organize data
        ai_client = await self._get_ai_client()
        response = await ai_client.text_completion(
            messages=[{"role": "user", "content": organize_prompt}],
            max_tokens=500,
            temperature=0.1
        )
        
        # Parse JSON response with robust parsing (handle markdown blocks)
        try:
            org_data = self._parse_json_response(response)
            
            return {
                "task_type": "data_organization",
                "organization_type": organization_type,
                "original_data": data_content[:200] + "..." if len(data_content) > 200 else data_content,
                "organized_data": org_data.get("organized_data", {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "categories_count": len(org_data.get("organized_data", {}).get("categories", []))
            }
            
        except json.JSONDecodeError as e:
            # NO MORE FAKE SUCCESS - fail properly when JSON parsing fails
            logger.error(f"Data organization executor failed: AI returned invalid JSON: {e}")
            logger.error(f"AI response was: {response[:500]}...")
            raise Exception(f"Data organization failed: AI returned invalid JSON format. Response: {response[:100]}...")


# Task executor registry
TASK_EXECUTORS = {
    "email_draft": EmailDraftExecutor,
    "text_generation": TextGenerationExecutor,  # Universal text generation
    "research": ResearchExecutor,
    "document_creation": DocumentCreationExecutor,
    "data_organization": DataOrganizerExecutor
}


async def get_task_executor(task_type: str) -> BaseTaskExecutor:
    """Get appropriate task executor for given task type"""
    executor_class = TASK_EXECUTORS.get(task_type)
    if not executor_class:
        raise ValueError(f"Unknown task type: {task_type}")
    
    return executor_class()


async def execute_autonomous_task(task_type: str, task_params: Dict[str, Any]) -> ExecutionResult:
    """Execute autonomous task with proper error handling"""
    logger.info(f"🤖 Executing autonomous task: {task_type}")
    
    try:
        executor = await get_task_executor(task_type)
        result = await executor.execute(task_params)
        
        if result.success:
            logger.info(f"✅ Task completed: {task_type} in {result.execution_time:.2f}s")
        else:
            logger.error(f"❌ Task failed: {task_type} - {result.error_message}")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 Task executor failed: {task_type} - {e}")
        return ExecutionResult(False, {}, 0.0, f"Executor error: {str(e)}")
