"""
Maximally Helpful AI Assistant Engine - Immediate Contextual Assistance

This engine analyzes raw observation transcription data to provide immediate,
completed work based on what the user is currently doing. Unlike traditional
suggestion systems, this engine ALWAYS finds ways to help by generating
actual deliverables that users can immediately use.

Key Features:
- Triggers on every observation with extreme detail extraction
- Generates completed work, not just suggestions
- Uses intelligent content generation executors
- Provides "Click to see results" workflow
- Always attempts to help in some way (maximal helpfulness)
- Integrates with existing SSE system for real-time delivery
"""

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

        Args:
            observation_id: ID of the observation to analyze
            session: Database session
            
        Returns:
            List of suggestion dictionaries if successful, None if failed/rate limited
        """
        if not self._started:
            await self.start()
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Proactive engine triggered for observation {observation_id}")
            
            # Step 1: Rate limiting check (use separate rate limiter from Gumbo)
            rate_limiter = await get_rate_limiter()
            if not await rate_limiter.can_generate_suggestions():
                wait_time = await rate_limiter.get_wait_time()
                logger.info(f"⏰ Proactive engine rate limited, next available in {wait_time:.1f}s")
                
                self._suggestion_metrics["rate_limit_hits"] += 1
                return None
            
            # Step 2: Retrieve observation
            observation = await self._get_observation(session, observation_id)
            if not observation:
                logger.error(f"Observation {observation_id} not found")
                return None
            
            # Step 3: Analyze transcription content with AI and proposition intelligence
            suggestions = await self._analyze_transcription(observation.content, observation_id, session)
            
            if not suggestions:
                logger.info(f"No proactive suggestions generated for observation {observation_id}")
                return None
            
            # Step 4: Save suggestions to database
            suggestion_ids = await self._save_suggestions_to_database(
                suggestions, observation_id, session
            )
            
            # Step 5: Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(len(suggestions), processing_time)
            
            # Step 6: Broadcast via SSE (handled by caller)
            logger.info(f"✅ Proactive engine completed for observation {observation_id} in {processing_time:.2f}s")
            logger.info(f"Generated {len(suggestions)} proactive suggestions")
            
            return suggestions
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Proactive engine failed for observation {observation_id} after {processing_time:.2f}s: {e}")
            self._suggestion_metrics["errors"] += 1
            return None
    
    async def _get_observation(
        self, 
        session: AsyncSession, from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import existing GUM components
from ..models import Observation, Suggestion, Proposition
from ..suggestion_models import SuggestionData, SuggestionBatch
from .rate_limiter import get_rate_limiter
from sqlalchemy import select, desc

# Import enhanced analysis (universal expert imported dynamically to avoid circular imports)
from .enhanced_analysis import EnhancedTranscriptionAnalyzer, DetailedContext

# Import configuration
try:
    from ..config.proactive_config import get_config
except ImportError:
    # Fallback if config module not available
    def get_config():
        from dataclasses import dataclass
        @dataclass
        class FallbackConfig:
            max_tokens: int = 1200
            temperature: float = 0.05
            timeout_seconds: float = 30.0
            max_retries: int = 2
            retry_delay_seconds: float = 1.0
            min_specificity_score: int = 3  # Lowered from 6 to 3 for more permissive scoring
            processing_timeout_seconds: float = 5.0
            enable_context_parsing: bool = True
            enable_specificity_scoring: bool = True
            enable_retry_logic: bool = True
            enable_enhanced_validation: bool = True
            max_transcription_length: int = 2000
            max_visible_content_length: int = 500
        return FallbackConfig()

# Import unified AI client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)

# CAPABILITY REASONING PROMPT - Determines what AI can execute vs suggest
CAPABILITY_REASONING_PROMPT = """You are an AI assistant that can perform some tasks autonomously and suggest others to the user.

YOUR CAPABILITIES:
- ANY text generation: emails, messages, responses, rewrites, summaries, outlines, drafts, captions, posts, comments, scripts, letters, proposals, reports, etc.
- Data synthesis: research compilation, comparisons, analysis, organizing information, deck building guides, strategy recommendations
- Content creation: documents, notes, agendas, plans, lists, tables, structured output, game strategies, optimal configurations
- Text transformation: rewriting, improving, translating, formatting, editing

YOU CANNOT:
- Click, send, or confirm actions in external apps (games, email clients, browsers, messaging apps)
- Access or modify user's private environment (folders, files, configs, game interfaces)
- Make irreversible changes on behalf of the user
- Control user interfaces or navigate apps
- Actually send messages/emails (only draft them)

REASONING FRAMEWORK:
For every opportunity you identify, ask yourself:
1. Can I fully complete this task end-to-end with my current abilities?
2. If YES → Execute it autonomously 
3. If NO → Suggest the best next step and state what the human must do

TRANSCRIPTION DATA ANALYSIS:
{parsed_transcription}

CONTEXT EXTRACTION:
Current Application: {current_app}
Active Window/Document: {active_window}
Specific Content/Text: {visible_content}
User Actions Detected: {user_actions}
Time Context: {time_context}

TASK CLASSIFICATION:
For each task, provide:
- Category: [Research/Text/Action] 
- Capability: [Can execute/Needs human]
- Plan: [What I'll do / What human must do]

EXECUTION TYPES & REQUIRED PARAMETERS:
- research: {"topic": "what to research", "context": "current situation"}
- text_generation: {"task_type": "email|message|rewrite", "content": "text to work with", "context": "situation"}
- document_creation: {"document_type": "outline|plan", "topic": "what to create"}
- data_organization: {"data_content": "actual data to organize", "organization_type": "list|categories"}

CRITICAL: DO NOT USE "✅ Completed:" or "Completed:" in titles - these are reserved for actually executed tasks only.

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
  "tasks": [
    {{
      "title": "Hyper-specific action with exact details (max 60 chars) - NO ✅ or Completed prefixes",
      "description": "Detailed step-by-step instructions referencing specific content from transcription (max 400 chars)",
      "category": "Research|Text|Action",
      "capability": "Can execute|Needs human",
      "plan": "Detailed explanation of execution or what human must do",
      "execute": true|false,
      "execution_type": "research|text_generation|document_creation|data_organization",
      "execution_params": {{"topic": "specific topic", "context": "specific context"}},
      "rationale": "Specific evidence from transcription (max 250 chars)",
      "priority": "high|medium|low",
      "confidence": 1-10
    }}
  ]
}}

Always ask yourself: Can I fully complete this task end-to-end with my current abilities?
Never attempt actions outside your abilities.
Preserve the quality and specificity of suggestions - be detailed and actionable."""

# Enhanced Proactive AI with Proposition Intelligence - Extremely Strict JSON
ENHANCED_PROACTIVE_UNIVERSAL_EXPERT_PROMPT = """You are an unconstrained proactive AI assistant with universal expertise. You analyze current user activity combined with behavioral intelligence to provide immediate, completed work.

CURRENT ACTIVITY (CONCRETE DATA):
{current_transcription}

BEHAVIORAL INTELLIGENCE (USER PATTERNS):
{behavioral_propositions}

RECENT ACTIVITY CONTEXT (TIMELINE):
{recent_observations}

GROUNDING EVIDENCE (ANTI-HALLUCINATION):
{grounding_evidence}

UNCONSTRAINED CAPABILITIES:
You are able to but not limited to ANY form of assistance across ALL domains:
- Content creation, editing, optimization, generation, rewriting, improvement
- Technical assistance, debugging, code creation, system optimization, documentation
- Research, analysis, data processing, information synthesis, compilation
- Communication drafting, responding, meeting preparation, email composition
- Creative work, design assistance, ideation, concept development, framework creation
- Planning, organization, workflow optimization, task management, process improvement
- Problem-solving, decision support, strategy development, obstacle prevention
- Learning assistance, explanation, tutorial creation, knowledge transfer
- Business analysis, market research, competitive intelligence, strategic planning
- Academic support, research compilation, citation management, paper structuring
- Financial modeling, data analysis, reporting, forecasting, budgeting
- Legal document drafting, compliance analysis, contract review, policy creation
- Medical research synthesis, clinical summaries, health data analysis
- And ANY other form of assistance the context suggests or requires

ANTI-HALLUCINATION REQUIREMENTS (CRITICAL):
1. MUST reference specific evidence from current activity, behavioral patterns, or recent observations
2. MUST ground every suggestion in concrete data provided above
3. MUST use actual app names, file names, actions, patterns from the evidence
4. MUST NOT speculate beyond what's supported by the provided context
5. MUST reference exact elements from current transcription and behavioral intelligence
6. MUST connect suggestions to specific behavioral patterns mentioned in propositions

PROACTIVE INTELLIGENCE FRAMEWORK:
1. Current Context Analysis: What is happening RIGHT NOW? (Use specific current activity evidence)
2. Behavioral Pattern Application: What do their patterns reveal? (Reference specific propositions)
3. Next Step Prediction: What will they likely need next? (Based on evidence, not speculation)
4. Workflow Support Creation: What completed work would help? (Grounded in specific context)
5. Obstacle Prevention: What problems can we solve now? (Based on patterns and current activity)

EXTREMELY STRICT JSON OUTPUT FORMAT (NO DEVIATIONS ALLOWED):
{{
  "immediate_work": [
    {{
      "title": "I [specific action] based on [specific evidence reference]",
      "description": "Completed work description referencing specific evidence from current activity and behavioral patterns",
      "category": "completed_work",
      "rationale": "Specific evidence from current activity + behavioral intelligence that supports this assistance",
      "priority": "high",
      "confidence": 8,
      "has_completed_work": true,
      "completed_work": {{
        "content": "Actual completed work content",
        "content_type": "text",
        "preview": "Preview of completed work",
        "action_label": "Click to use specific deliverable",
        "metadata": {{
          "evidence_used": ["Specific evidence references that ground this suggestion"],
          "behavioral_patterns_applied": ["Specific propositions that informed this work"],
          "current_context_references": ["Specific details from current activity"],
          "anti_hallucination_check": "How this suggestion is grounded in provided evidence"
        }}
      }}
    }}
  ]
}}

CRITICAL JSON FORMATTING RULES:
- Use ONLY double quotes for strings
- NO trailing commas anywhere
- ALL string values must be properly escaped
- confidence MUST be integer 8, 9, or 10
- content_type MUST be exactly "text", "markdown", "json", "html", or "csv"
- priority MUST be exactly "high", "medium", or "low"
- category MUST be exactly "completed_work"
- has_completed_work MUST be exactly true
- ALL arrays must contain at least one string element
- NO undefined, null, or empty string values allowed

MANDATORY GROUNDING: Every suggestion must reference specific evidence from the provided context. No generic advice. Only assistance based on concrete data about current activity and established behavioral patterns."""

# Enhanced transcription parser for better context extraction
def parse_transcription_data(transcription_content: str) -> Dict[str, str]:
    """
    Parse transcription data to extract structured context for better AI analysis.
    
    Args:
        transcription_content: Raw transcription from observation.content
        
    Returns:
        Dictionary with parsed context elements
    """
    import re
    from datetime import datetime
    
    # Initialize context dictionary
    context = {
        "current_app": "Unknown",
        "active_window": "Unknown",
        "visible_content": "No specific content detected",
        "user_actions": "General activity",
        "time_context": datetime.now().strftime("%I:%M %p")
    }
    
    # Extract application name - handle multiple formats
    app_patterns = [
        r'Application[:\s]+([^\n]+)',  # "Application: Canva"
        r'User is in ([A-Za-z]+)',     # "User is in Canva"
        r'User in ([A-Za-z]+)',        # "User in VS Code"
        r'([A-Za-z]+) application',    # "Canva application"
        r'working in ([A-Za-z]+)',     # "working in Figma"
    ]
    
    for pattern in app_patterns:
        app_match = re.search(pattern, transcription_content, re.IGNORECASE)
        if app_match:
            context["current_app"] = app_match.group(1).strip()
            break
    
    # Extract window title/document name
    window_patterns = [
        r'Window Title[:\s]+([^\n]+)',
        r'Title[:\s]+([^\n]+)',
        r'Document[:\s]+([^\n]+)'
    ]
    for pattern in window_patterns:
        match = re.search(pattern, transcription_content, re.IGNORECASE)
        if match:
            context["active_window"] = match.group(1).strip()
            break
    
    # Extract visible text content
    content_patterns = [
        r'Visible Text Content[:\s]+([^]*?)(?=\n[A-Z]|$)',
        r'Text Content[:\s]+([^]*?)(?=\n[A-Z]|$)',
        r'Content[:\s]+([^]*?)(?=\n[A-Z]|$)'
    ]
    for pattern in content_patterns:
        match = re.search(pattern, transcription_content, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # Limit content length but preserve key information
            context["visible_content"] = content[:500] + "..." if len(content) > 500 else content
            break
    
    # Extract user actions/activity
    action_patterns = [
        r'User is ([^.]+)',
        r'Currently ([^.]+)',
        r'Activity[:\s]+([^\n]+)'
    ]
    for pattern in action_patterns:
        match = re.search(pattern, transcription_content, re.IGNORECASE)
        if match:
            context["user_actions"] = match.group(1).strip()
            break
    
    # Extract specific details (file names, line numbers, etc.)
    details = []
    
    # Look for file names
    file_matches = re.findall(r'([a-zA-Z0-9_-]+\.[a-zA-Z]{2,4})', transcription_content)
    if file_matches:
        details.append(f"Files: {', '.join(set(file_matches[:3]))}")
    
    # Look for line numbers
    line_matches = re.findall(r'line\s+(\d+)', transcription_content, re.IGNORECASE)
    if line_matches:
        details.append(f"Line: {line_matches[0]}")
    
    # Look for function/method names
    func_matches = re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)', transcription_content, re.IGNORECASE)
    if func_matches:
        details.append(f"Function: {func_matches[0]}")
    
    if details:
        context["user_actions"] += f" ({', '.join(details)})"
    
    return context


class ProactiveEngine:
    """
    Maximally helpful AI assistant engine that provides immediate contextual assistance
    based on raw observation transcription data with completed work generation.
    """
    
    def __init__(self, config: Optional[object] = None):
        """Initialize the maximally helpful AI assistant engine with configuration."""
        self.config = config or get_config()
        self.ai_client = None
        self._started = False
        self._startup_time = None
        
        # Initialize enhanced analysis engine
        self.enhanced_analyzer = EnhancedTranscriptionAnalyzer()
        
        # Enhanced metrics tracking
        self._suggestion_metrics = {
            "total_suggestions": 0,
            "total_completed_work": 0,
            "total_observations_processed": 0,
            "total_processing_time": 0.0,
            "last_suggestion_at": None,
            "rate_limit_hits": 0,
            "errors": 0,
            "timeouts": 0,
            "validation_failures": 0,
            "specificity_scores": [],  # Track quality over time
            "retry_attempts": 0,
            "successful_retries": 0,
            "executor_usage": {},  # Track which executors are used most
            "completed_work_types": {}  # Track types of completed work
        }
        
        logger.info(f"MaximallyHelpfulEngine initialized with enhanced analysis and intelligent executors")
    
    async def start(self):
        """Start the proactive engine with proper initialization."""
        if self._started:
            return
        
        try:
            # Initialize AI client
            self.ai_client = await get_unified_client()
            
            self._started = True
            self._startup_time = datetime.now(timezone.utc)
            
            logger.info("ProactiveEngine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start ProactiveEngine: {e}")
            raise
    
    async def stop(self):
        """Stop the proactive engine with proper cleanup."""
        if not self._started:
            return
        
        try:
            self._started = False
            logger.info("ProactiveEngine stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping ProactiveEngine: {e}")
    
    async def process_observation(
        self, 
        observation_id: int, 
        session: AsyncSession
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Main proactive engine entry point.
        
        Triggered when a new observation is created. Analyzes the raw transcription
        data to provide immediate, contextual suggestions.
        
        observation_id: int
    ) -> Optional[Observation]:
        """Retrieve the observation from database."""
        try:
            stmt = select(Observation).where(Observation.id == observation_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to retrieve observation {observation_id}: {e}")
            return None
    
    async def _analyze_transcription(self, transcription_content: str, observation_id: int = None, session: AsyncSession = None) -> List[Dict[str, Any]]:
        """
        Enhanced transcription analysis with proposition intelligence integration and strict JSON formatting.
        
        Args:
            transcription_content: Raw transcription data from observation.content
            observation_id: ID of the current observation for context retrieval
            session: Database session for proposition queries
            
        Returns:
            List of completed work and suggestion dictionaries
        """
        max_retries = self.config.max_retries if self.config.enable_retry_logic else 0
        retry_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                logger.info("🔍 Starting enhanced transcription analysis with proposition intelligence...")
                
                # Step 1: Get enhanced context with propositions (ONLY PATH)
                enhanced_context = await self._get_enhanced_context_with_propositions(
                    transcription_content, observation_id, session
                )
                
                logger.info(f"📊 Enhanced context: {enhanced_context['current_app']} | {len(enhanced_context['behavioral_propositions'])} propositions | {len(enhanced_context['recent_observations'])} observations")
                
                # Step 2: Generate proactive work with proposition intelligence (ONLY PATH)
                logger.info("🚀 Generating proactive work with proposition intelligence...")
                
                # Use ONLY enhanced prompt with proposition intelligence
                prompt = ENHANCED_PROACTIVE_UNIVERSAL_EXPERT_PROMPT.format(
                    current_transcription=enhanced_context['current_transcription'],
                    behavioral_propositions=enhanced_context['behavioral_propositions_formatted'],
                    recent_observations=enhanced_context['recent_observations_formatted'],
                    grounding_evidence=enhanced_context['grounding_evidence_formatted']
                )
                
                # Call AI with strict JSON requirements
                response_content = await asyncio.wait_for(
                    self.ai_client.text_completion(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1500,
                        temperature=0.05  # Very low temperature for strict JSON
                    ),
                    timeout=self.config.timeout_seconds
                )
                
                logger.debug(f"Raw AI response for enhanced proactive: {response_content[:500]}...")
                
                # Parse AI response with strict validation
                try:
                    response_data = self._parse_strict_json_response(response_content)
                    immediate_work_items = response_data.get("immediate_work", [])
                    
                    valid_suggestions = []
                    for work_item in immediate_work_items:
                        # Validate strict JSON structure
                        if self._validate_strict_json_structure(work_item):
                            # Create enhanced proactive suggestion
                            proactive_suggestion = {
                                "title": work_item.get("title", "I completed work for you"),
                                "description": work_item.get("description", "Immediate work completed"),
                                "category": "proactive_work",
                                "rationale": work_item.get("rationale", "Based on enhanced context analysis"),
                                "priority": work_item.get("priority", "high"),
                                "confidence": work_item.get("confidence", 8),
                                "has_completed_work": True,
                                "completed_work": work_item.get("completed_work", {}),
                                "source_app": enhanced_context.get('current_app', 'Unknown'),
                                "source_window": enhanced_context.get('active_window', 'Unknown'),
                                "generated_at": datetime.now(timezone.utc).isoformat(),
                                "executor_type": "enhanced_proactive_with_propositions",
                                "proposition_intelligence_used": True,
                                "grounding_score": self._calculate_grounding_score(work_item, enhanced_context)
                            }
                            valid_suggestions.append(proactive_suggestion)
                        else:
                            logger.warning(f"Invalid JSON structure in work item: {work_item}")
                    
                    logger.info(f"⚡ Generated {len(valid_suggestions)} enhanced proactive work items with proposition intelligence")
                    
                    if valid_suggestions:
                        return valid_suggestions
                    elif attempt < max_retries:
                        logger.warning(f"No valid suggestions on attempt {attempt + 1}, retrying...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.info("No valid suggestions generated after all attempts")
                        return []
                    
                except Exception as parse_error:
                    logger.error(f"Enhanced proactive parsing failed: {parse_error}")
                    logger.error(f"Response content: {response_content[:500]}...")
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return []
                
            except asyncio.TimeoutError:
                self._suggestion_metrics["timeouts"] += 1
                logger.warning(f"AI analysis timeout on attempt {attempt + 1}")
                if attempt < max_retries:
                    self._suggestion_metrics["retry_attempts"] += 1
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error("AI analysis failed after all retry attempts (timeout)")
                    return []
                    
            except Exception as e:
                self._suggestion_metrics["errors"] += 1
                logger.error(f"Enhanced proactive analysis failed on attempt {attempt + 1}: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception details: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                if attempt < max_retries:
                    self._suggestion_metrics["retry_attempts"] += 1
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error("Enhanced proactive analysis failed after all retry attempts")
                    return []
        
        return []
    
    async def _get_enhanced_context_with_propositions(
        self,
        transcription_content: str,
        observation_id: int = None,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get enhanced context combining current transcription with proposition intelligence.
        
        Args:
            transcription_content: Current transcription data
            observation_id: Current observation ID
            session: Database session for queries
            
        Returns:
            Dictionary with enhanced context including propositions and grounding evidence
        """
        try:
            # Parse current transcription for basic context
            parsed_context = parse_transcription_data(transcription_content)
            
            # Get recent propositions for behavioral intelligence
            recent_propositions = []
            recent_observations = []
            
            if session:
                # Get recent propositions (last 5 for behavioral patterns)
                props_stmt = (
                    select(Proposition)
                    .order_by(desc(Proposition.created_at))
                    .limit(5)
                )
                props_result = await session.execute(props_stmt)
                recent_propositions = props_result.scalars().all()
                
                # Get recent observations (last 8 for activity context, excluding current)
                obs_stmt = (
                    select(Observation)
                    .where(Observation.id != observation_id if observation_id else True)
                    .order_by(desc(Observation.created_at))
                    .limit(8)
                )
                obs_result = await session.execute(obs_stmt)
                recent_observations = obs_result.scalars().all()
            
            # Extract grounding evidence for anti-hallucination
            grounding_evidence = self._extract_grounding_evidence(
                transcription_content, recent_propositions, recent_observations
            )
            
            # Format behavioral propositions
            behavioral_propositions_formatted = self._format_behavioral_propositions(recent_propositions)
            
            # Format recent observations
            recent_observations_formatted = self._format_recent_observations(recent_observations)
            
            # Format grounding evidence
            grounding_evidence_formatted = self._format_grounding_evidence(grounding_evidence)
            
            return {
                'current_transcription': transcription_content,
                'current_app': parsed_context.get('current_app', 'Unknown'),
                'active_window': parsed_context.get('active_window', 'Unknown'),
                'behavioral_propositions': recent_propositions,
                'recent_observations': recent_observations,
                'behavioral_propositions_formatted': behavioral_propositions_formatted,
                'recent_observations_formatted': recent_observations_formatted,
                'grounding_evidence': grounding_evidence,
                'grounding_evidence_formatted': grounding_evidence_formatted
            }
            
        except Exception as e:
            logger.error(f"Failed to get enhanced context: {e}")
            # Return fallback context
            return {
                'current_transcription': transcription_content,
                'current_app': 'Unknown',
                'active_window': 'Unknown',
                'behavioral_propositions': [],
                'recent_observations': [],
                'behavioral_propositions_formatted': "No recent behavioral patterns available",
                'recent_observations_formatted': "No recent activity context available",
                'grounding_evidence': {},
                'grounding_evidence_formatted': "No grounding evidence available"
            }
    
    def _extract_grounding_evidence(
        self,
        transcription: str,
        propositions: List[Proposition],
        observations: List[Observation]
    ) -> Dict[str, List[str]]:
        """Extract concrete evidence for anti-hallucination grounding."""
        import re
        
        evidence = {
            'specific_apps': [],
            'specific_files': [],
            'specific_actions': [],
            'specific_patterns': [],
            'specific_timeframes': [],
            'specific_content': []
        }
        
        # Extract from current transcription
        transcription_lower = transcription.lower()
        
        # Extract app names
        app_patterns = ['canva', 'vscode', 'chrome', 'safari', 'figma', 'slack', 'discord', 'notion', 'obsidian']
        for app in app_patterns:
            if app in transcription_lower:
                evidence['specific_apps'].append(app.title())
        
        # Extract file references
        files = re.findall(r'([a-zA-Z0-9_-]+\.[a-zA-Z]{2,4})', transcription)
        evidence['specific_files'].extend(files[:5])  # Limit to 5
        
        # Extract actions
        actions = re.findall(r'(editing|creating|debugging|browsing|working on|opened|closed|clicked|typing)', transcription_lower)
        evidence['specific_actions'].extend(list(set(actions))[:5])  # Unique actions, limit to 5
        
        # Extract content snippets
        content_snippets = re.findall(r'"([^"]{10,50})"', transcription)
        evidence['specific_content'].extend(content_snippets[:3])  # Limit to 3
        
        # Extract from propositions
        for prop in propositions:
            if prop.text and prop.confidence and prop.confidence >= 7:
                evidence['specific_patterns'].append(prop.text[:100])  # Truncate long patterns
                
                # Extract timeframes from propositions
                timeframes = re.findall(r'(\d+[-\s]?\d*\s?(minute|hour|session|day))', prop.text.lower())
                evidence['specific_timeframes'].extend([f"{t[0]} {t[1]}" for t in timeframes])
        
        # Limit all evidence lists
        for key in evidence:
            evidence[key] = evidence[key][:5]  # Max 5 items per category
        
        return evidence
    
    def _format_behavioral_propositions(self, propositions: List[Proposition]) -> str:
        """Format propositions for AI prompt."""
        if not propositions:
            return "No recent behavioral patterns available"
        
        formatted = []
        for prop in propositions:
            confidence_str = f" (confidence: {prop.confidence})" if prop.confidence else ""
            formatted.append(f"- {prop.text}{confidence_str}")
        
        return "\n".join(formatted)
    
    def _format_recent_observations(self, observations: List[Observation]) -> str:
        """Format recent observations for AI prompt."""
        if not observations:
            return "No recent activity context available"
        
        formatted = []
        for obs in observations:
            # Truncate long observations
            content = obs.content[:150] + "..." if len(obs.content) > 150 else obs.content
            formatted.append(f"- {content}")
        
        return "\n".join(formatted)
    
    def _format_grounding_evidence(self, evidence: Dict[str, List[str]]) -> str:
        """Format grounding evidence for AI prompt."""
        if not any(evidence.values()):
            return "No grounding evidence available"
        
        formatted = []
        for category, items in evidence.items():
            if items:
                category_name = category.replace('_', ' ').title()
                formatted.append(f"{category_name}: {', '.join(items)}")
        
        return "\n".join(formatted)
    
    def _parse_strict_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with extremely strict validation."""
        try:
            # Clean up the response
            response = response.strip()
            logger.debug(f"Parsing strict JSON response: {response[:200]}...")
            
            # Try direct JSON parsing first
            try:
                data = json.loads(response)
                if "immediate_work" in data and isinstance(data["immediate_work"], list):
                    logger.debug("Direct strict JSON parsing successful")
                    return data
            except json.JSONDecodeError:
                logger.debug("Direct JSON parsing failed, trying extraction")
            
            # Extract JSON from markdown or text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    data = json.loads(json_str)
                    if "immediate_work" in data and isinstance(data["immediate_work"], list):
                        logger.debug("Extracted strict JSON parsing successful")
                        return data
                except json.JSONDecodeError as e:
                    logger.error(f"Extracted JSON parsing failed: {e}")
            
            # Fallback: create minimal valid structure
            logger.warning("All strict JSON parsing failed, creating fallback")
            return {"immediate_work": []}
            
        except Exception as e:
            logger.error(f"Strict JSON parsing error: {e}")
            return {"immediate_work": []}
    
    def _validate_strict_json_structure(self, work_item: Dict[str, Any]) -> bool:
        """Validate that work item meets strict JSON requirements."""
        try:
            # Check required fields
            required_fields = ["title", "description", "category", "rationale", "priority", "confidence", "has_completed_work", "completed_work"]
            if not all(field in work_item for field in required_fields):
                logger.warning(f"Work item missing required fields: {[f for f in required_fields if f not in work_item]}")
                return False
            
            # Validate field types and values
            if not isinstance(work_item["title"], str) or len(work_item["title"]) == 0:
                return False
            
            if not isinstance(work_item["description"], str) or len(work_item["description"]) == 0:
                return False
            
            if work_item["category"] != "completed_work":
                return False
            
            if not isinstance(work_item["confidence"], int) or work_item["confidence"] not in [8, 9, 10]:
                return False
            
            if work_item["priority"] not in ["high", "medium", "low"]:
                return False
            
            if work_item["has_completed_work"] is not True:
                return False
            
            # Validate completed_work structure
            completed_work = work_item.get("completed_work", {})
            if not isinstance(completed_work, dict):
                return False
            
            cw_required = ["content", "content_type", "preview", "action_label", "metadata"]
            if not all(field in completed_work for field in cw_required):
                return False
            
            if completed_work["content_type"] not in ["text", "markdown", "json", "html", "csv"]:
                return False
            
            # Validate metadata structure
            metadata = completed_work.get("metadata", {})
            if not isinstance(metadata, dict):
                return False
            
            metadata_required = ["evidence_used", "behavioral_patterns_applied", "current_context_references", "anti_hallucination_check"]
            if not all(field in metadata for field in metadata_required):
                return False
            
            # Validate that evidence arrays contain strings
            for field in ["evidence_used", "behavioral_patterns_applied", "current_context_references"]:
                if not isinstance(metadata[field], list) or len(metadata[field]) == 0:
                    return False
                if not all(isinstance(item, str) for item in metadata[field]):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating strict JSON structure: {e}")
            return False
    
    def _calculate_grounding_score(self, work_item: Dict[str, Any], enhanced_context: Dict[str, Any]) -> float:
        """Calculate how well grounded a suggestion is in provided evidence."""
        try:
            score = 0.0
            total_possible = 0.0
            
            # Check references to current transcription
            current_transcription = enhanced_context.get('current_transcription', '').lower()
            work_text = f"{work_item.get('title', '')} {work_item.get('description', '')}".lower()
            
            if current_transcription:
                transcription_words = set(current_transcription.split())
                work_words = set(work_text.split())
                overlap = len(transcription_words.intersection(work_words))
                if len(transcription_words) > 0:
                    score += (overlap / len(transcription_words)) * 0.4
                total_possible += 0.4
            
            # Check references to behavioral propositions
            propositions = enhanced_context.get('behavioral_propositions', [])
            if propositions:
                prop_references = 0
                for prop in propositions:
                    prop_words = set(prop.text.lower().split())
                    work_words = set(work_text.split())
                    if len(prop_words.intersection(work_words)) > 0:
                        prop_references += 1
                
                if len(propositions) > 0:
                    score += (prop_references / len(propositions)) * 0.3
                total_possible += 0.3
            
            # Check references to grounding evidence
            grounding_evidence = enhanced_context.get('grounding_evidence', {})
            if grounding_evidence:
                evidence_references = 0
                total_evidence = 0
                
                for category, items in grounding_evidence.items():
                    total_evidence += len(items)
                    for item in items:
                        if str(item).lower() in work_text:
                            evidence_references += 1
                
                if total_evidence > 0:
                    score += (evidence_references / total_evidence) * 0.3
                total_possible += 0.3
            
            return score / total_possible if total_possible > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating grounding score: {e}")
            return 0.0
    
    def _create_context_summary(self, detailed_context: DetailedContext) -> str:
        """Create a comprehensive context summary for AI prompt"""
        return f"""
BASIC CONTEXT:
- Application: {detailed_context.current_app}
- Window: {detailed_context.active_window}
- Content: {detailed_context.visible_content[:400]}
- Actions: {detailed_context.user_actions}

FILE CONTEXT:
- Files: {detailed_context.file_context.get('files_mentioned', [])}
- Types: {detailed_context.file_context.get('file_types', [])}
- Operations: {detailed_context.file_context.get('file_operations', [])}

CODE CONTEXT:
- Language: {detailed_context.code_context.get('programming_language', 'None')}
- Functions: {detailed_context.code_context.get('functions', [])}
- Classes: {detailed_context.code_context.get('classes', [])}
- Errors: {detailed_context.code_context.get('errors', [])}

DATA CONTEXT:
- Numbers: {detailed_context.data_context.get('numbers', [])[:10]}
- Percentages: {detailed_context.data_context.get('percentages', [])}
- Currencies: {detailed_context.data_context.get('currencies', [])}

WORKFLOW CONTEXT:
- Current Task: {detailed_context.workflow_context.get('current_task', 'Unknown')}
- Tools Used: {detailed_context.workflow_context.get('tools_used', [])}

COMMUNICATION CONTEXT:
- Emails: {detailed_context.communication_context.get('emails', [])}
- Subjects: {detailed_context.communication_context.get('subjects', [])}
- Type: {detailed_context.communication_context.get('communication_type', 'None')}

PATTERNS & INTENT:
- Content Patterns: {detailed_context.content_patterns}
- Intent Signals: {detailed_context.intent_signals}
- Actionable Items: {len(detailed_context.actionable_items)} items detected
"""
    
    def _validate_enhanced_suggestion(self, suggestion: Dict[str, Any], transcription: str, context: Dict[str, str]) -> bool:
        """
        Enhanced validation with context awareness and specificity scoring.
        
        Args:
            suggestion: Suggestion dictionary from AI
            transcription: Original transcription content
            context: Parsed context from transcription
            
        Returns:
            True if suggestion meets enhanced quality requirements
        """
        try:
            # Check required fields
            required_fields = ["title", "description", "category", "rationale"]
            if not all(field in suggestion for field in required_fields):
                logger.warning(f"Suggestion missing required fields: {[f for f in required_fields if f not in suggestion]}")
                return False
            
            # Check field lengths
            if len(suggestion["title"]) > 60:
                logger.warning(f"Suggestion title too long: {len(suggestion['title'])} chars")
                return False
            
            if len(suggestion["description"]) > 300:
                logger.warning(f"Suggestion description too long: {len(suggestion['description'])} chars")
                return False
            
            if len(suggestion["rationale"]) > 200:
                logger.warning(f"Suggestion rationale too long: {len(suggestion['rationale'])} chars")
                return False
            
            # Enhanced specificity validation
            specificity_score = self._calculate_specificity_score(suggestion, transcription, context)
            
            # Require minimum specificity score
            if specificity_score < 6:
                logger.warning(f"Suggestion specificity too low: {specificity_score}/10")
                return False
            
            # Store specificity score in suggestion
            suggestion["specificity_score"] = specificity_score
            
            logger.debug(f"Suggestion validated with specificity score: {specificity_score}/10")
            return True
            
        except Exception as e:
            logger.error(f"Error validating enhanced suggestion: {e}")
            return False
    
    def _calculate_specificity_score(self, suggestion: Dict[str, Any], transcription: str, context: Dict[str, str]) -> int:
        """
        Calculate specificity score for a suggestion based on context references.
        
        Returns:
            Score from 1-10 (10 = highly specific, 1 = generic)
        """
        import re
        
        score = 2  # Base score for having a suggestion
        
        description = suggestion["description"].lower()
        title = suggestion["title"].lower()
        combined_text = f"{title} {description}".lower()
        
        # Check for application references (+2 points)
        if context["current_app"].lower() != "unknown" and context["current_app"].lower() in combined_text:
            score += 2
        elif context["current_app"].lower() != "unknown":
            score += 1  # Partial credit for having app context
        
        # Check for file/document references (+2 points)
        if context["active_window"].lower() != "unknown":
            window_words = context["active_window"].lower().split()
            if any(word in combined_text for word in window_words if len(word) > 3):
                score += 2
            else:
                score += 1  # Partial credit for having window context
        
        # Check for specific numbers (line numbers, counts, etc.) (+1 point)
        if re.search(r'\b\d+\b', combined_text):
            score += 1
        
        # Check for specific content references (+1 point)
        if context["visible_content"] != "No specific content detected":
            content_words = context["visible_content"].lower().split()
            specific_matches = sum(1 for word in content_words if len(word) > 5 and word in combined_text)
            if specific_matches >= 1:  # Lowered from 2 to 1
                score += 1
        
        # Check for action verbs and concrete steps (+1 point)
        action_verbs = ["save", "create", "open", "close", "edit", "copy", "move", "delete", "run", "execute", "try", "use", "consider"]
        if any(verb in combined_text for verb in action_verbs):
            score += 1
        
        # Check for timing specificity (+1 point)
        timing_words = ["now", "immediately", "before", "after", "next", "current", "right", "soon"]
        if any(word in combined_text for word in timing_words):
            score += 1
        
        # Check for length and detail (+1 point)
        if len(description) > 30 or len(title) > 15:
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    def _validate_basic_suggestion(self, suggestion: Dict[str, Any]) -> bool:
        """
        Basic validation for suggestions when enhanced validation is disabled.
        
        Args:
            suggestion: Suggestion dictionary from AI
            
        Returns:
            True if suggestion meets basic quality requirements
        """
        try:
            # Check required fields
            required_fields = ["title", "description", "category", "rationale"]
            if not all(field in suggestion for field in required_fields):
                logger.warning("Suggestion missing required fields")
                return False
            
            # NOTE: Fake "Completed" titles are now handled by conversion logic in main processing
            # No longer rejecting them here since they get converted to executable tasks
            
            # Check field lengths
            if len(suggestion["title"]) > 60:
                logger.warning("Suggestion title too long")
                return False
            
            if len(suggestion["description"]) > 300:
                logger.warning("Suggestion description too long")
                return False
            
            if len(suggestion["rationale"]) > 200:
                logger.warning("Suggestion rationale too long")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating basic suggestion: {e}")
            return False
    
    def _validate_suggestion(self, suggestion: Dict[str, Any], transcription: str) -> bool:
        """
        Validate that a suggestion meets quality requirements.
        
        Args:
            suggestion: Suggestion dictionary from AI
            transcription: Original transcription content
            
        Returns:
            True if suggestion is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ["title", "description", "category", "rationale"]
            if not all(field in suggestion for field in required_fields):
                logger.warning("Suggestion missing required fields")
                return False
            
            # Check field lengths
            if len(suggestion["title"]) > 60:
                logger.warning("Suggestion title too long")
                return False
            
            if len(suggestion["description"]) > 300:
                logger.warning("Suggestion description too long")
                return False
            
            if len(suggestion["rationale"]) > 200:
                logger.warning("Suggestion rationale too long")
                return False
            
            # Check that suggestion references specific content from transcription
            description = suggestion["description"].lower()
            rationale = suggestion["rationale"].lower()
            transcription_lower = transcription.lower()
            
            # Look for specific references (numbers, names, specific terms)
            has_specific_reference = False
            
            # Check for numbers, specific names, or quoted content
            import re
            if (re.search(r'\b\d+\b', description) or  # Numbers
                re.search(r'\b[A-Z][a-z]+\b', suggestion["description"]) or  # Proper nouns
                any(word in transcription_lower for word in description.split() if len(word) > 6)):  # Specific terms
                has_specific_reference = True
            
            if not has_specific_reference:
                logger.warning("Suggestion lacks specific references to transcription content")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating suggestion: {e}")
            return False
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from AI with enhanced error handling for completed work."""
        try:
            # Clean up the response
            response = response.strip()
            logger.debug(f"Raw AI response: {response[:200]}...")
            
            # Method 1: Try direct JSON parsing first
            try:
                data = json.loads(response)
                if "immediate_work" in data:
                    logger.debug("Direct JSON parsing successful - immediate_work found")
                    return data
                elif "suggestions" in data:
                    logger.debug("Direct JSON parsing successful - suggestions found")
                    return data
                elif "tasks" in data:
                    logger.debug("Direct JSON parsing successful - tasks found")
                    return data
                elif "propositions" in data:
                    logger.debug("Direct JSON parsing successful - propositions found, converting to suggestions")
                    return self._convert_propositions_to_suggestions(data)
            except json.JSONDecodeError:
                logger.debug("Direct JSON parsing failed, trying markdown extraction")
            
            # Method 2: Enhanced markdown extraction for completed work
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
                            # Find the closing brace - handle truncated responses
                            end_idx = response.find(end_marker, json_start)
                            if end_idx >= 0:
                                json_str = response[json_start:end_idx].strip()
                            else:
                                # Handle truncated response - find last complete JSON structure
                                json_str = response[json_start:].strip()
                                # Find the last complete closing brace
                                brace_count = 0
                                last_complete_pos = -1
                                for i, char in enumerate(json_str):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            last_complete_pos = i + 1
                                            break
                                
                                if last_complete_pos > 0:
                                    json_str = json_str[:last_complete_pos]
                                
                            logger.debug(f"Extracted JSON from markdown: {json_str[:200]}...")
                            try:
                                data = json.loads(json_str)
                                if "immediate_work" in data:
                                    logger.debug("Markdown JSON parsing successful - immediate_work found")
                                    return data
                                elif "suggestions" in data:
                                    logger.debug("Markdown JSON parsing successful - suggestions found")
                                    return data
                                elif "tasks" in data:
                                    logger.debug("Markdown JSON parsing successful - tasks found")
                                    return data
                                elif "propositions" in data:
                                    logger.debug("Markdown JSON parsing successful - propositions found, converting to suggestions")
                                    return self._convert_propositions_to_suggestions(data)
                            except json.JSONDecodeError as e:
                                logger.debug(f"Markdown JSON parsing failed: {e}")
                                continue
            
            # Method 3: Enhanced brace matching for completed work
            start_idx = response.find('{')
            if start_idx >= 0:
                # Find the last complete JSON structure
                json_candidate = response[start_idx:]
                brace_count = 0
                last_complete_pos = -1
                
                for i, char in enumerate(json_candidate):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_complete_pos = i + 1
                            break
                
                if last_complete_pos > 0:
                    json_str = json_candidate[:last_complete_pos]
                    logger.debug(f"Extracted JSON by enhanced brace matching: {json_str[:200]}...")
                    try:
                        data = json.loads(json_str)
                        if "immediate_work" in data:
                            logger.debug("Enhanced brace matching successful - immediate_work found")
                            return data
                        elif "suggestions" in data:
                            logger.debug("Enhanced brace matching successful - suggestions found")
                            return data
                        elif "tasks" in data:
                            logger.debug("Enhanced brace matching successful - tasks found")
                            return data
                        elif "propositions" in data:
                            logger.debug("Enhanced brace matching successful - propositions found, converting to suggestions")
                            return self._convert_propositions_to_suggestions(data)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Enhanced brace matching failed: {e}")
            
            # Method 4: Fallback - create completed work from response text
            logger.warning("All JSON parsing methods failed, creating fallback completed work")
            logger.error(f"Failed response content: {response[:1000]}...")
            
            # Extract title from response if possible
            title_match = re.search(r'"title":\s*"([^"]+)"', response)
            description_match = re.search(r'"description":\s*"([^"]+)"', response)
            
            fallback_title = title_match.group(1) if title_match else "I analyzed your context and created helpful content"
            fallback_description = description_match.group(1) if description_match else "AI-generated analysis based on your current activity"
            
            return {
                "immediate_work": [
                    {
                        "title": fallback_title,
                        "description": fallback_description,
                        "category": "completed_work",
                        "rationale": "Fallback parsing from AI response",
                        "priority": "medium",
                        "confidence": 7,
                        "has_completed_work": True,
                        "completed_work": {
                            "content": response[:1000],  # Use raw response as content
                            "content_type": "text",
                            "preview": fallback_description,
                            "action_label": "View AI Analysis",
                            "metadata": {"parsing_method": "fallback"}
                        }
                    }
                ]
            }
                
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            logger.error(f"Response content: {response[:500]}...")
            return {"immediate_work": []}
    
    def _convert_propositions_to_suggestions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert propositions format to suggestions format."""
        suggestions = []
        for prop in data.get("propositions", []):
            suggestion = {
                "title": prop.get("proposition", "Suggestion")[:60],
                "description": f"Based on: {prop.get('reasoning', '')[:300]}",
                "category": "immediate_optimization",
                "rationale": prop.get("reasoning", "")[:200],
                "priority": "medium",
                "confidence": int(prop.get("confidence", 5)) if isinstance(prop.get("confidence"), str) else prop.get("confidence", 5)
            }
            suggestions.append(suggestion)
        return {"suggestions": suggestions}
    
    async def _save_suggestions_to_database(
        self,
        suggestions: List[Dict[str, Any]],
        observation_id: int,
        session: AsyncSession
    ) -> List[int]:
        """Save maximally helpful suggestions with completed work to database."""
        try:
            suggestion_ids = []
            batch_id = str(uuid.uuid4())
            
            for suggestion_data in suggestions:
                # Determine category based on whether it has completed work
                category = "completed_work" if suggestion_data.get("has_completed_work") else "proactive"
                
                # Create database record
                db_suggestion = Suggestion(
                    title=suggestion_data.get("title", "AI Assistance")[:200],
                    description=suggestion_data.get("description", "")[:1000],
                    category=category,
                    rationale=suggestion_data.get("rationale", "")[:500],
                    expected_utility=suggestion_data.get("confidence", 7) / 10.0,  # Convert to 0-1 scale
                    probability_useful=suggestion_data.get("confidence", 7) / 10.0,
                    trigger_proposition_id=None,  # Proactive suggestions don't have propositions
                    batch_id=batch_id,
                    delivered=False,  # Will be marked True when delivered via SSE
                    
                    # Completed work fields
                    has_completed_work=suggestion_data.get("has_completed_work", False),
                    executor_type=suggestion_data.get("executor_type", "unknown")
                )
                
                # Add completed work data if present
                if suggestion_data.get("has_completed_work") and suggestion_data.get("completed_work"):
                    completed_work = suggestion_data["completed_work"]
                    db_suggestion.completed_work_content = completed_work.get("content", "")
                    db_suggestion.completed_work_type = completed_work.get("content_type", "text")
                    db_suggestion.completed_work_preview = completed_work.get("preview", "")[:500]
                    db_suggestion.action_label = completed_work.get("action_label", "View Results")[:100]
                    db_suggestion.work_metadata = json.dumps(completed_work.get("metadata", {}))
                
                session.add(db_suggestion)
                await session.flush()  # Get the ID
                suggestion_ids.append(db_suggestion.id)
            
            await session.commit()
            
            completed_work_count = sum(1 for s in suggestions if s.get("has_completed_work"))
            logger.info(f"Saved {len(suggestion_ids)} suggestions to database ({completed_work_count} with completed work)")
            return suggestion_ids
            
        except Exception as e:
            logger.error(f"Failed to save suggestions to database: {e}")
            await session.rollback()
            return []
    
    def _update_metrics(self, suggestion_count: int, processing_time: float):
        """Update internal metrics tracking."""
        self._suggestion_metrics["total_suggestions"] += suggestion_count
        self._suggestion_metrics["total_observations_processed"] += 1
        self._suggestion_metrics["total_processing_time"] += processing_time
        self._suggestion_metrics["last_suggestion_at"] = datetime.now(timezone.utc)
    
    async def _execute_autonomous_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute autonomous task using task executors"""
        try:
            # Import task executors
            from .task_executors import execute_autonomous_task
            
            execution_type = task.get("execution_type")
            execution_params = task.get("execution_params", {})
            
            if not execution_type:
                logger.error("Task missing execution_type")
                return None
            
            # Add task context to params
            execution_params.update({
                "title": task.get("title", ""),
                "description": task.get("description", ""),
                "context": task.get("rationale", "")
            })
            
            # Execute the task
            result = await execute_autonomous_task(execution_type, execution_params)
            
            if result.success:
                # Convert to suggestion format with execution data
                return {
                    "title": f"✅ Completed: {task.get('title', 'Task')}",
                    "description": f"I {task.get('description', 'completed a task')}",
                    "category": "autonomous_action", 
                    "rationale": task.get("rationale", ""),
                    "priority": task.get("priority", "medium"),
                    "confidence": task.get("confidence", 7),
                    "executed": True,
                    "execution_result": json.dumps(result.result_data),
                    "execution_status": result.status,
                    "execution_time_seconds": result.execution_time
                }
            else:
                logger.error(f"Task execution failed: {result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing autonomous task: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current engine health status."""
        if not self._started:
            return {
                "status": "stopped",
                "uptime_seconds": 0,
                "metrics": self._suggestion_metrics
            }
        
        uptime = (datetime.now(timezone.utc) - self._startup_time).total_seconds()
        
        # Calculate average processing time
        avg_processing_time = 0.0
        if self._suggestion_metrics["total_observations_processed"] > 0:
            avg_processing_time = (
                self._suggestion_metrics["total_processing_time"] / 
                self._suggestion_metrics["total_observations_processed"]
            )
        
        status = "healthy"
        if avg_processing_time > 5.0:  # Slow processing
            status = "degraded"
        
        return {
            "status": status,
            "uptime_seconds": uptime,
            "metrics": {
                **self._suggestion_metrics,
                "average_processing_time_seconds": avg_processing_time
            }
        }


# Global engine instance (singleton pattern)
_global_proactive_engine: Optional[ProactiveEngine] = None


async def get_proactive_engine() -> ProactiveEngine:
    """
    Get the global proactive engine instance.
    
    Returns:
        Initialized ProactiveEngine instance
    """
    global _global_proactive_engine
    
    if _global_proactive_engine is None:
        _global_proactive_engine = ProactiveEngine()
        await _global_proactive_engine.start()
    
    return _global_proactive_engine


async def trigger_proactive_suggestions(observation_id: int, session: AsyncSession) -> Optional[List[Dict[str, Any]]]:
    """
    Convenience function to trigger proactive suggestions.
    
    This is the main entry point called from gum/gum.py when a new observation
    is created.
    
    Args:
        observation_id: ID of the observation to analyze
        session: Database session
        
    Returns:
        List of suggestion dictionaries if successful, None if failed
    """
    try:
        engine = await get_proactive_engine()
        return await engine.process_observation(observation_id, session)
    except Exception as e:
        logger.error(f"Failed to trigger proactive suggestions: {e}")
        return None


async def shutdown_proactive_engine():
    """Shutdown the global proactive engine (for cleanup)."""
    global _global_proactive_engine
    
    if _global_proactive_engine is not None:
        await _global_proactive_engine.stop()
        _global_proactive_engine = None
        logger.info("Global ProactiveEngine shutdown complete")