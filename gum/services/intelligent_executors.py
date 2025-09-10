"""
Intelligent Content Generation Executors
Creates completed work that users can immediately use - no external system modifications
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

# Import unified AI client for content generation
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)

@dataclass
class CompletedWork:
    """Represents completed work ready for user consumption"""
    title: str
    description: str
    content: str
    content_type: str  # 'text', 'json', 'markdown', 'html', 'csv'
    preview: str
    action_label: str  # e.g., "Open Chat", "View Results", "Copy Content"
    metadata: Dict[str, Any]
    created_at: datetime

class BaseIntelligentExecutor:
    """Base class for intelligent content generation executors"""
    
    def __init__(self, max_execution_time: float = 45.0):
        self.max_execution_time = max_execution_time
        self.ai_client = None
    
    async def _get_ai_client(self):
        """Get AI client with lazy initialization"""
        if self.ai_client is None:
            self.ai_client = await get_unified_client()
        return self.ai_client
    
    async def execute(self, context: Dict[str, Any]) -> Optional[CompletedWork]:
        """Execute intelligent content generation"""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self._generate_content(context),
                timeout=self.max_execution_time
            )
            
            execution_time = time.time() - start_time
            logger.info(f"✅ Generated content in {execution_time:.2f}s: {result.title}")
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Content generation timeout after {execution_time:.2f}s")
            return None
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Content generation failed: {e}")
            return None
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _generate_content")

class FinancialAnalysisExecutor(BaseIntelligentExecutor):
    """Creates completed financial analysis and reports"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate financial analysis based on detected data"""
        
        # Extract financial context
        numbers = context.get('data_context', {}).get('numbers', [])
        percentages = context.get('data_context', {}).get('percentages', [])
        currencies = context.get('data_context', {}).get('currencies', [])
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        You are a financial analyst. Based on this data context, create a comprehensive financial analysis report.
        
        CONTEXT:
        Numbers detected: {numbers[:10]}  # First 10 numbers
        Percentages: {percentages}
        Currency amounts: {currencies}
        Content: {visible_content[:500]}
        
        Create a professional financial analysis report that includes:
        1. Executive Summary (2-3 sentences)
        2. Key Metrics Analysis
        3. Performance Highlights
        4. Risk Assessment
        5. Recommendations
        
        Format as a structured report ready for email or presentation.
        Make specific references to the actual numbers you see in the data.
        """
        
        client = await self._get_ai_client()
        analysis = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        
        return CompletedWork(
            title="Quarterly Financial Analysis Report",
            description="I analyzed your financial data and created a comprehensive performance report with key metrics, highlights, and strategic recommendations.",
            content=analysis,
            content_type="markdown",
            preview=analysis[:200] + "...",
            action_label="Open Report",
            metadata={
                "data_points": len(numbers),
                "metrics_analyzed": len(percentages),
                "currency_amounts": len(currencies),
                "analysis_type": "financial_performance"
            },
            created_at=datetime.now(timezone.utc)
        )

class WorkflowOptimizerExecutor(BaseIntelligentExecutor):
    """Analyzes workflows and creates optimization recommendations"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate workflow optimization analysis"""
        
        tools_used = context.get('workflow_context', {}).get('tools_used', [])
        current_task = context.get('workflow_context', {}).get('current_task', 'unknown')
        file_context = context.get('file_context', {})
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        You are a productivity consultant. Analyze this workflow and create specific optimization recommendations.
        
        WORKFLOW CONTEXT:
        Current task: {current_task}
        Tools being used: {tools_used}
        Files involved: {file_context.get('files_mentioned', [])}
        File types: {file_context.get('file_types', [])}
        Content: {visible_content[:400]}
        
        Create a detailed workflow optimization report with:
        1. Current Workflow Analysis
        2. Identified Inefficiencies
        3. Specific Automation Opportunities
        4. Tool Recommendations
        5. Implementation Steps
        
        Be specific about the tools and files you see. Provide actionable recommendations.
        """
        
        client = await self._get_ai_client()
        optimization = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.2
        )
        
        return CompletedWork(
            title="Workflow Optimization Analysis",
            description=f"I analyzed your {current_task} workflow and identified 3 automation opportunities with specific implementation steps.",
            content=optimization,
            content_type="markdown",
            preview=optimization[:200] + "...",
            action_label="View Recommendations",
            metadata={
                "task_type": current_task,
                "tools_analyzed": len(tools_used),
                "files_analyzed": len(file_context.get('files_mentioned', [])),
                "optimization_type": "workflow_efficiency"
            },
            created_at=datetime.now(timezone.utc)
        )

class ContentCreatorExecutor(BaseIntelligentExecutor):
    """Creates various types of content based on context"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate content based on detected patterns"""
        
        content_patterns = context.get('content_patterns', [])
        visible_content = context.get('visible_content', '')
        communication_context = context.get('communication_context', {})
        
        # Determine content type to create
        if 'communication_work' in content_patterns:
            return await self._create_communication_content(context)
        elif 'academic_work' in content_patterns:
            return await self._create_academic_content(context)
        elif 'creative_work' in content_patterns:
            return await self._create_creative_content(context)
        else:
            return await self._create_general_content(context)
    
    async def _create_communication_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Create communication content like emails, presentations"""
        
        subjects = context.get('communication_context', {}).get('subjects', [])
        emails = context.get('communication_context', {}).get('emails', [])
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        Create professional communication content based on this context.
        
        CONTEXT:
        Email subjects: {subjects}
        Email addresses: {emails}
        Content: {visible_content[:400]}
        
        Create a professional email response or communication piece that:
        1. Addresses the key points from the context
        2. Is appropriately formal/informal based on context
        3. Includes clear next steps
        4. Is ready to send
        
        Format as a complete email with subject line.
        """
        
        client = await self._get_ai_client()
        communication = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4
        )
        
        return CompletedWork(
            title="Professional Email Draft",
            description="I drafted a professional email response addressing the key points from your conversation, ready to send.",
            content=communication,
            content_type="text",
            preview=communication[:150] + "...",
            action_label="Copy Email",
            metadata={
                "communication_type": "email",
                "recipients": len(emails),
                "subjects_referenced": len(subjects)
            },
            created_at=datetime.now(timezone.utc)
        )
    
    async def _create_academic_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Create academic content like research summaries, analysis"""
        
        visible_content = context.get('visible_content', '')
        file_context = context.get('file_context', {})
        
        prompt = f"""
        Create academic content based on this research context.
        
        CONTEXT:
        Content: {visible_content[:500]}
        Files: {file_context.get('files_mentioned', [])}
        
        Create a structured academic analysis that includes:
        1. Key Findings Summary
        2. Methodology Notes
        3. Critical Analysis
        4. Implications
        5. Further Research Directions
        
        Format as a professional academic summary.
        """
        
        client = await self._get_ai_client()
        academic_content = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3
        )
        
        return CompletedWork(
            title="Research Analysis Summary",
            description="I created a structured academic analysis with key findings, methodology, and implications based on your research.",
            content=academic_content,
            content_type="markdown",
            preview=academic_content[:200] + "...",
            action_label="View Analysis",
            metadata={
                "content_type": "academic_analysis",
                "sources_analyzed": len(file_context.get('files_mentioned', []))
            },
            created_at=datetime.now(timezone.utc)
        )
    
    async def _create_general_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Create general helpful content"""
        
        visible_content = context.get('visible_content', '')
        actionable_items = context.get('actionable_items', [])
        
        prompt = f"""
        Based on this context, create helpful content that provides immediate value.
        
        CONTEXT:
        Content: {visible_content[:400]}
        Actionable items: {[item.get('context', '') for item in actionable_items[:3]]}
        
        Create content that:
        1. Addresses the main topic or task
        2. Provides actionable insights
        3. Is immediately useful
        4. Includes specific recommendations
        
        Format as a structured guide or summary.
        """
        
        client = await self._get_ai_client()
        content = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4
        )
        
        return CompletedWork(
            title="Contextual Guide",
            description="I created a helpful guide with actionable insights based on your current activity.",
            content=content,
            content_type="markdown",
            preview=content[:150] + "...",
            action_label="View Guide",
            metadata={
                "actionable_items": len(actionable_items),
                "content_type": "general_guide"
            },
            created_at=datetime.now(timezone.utc)
        )

class CodeAnalysisExecutor(BaseIntelligentExecutor):
    """Analyzes code and creates documentation, refactoring suggestions"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate code analysis and documentation"""
        
        code_context = context.get('code_context', {})
        visible_content = context.get('visible_content', '')
        file_context = context.get('file_context', {})
        
        functions = code_context.get('functions', [])
        classes = code_context.get('classes', [])
        errors = code_context.get('errors', [])
        language = code_context.get('programming_language', 'unknown')
        
        if errors:
            return await self._create_debugging_guide(context)
        elif functions or classes:
            return await self._create_code_documentation(context)
        else:
            return await self._create_code_analysis(context)
    
    async def _create_debugging_guide(self, context: Dict[str, Any]) -> CompletedWork:
        """Create debugging guide for detected errors"""
        
        errors = context.get('code_context', {}).get('errors', [])
        language = context.get('code_context', {}).get('programming_language', 'unknown')
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        Create a debugging guide for these code errors.
        
        CONTEXT:
        Programming language: {language}
        Errors detected: {errors}
        Code context: {visible_content[:400]}
        
        Create a comprehensive debugging guide with:
        1. Error Analysis
        2. Root Cause Identification
        3. Step-by-step Solutions
        4. Prevention Strategies
        5. Code Examples (if applicable)
        
        Be specific about the errors you see and provide actionable solutions.
        """
        
        client = await self._get_ai_client()
        debugging_guide = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.2
        )
        
        return CompletedWork(
            title="Code Debugging Guide",
            description=f"I analyzed your {language} errors and created a step-by-step debugging guide with specific solutions.",
            content=debugging_guide,
            content_type="markdown",
            preview=debugging_guide[:200] + "...",
            action_label="View Solutions",
            metadata={
                "language": language,
                "errors_analyzed": len(errors),
                "guide_type": "debugging"
            },
            created_at=datetime.now(timezone.utc)
        )
    
    async def _create_code_documentation(self, context: Dict[str, Any]) -> CompletedWork:
        """Create documentation for detected code"""
        
        code_context = context.get('code_context', {})
        functions = code_context.get('functions', [])
        classes = code_context.get('classes', [])
        language = code_context.get('programming_language', 'unknown')
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        Create comprehensive code documentation.
        
        CONTEXT:
        Programming language: {language}
        Functions: {functions[:10]}
        Classes: {classes[:5]}
        Code context: {visible_content[:400]}
        
        Create professional documentation with:
        1. Overview
        2. Function/Class Descriptions
        3. Usage Examples
        4. Parameters and Return Values
        5. Best Practices
        
        Format as clean, professional documentation.
        """
        
        client = await self._get_ai_client()
        documentation = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        
        return CompletedWork(
            title="Code Documentation",
            description=f"I generated comprehensive documentation for your {language} code with usage examples and best practices.",
            content=documentation,
            content_type="markdown",
            preview=documentation[:200] + "...",
            action_label="View Docs",
            metadata={
                "language": language,
                "functions_documented": len(functions),
                "classes_documented": len(classes),
                "doc_type": "code_documentation"
            },
            created_at=datetime.now(timezone.utc)
        )

class DataAnalysisExecutor(BaseIntelligentExecutor):
    """Analyzes data and creates insights, visualizations descriptions"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate data analysis insights"""
        
        data_context = context.get('data_context', {})
        numbers = data_context.get('numbers', [])
        percentages = data_context.get('percentages', [])
        dates = data_context.get('dates', [])
        visible_content = context.get('visible_content', '')
        
        prompt = f"""
        Analyze this data and create actionable insights.
        
        DATA CONTEXT:
        Numbers: {numbers[:15]}  # First 15 numbers
        Percentages: {percentages}
        Dates: {dates}
        Content: {visible_content[:400]}
        
        Create a data analysis report with:
        1. Data Summary
        2. Key Patterns Identified
        3. Statistical Insights
        4. Trends and Correlations
        5. Actionable Recommendations
        6. Suggested Visualizations
        
        Be specific about the actual numbers and patterns you see.
        """
        
        client = await self._get_ai_client()
        analysis = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.3
        )
        
        return CompletedWork(
            title="Data Analysis Report",
            description=f"I analyzed {len(numbers)} data points and identified key patterns with actionable recommendations.",
            content=analysis,
            content_type="markdown",
            preview=analysis[:200] + "...",
            action_label="View Analysis",
            metadata={
                "data_points": len(numbers),
                "percentages": len(percentages),
                "date_ranges": len(dates),
                "analysis_type": "statistical_insights"
            },
            created_at=datetime.now(timezone.utc)
        )

class ResourceCompilerExecutor(BaseIntelligentExecutor):
    """Compiles relevant resources and creates curated lists"""
    
    async def _generate_content(self, context: Dict[str, Any]) -> CompletedWork:
        """Generate curated resource compilation"""
        
        current_task = context.get('workflow_context', {}).get('current_task', 'unknown')
        content_patterns = context.get('content_patterns', [])
        visible_content = context.get('visible_content', '')
        intent_signals = context.get('intent_signals', [])
        
        prompt = f"""
        Create a curated resource compilation based on this context.
        
        CONTEXT:
        Current task: {current_task}
        Content patterns: {content_patterns}
        Intent signals: {intent_signals}
        Content: {visible_content[:400]}
        
        Create a comprehensive resource guide with:
        1. Essential Tools and Resources
        2. Learning Materials
        3. Best Practices
        4. Community Resources
        5. Next Steps
        
        Organize by priority and relevance to the current task.
        """
        
        client = await self._get_ai_client()
        resources = await client.text_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.4
        )
        
        return CompletedWork(
            title="Curated Resource Guide",
            description=f"I compiled essential resources and tools for your {current_task} work, organized by priority.",
            content=resources,
            content_type="markdown",
            preview=resources[:200] + "...",
            action_label="View Resources",
            metadata={
                "task_focus": current_task,
                "patterns_analyzed": len(content_patterns),
                "resource_type": "curated_compilation"
            },
            created_at=datetime.now(timezone.utc)
        )

# Executor registry for intelligent content generation
INTELLIGENT_EXECUTORS = {
    'financial_analysis': FinancialAnalysisExecutor,
    'workflow_optimization': WorkflowOptimizerExecutor,
    'content_creation': ContentCreatorExecutor,
    'code_analysis': CodeAnalysisExecutor,
    'data_analysis': DataAnalysisExecutor,
    'resource_compilation': ResourceCompilerExecutor
}

async def get_intelligent_executor(executor_type: str) -> BaseIntelligentExecutor:
    """Get appropriate intelligent executor for content generation"""
    executor_class = INTELLIGENT_EXECUTORS.get(executor_type)
    if not executor_class:
        # Default to content creation executor
        executor_class = ContentCreatorExecutor
    
    return executor_class()

async def determine_best_executor(context: Dict[str, Any]) -> str:
    """Determine the best executor type based on context"""
    
    # Check for financial patterns
    data_context = context.get('data_context', {})
    if (data_context.get('currencies') or 
        any(word in context.get('visible_content', '').lower() 
            for word in ['revenue', 'profit', 'budget', 'financial', 'quarterly'])):
        return 'financial_analysis'
    
    # Check for code patterns
    code_context = context.get('code_context', {})
    if (code_context.get('functions') or code_context.get('classes') or 
        code_context.get('errors') or code_context.get('programming_language')):
        return 'code_analysis'
    
    # Check for data analysis patterns
    if len(data_context.get('numbers', [])) > 5:
        return 'data_analysis'
    
    # Check for workflow patterns
    workflow_context = context.get('workflow_context', {})
    if workflow_context.get('tools_used') and len(workflow_context.get('tools_used', [])) > 1:
        return 'workflow_optimization'
    
    # Check for research/resource patterns
    intent_signals = context.get('intent_signals', [])
    if 'analysis_intent' in intent_signals or 'research' in context.get('visible_content', '').lower():
        return 'resource_compilation'
    
    # Default to content creation
    return 'content_creation'