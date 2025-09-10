"""
Universal AI Expert System
A truly intelligent system that can understand any situation, research the context,
and implement solutions like a professional expert in that domain.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

# Import unified AI client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)

@dataclass
class ExpertWork:
    """Represents expert-level completed work"""
    title: str
    description: str
    content: str
    content_type: str
    preview: str
    action_label: str
    expert_domain: str
    research_summary: str
    implementation_approach: str
    metadata: Dict[str, Any]
    created_at: datetime

class UniversalAIExpert:
    """
    Universal AI Expert that can understand any situation and implement solutions
    like a professional expert in that domain.
    """
    
    def __init__(self, max_execution_time: float = 60.0):
        self.max_execution_time = max_execution_time
        self.ai_client = None
    
    async def _get_ai_client(self):
        """Get AI client with lazy initialization"""
        if self.ai_client is None:
            self.ai_client = await get_unified_client()
        return self.ai_client
    
    async def analyze_and_implement(self, context: Dict[str, Any]) -> Optional[ExpertWork]:
        """
        Universal analysis and implementation pipeline:
        1. Understand the situation deeply
        2. Research the domain and best practices
        3. Implement a professional solution
        """
        
        try:
            # Step 1: Deep Situation Understanding
            situation_analysis = await self._understand_situation(context)
            
            # Step 2: Domain Research and Expertise Acquisition
            expert_knowledge = await self._research_domain(situation_analysis)
            
            # Step 3: Professional Implementation
            expert_work = await self._implement_solution(situation_analysis, expert_knowledge, context)
            
            return expert_work
            
        except Exception as e:
            logger.error(f"Universal AI Expert failed: {e}")
            return None
    
    async def _understand_situation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep situation understanding - figure out what's really happening
        """
        
        visible_content = context.get('visible_content', '')
        file_context = context.get('file_context', {})
        code_context = context.get('code_context', {})
        data_context = context.get('data_context', {})
        workflow_context = context.get('workflow_context', {})
        
        situation_prompt = f"""
You are a universal expert analyst. Analyze this situation deeply and understand what's really happening.

CONTEXT DATA:
Visible Content: {visible_content}
Files: {file_context.get('files_mentioned', [])}
Code Elements: {code_context}
Data Elements: {data_context}
Workflow: {workflow_context}

DEEP ANALYSIS TASK:
1. What is the user actually trying to accomplish? (not just what they're doing)
2. What domain/field is this? (finance, engineering, marketing, research, etc.)
3. What stage are they at in their work?
4. What are the key challenges or problems they're facing?
5. What would a professional expert in this domain do next?
6. What specific deliverable would be most valuable right now?

Return a JSON analysis:
{{
    "primary_objective": "What the user is ultimately trying to achieve",
    "domain": "The professional domain this falls under",
    "work_stage": "Where they are in the process",
    "key_challenges": ["challenge1", "challenge2"],
    "expert_perspective": "What a professional would focus on",
    "most_valuable_deliverable": "The single most valuable thing to create right now",
    "context_clues": ["specific evidence from the data"],
    "urgency_level": "high|medium|low",
    "complexity_level": "high|medium|low"
}}
"""
        
        client = await self._get_ai_client()
        response = await client.text_completion(
            messages=[{"role": "user", "content": situation_prompt}],
            max_tokens=800,
            temperature=0.1
        )
        
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "primary_objective": "Analyze and improve current work",
                "domain": "general",
                "work_stage": "in_progress",
                "key_challenges": ["unclear context"],
                "expert_perspective": "Provide helpful analysis",
                "most_valuable_deliverable": "Contextual analysis",
                "context_clues": ["limited data available"],
                "urgency_level": "medium",
                "complexity_level": "medium"
            }
    
    async def _research_domain(self, situation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research the domain and acquire expert knowledge
        """
        
        domain = situation_analysis.get('domain', 'general')
        objective = situation_analysis.get('primary_objective', '')
        challenges = situation_analysis.get('key_challenges', [])
        
        research_prompt = f"""
You are now becoming an expert in {domain}. Research and compile expert knowledge for this situation.

SITUATION:
Domain: {domain}
Objective: {objective}
Challenges: {challenges}

RESEARCH TASK:
Act as a world-class expert in {domain}. Provide comprehensive expert knowledge including:

1. DOMAIN EXPERTISE:
   - Key principles and best practices in {domain}
   - Common methodologies and frameworks
   - Industry standards and benchmarks
   - Critical success factors

2. SITUATION-SPECIFIC KNOWLEDGE:
   - How experts typically approach this type of objective
   - Common pitfalls and how to avoid them
   - Tools and techniques that would be most effective
   - Quality standards for deliverables in this domain

3. IMPLEMENTATION STRATEGY:
   - Step-by-step approach a professional would take
   - Key deliverables that provide maximum value
   - How to structure the work for best results
   - Metrics or criteria for success

Return expert knowledge as JSON:
{{
    "domain_expertise": {{
        "key_principles": ["principle1", "principle2"],
        "best_practices": ["practice1", "practice2"],
        "methodologies": ["method1", "method2"],
        "success_factors": ["factor1", "factor2"]
    }},
    "situation_approach": {{
        "professional_method": "How an expert would approach this",
        "common_pitfalls": ["pitfall1", "pitfall2"],
        "recommended_tools": ["tool1", "tool2"],
        "quality_standards": ["standard1", "standard2"]
    }},
    "implementation_strategy": {{
        "step_by_step": ["step1", "step2", "step3"],
        "key_deliverables": ["deliverable1", "deliverable2"],
        "success_metrics": ["metric1", "metric2"],
        "professional_structure": "How to organize the work"
    }}
}}
"""
        
        client = await self._get_ai_client()
        response = await client.text_completion(
            messages=[{"role": "user", "content": research_prompt}],
            max_tokens=1000,
            temperature=0.2
        )
        
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Fallback
            return {
                "domain_expertise": {
                    "key_principles": ["thoroughness", "accuracy"],
                    "best_practices": ["research first", "validate results"],
                    "methodologies": ["systematic approach"],
                    "success_factors": ["attention to detail"]
                },
                "situation_approach": {
                    "professional_method": "Systematic analysis and implementation",
                    "common_pitfalls": ["rushing", "incomplete analysis"],
                    "recommended_tools": ["structured approach"],
                    "quality_standards": ["professional quality"]
                },
                "implementation_strategy": {
                    "step_by_step": ["analyze", "research", "implement"],
                    "key_deliverables": ["comprehensive solution"],
                    "success_metrics": ["user satisfaction"],
                    "professional_structure": "Clear and actionable"
                }
            }
    
    async def _implement_solution(self, situation_analysis: Dict[str, Any], 
                                expert_knowledge: Dict[str, Any], 
                                original_context: Dict[str, Any]) -> ExpertWork:
        """
        Implement a professional solution using expert knowledge
        """
        
        domain = situation_analysis.get('domain', 'general')
        objective = situation_analysis.get('primary_objective', '')
        deliverable = situation_analysis.get('most_valuable_deliverable', '')
        
        # Get the implementation strategy
        implementation_strategy = expert_knowledge.get('implementation_strategy', {})
        domain_expertise = expert_knowledge.get('domain_expertise', {})
        
        implementation_prompt = f"""
You are now a world-class expert in {domain} implementing a professional solution.

SITUATION ANALYSIS:
{json.dumps(situation_analysis, indent=2)}

EXPERT KNOWLEDGE:
{json.dumps(expert_knowledge, indent=2)}

ORIGINAL CONTEXT:
{json.dumps(original_context, indent=2)}

IMPLEMENTATION TASK:
As a professional expert in {domain}, create a comprehensive, high-quality deliverable that addresses the user's objective: {objective}

The deliverable should be: {deliverable}

EXPERT IMPLEMENTATION REQUIREMENTS:
1. Apply professional standards and best practices from {domain}
2. Use the methodologies and frameworks that experts in this field use
3. Create something that would meet professional quality standards
4. Include specific, actionable content based on the actual context
5. Structure it the way a professional in {domain} would
6. Make it immediately useful and implementable

DELIVERABLE FORMAT:
Create a comprehensive, professional-quality deliverable that includes:
- Executive summary or overview
- Detailed analysis or methodology
- Specific recommendations or implementation steps
- Professional formatting and structure
- Actionable next steps

Make this something that could be presented to stakeholders or used immediately in a professional context.
"""
        
        client = await self._get_ai_client()
        implementation = await client.text_completion(
            messages=[{"role": "user", "content": implementation_prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        
        # Create expert work result
        return ExpertWork(
            title=f"✅ Completed: Professional {domain.title()} Analysis",
            description=f"I researched {domain} best practices and implemented a professional-grade solution for your {objective}.",
            content=implementation,
            content_type="markdown",
            preview=implementation[:200] + "...",
            action_label="Open Professional Analysis",
            expert_domain=domain,
            research_summary=json.dumps(expert_knowledge, indent=2),
            implementation_approach=json.dumps(situation_analysis, indent=2),
            metadata={
                "domain": domain,
                "objective": objective,
                "deliverable_type": deliverable,
                "expert_level": "professional",
                "research_depth": "comprehensive"
            },
            created_at=datetime.now(timezone.utc)
        )

class UniversalResearchEngine:
    """
    Universal research engine that can research any topic and become an expert
    """
    
    def __init__(self):
        self.ai_client = None
    
    async def _get_ai_client(self):
        if self.ai_client is None:
            self.ai_client = await get_unified_client()
        return self.ai_client
    
    async def research_and_become_expert(self, topic: str, context: str) -> Dict[str, Any]:
        """
        Research a topic deeply and acquire expert-level knowledge
        """
        
        research_prompt = f"""
You are a universal research AI. Research this topic comprehensively and become an expert.

TOPIC: {topic}
CONTEXT: {context}

COMPREHENSIVE RESEARCH TASK:
1. Research the topic from multiple angles
2. Understand the professional standards and best practices
3. Learn the methodologies and frameworks used by experts
4. Identify the key success factors and common pitfalls
5. Understand how professionals in this field work
6. Learn the terminology and concepts

Provide comprehensive expert knowledge:
{{
    "topic_overview": "Comprehensive overview of the topic",
    "expert_methodologies": ["method1", "method2", "method3"],
    "professional_standards": ["standard1", "standard2"],
    "best_practices": ["practice1", "practice2", "practice3"],
    "common_frameworks": ["framework1", "framework2"],
    "success_factors": ["factor1", "factor2"],
    "common_pitfalls": ["pitfall1", "pitfall2"],
    "professional_tools": ["tool1", "tool2"],
    "quality_criteria": ["criteria1", "criteria2"],
    "implementation_approach": "How professionals typically implement solutions",
    "key_deliverables": ["deliverable1", "deliverable2"],
    "expert_insights": ["insight1", "insight2"]
}}
"""
        
        client = await self._get_ai_client()
        response = await client.text_completion(
            messages=[{"role": "user", "content": research_prompt}],
            max_tokens=1200,
            temperature=0.2
        )
        
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {"error": "Failed to parse research results"}

# Universal AI Expert that replaces the constrained executors
async def create_universal_expert_solution(context: Dict[str, Any]) -> Optional[ExpertWork]:
    """
    Universal function that can handle ANY situation by:
    1. Understanding the situation
    2. Researching the domain
    3. Implementing like a professional expert
    """
    
    try:
        # Initialize universal expert
        expert = UniversalAIExpert()
        
        # Analyze and implement
        result = await expert.analyze_and_implement(context)
        
        return result
        
    except Exception as e:
        logger.error(f"Universal expert failed: {e}")
        return None

# Replace the constrained executor selection with universal approach
async def get_universal_expert() -> UniversalAIExpert:
    """Get the universal AI expert (replaces specific executors)"""
    return UniversalAIExpert()

async def determine_expert_approach(context: Dict[str, Any]) -> str:
    """
    Determine what kind of expert approach is needed
    (This replaces the constrained executor selection)
    """
    
    # The universal expert handles everything, but we can still categorize for metrics
    visible_content = context.get('visible_content', '').lower()
    
    # Detect domain based on content
    if any(word in visible_content for word in ['revenue', 'profit', 'budget', 'financial', 'quarterly', 'roi']):
        return 'financial_expert'
    elif any(word in visible_content for word in ['function', 'class', 'error', 'code', 'debug', 'syntax']):
        return 'technical_expert'
    elif any(word in visible_content for word in ['dataset', 'statistics', 'analytics', 'correlation', 'regression']):
        return 'data_expert'
    elif any(word in visible_content for word in ['marketing', 'campaign', 'brand', 'customer', 'engagement']):
        return 'marketing_expert'
    elif any(word in visible_content for word in ['research', 'study', 'analysis', 'hypothesis', 'methodology']):
        return 'research_expert'
    elif any(word in visible_content for word in ['design', 'ui', 'ux', 'interface', 'user experience']):
        return 'design_expert'
    elif any(word in visible_content for word in ['legal', 'contract', 'compliance', 'regulation', 'policy']):
        return 'legal_expert'
    elif any(word in visible_content for word in ['strategy', 'planning', 'roadmap', 'goals', 'objectives']):
        return 'strategy_expert'
    elif any(word in visible_content for word in ['project', 'timeline', 'milestone', 'deliverable', 'scope']):
        return 'project_expert'
    elif any(word in visible_content for word in ['sales', 'leads', 'prospects', 'pipeline', 'conversion']):
        return 'sales_expert'
    else:
        return 'universal_expert'  # Can handle anything