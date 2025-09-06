"""
Proactive Suggestion Engine - Immediate Contextual Suggestions

This engine analyzes raw observation transcription data to provide immediate,
actionable suggestions based on what the user is currently doing. Unlike the
Gumbo engine which waits for high-confidence behavioral patterns, this engine
triggers on EVERY observation to provide instant contextual assistance.

Key Features:
- Triggers on every observation (not just high-confidence propositions)
- Uses the same observation.content field that propositions use
- Provides immediate suggestions (2-3 seconds after activity)
- Saves to same Suggestion table with category="proactive"
- Integrates with existing SSE system for real-time delivery
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import existing GUM components
from ..models import Observation, Suggestion
from ..suggestion_models import SuggestionData, SuggestionBatch
from .rate_limiter import get_rate_limiter

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

# Enhanced Proactive AI Prompt with better transcription data extraction
PROACTIVE_ANALYSIS_PROMPT = """You are a hyper-observant productivity analyst that analyzes user activity transcriptions to provide extremely specific, data-driven suggestions. You notice patterns, inefficiencies, and opportunities that the user might miss.

TRANSCRIPTION DATA ANALYSIS:
{parsed_transcription}

CONTEXT EXTRACTION:
Current Application: {current_app}
Active Window/Document: {active_window}
Specific Content/Text: {visible_content}
User Actions Detected: {user_actions}
Time Context: {time_context}

DEEP ANALYSIS FRAMEWORK:
1. **Pattern Recognition**: What patterns do you see in their current activity? (file types, tools, workflows, timing, communication, decision-making)
2. **Specific Evidence**: What exact text, code, filenames, data, messages, or content are they working with?
3. **Workflow Analysis**: What stage are they at? What's the next logical step?
4. **Efficiency Opportunities**: What could be optimized, automated, or streamlined?
5. **Context Switching**: Are they jumping between tasks unnecessarily?
6. **Resource Utilization**: Are they using the right tools for the job?
7. **Error Prevention**: What mistakes are they likely to make based on current activity?
8. **Communication Gaps**: Are there people they should contact, messages to respond to, or updates to share?
9. **Decision Points**: Are there choices they need to make or information they need to gather?
10. **Time Management**: Are there deadlines, meetings, or time-sensitive tasks they should be aware of?
11. **Health & Wellbeing**: Are there breaks, meals, or self-care they should consider?
12. **Learning Opportunities**: Are there skills, knowledge, or resources they could benefit from?

PROACTIVE SUGGESTION REQUIREMENTS:
- MUST ONLY reference what is EXPLICITLY stated in the transcription - no assumptions or inferences
- MUST provide concrete, executable steps with specific commands or actions
- MUST explain the reasoning based on EXACT content from the transcription
- MUST consider their current workflow state and what they'll need next
- MUST be actionable within 5-30 minutes
- MUST be specific enough that another person could follow the exact steps
- MUST identify CONCRETE, SPECIFIC items that are actually mentioned (e.g., "Close the 3 GitHub tabs for 'Python validation' and 'VS Code debugging'" NOT "Close any distractions")
- MUST count and name specific things that are explicitly stated (e.g., "2 extra terminal windows", "3 unread emails from John", "5 Python files in gum/services/")
- MUST avoid vague categories like "distractions", "files", "tabs" - be specific about WHAT exactly
- MUST NOT make assumptions about what the user is doing beyond what's explicitly stated
- MUST NOT infer activities, deadlines, or context not mentioned in the transcription

EXAMPLES OF GOOD SUGGESTIONS:

**CODING & DEVELOPMENT:**
❌ BAD: "Consider organizing your files better"
✅ GOOD: "I noticed you're editing line 156 in proactive_engine.py and have 3 similar validation methods. Create a base class ValidationMixin to reduce the 47 lines of duplicate code I see in _validate_suggestion, _validate_enhanced_suggestion, and _validate_basic_suggestion methods."

**COMMUNICATION & COLLABORATION:**
❌ BAD: "Check your messages"
✅ GOOD: "I see you have 12 unread emails from your team in the background. The 3 from 'alerts@system.com' are likely automated and can be archived, while the 2 from 'sarah@company.com' marked 'URGENT' should be prioritized - they're from 2 hours ago and match your current debugging context."

**TIME MANAGEMENT & SCHEDULING:**
❌ BAD: "Check your calendar"
✅ GOOD: "You have a team standup in 15 minutes at 2:00 PM. Send a quick Slack message to John about the proactive engine progress before the meeting so he's updated on your debugging session."

**HEALTH & WELLBEING:**
❌ BAD: "Take a break"
✅ GOOD: "You've been debugging for 2 hours straight. Take a 10-minute walk now - your eyes are likely strained from staring at the _validate_suggestion method code, and fresh air will help you spot the JSON parsing issue."

**LEARNING & SKILLS:**
❌ BAD: "Learn something new"
✅ GOOD: "The validation logic you're debugging could benefit from Python's dataclasses. Check the 'Python dataclasses validation patterns' tab you have open - it shows exactly the approach you need for the _validate_basic_suggestion method."

**DECISION MAKING:**
❌ BAD: "Make a decision"
✅ GOOD: "You're choosing between 3 different JSON parsing approaches. The 'robust parsing' example in your GitHub tab shows the most reliable method for handling the markdown-wrapped responses you're seeing in the logs."

**WORKSPACE OPTIMIZATION:**
❌ BAD: "Close any distractions"
✅ GOOD: "Close the 3 GitHub documentation tabs for 'Python validation patterns' and 'VS Code debugging' that are open but not relevant to your current _validate_suggestion method debugging."

CRITICAL INSTRUCTION:
Only suggest actions based on what is EXPLICITLY stated in the transcription. Do not make assumptions about what the user is doing, what they need, or what their goals are beyond what is clearly visible in the transcription data. If the transcription only mentions "47 unread emails", don't assume they are "urgent team emails" or "performance review emails" unless specifically stated.

OUTPUT FORMAT:so
Return a JSON object with this exact structure:
{
  "suggestions": [
    {
      "title": "Hyper-specific action with exact details (max 60 chars)",
      "description": "Detailed step-by-step instructions referencing specific files, line numbers, or content from the transcription. Include exact commands, filenames, or actions. (max 400 chars)",
      "category": "immediate_optimization|productivity_boost|error_prevention|workflow_improvement|time_saving|code_optimization|file_management|communication|health_wellbeing|learning|decision_making|scheduling",
      "rationale": "Specific evidence from the transcription that supports this suggestion, including file names, line numbers, or observable patterns (max 250 chars)",
      "priority": "high|medium|low",
      "confidence": 1-10
    }
  ]
}"""

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
    
    # Extract application name
    app_match = re.search(r'Application[:\s]+([^\n]+)', transcription_content, re.IGNORECASE)
    if app_match:
        context["current_app"] = app_match.group(1).strip()
    
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
    Proactive suggestion engine that provides immediate contextual suggestions
    based on raw observation transcription data.
    """
    
    def __init__(self, config: Optional[object] = None):
        """Initialize the proactive engine with configuration."""
        self.config = config or get_config()
        self.ai_client = None
        self._started = False
        self._startup_time = None
        
        # Enhanced metrics tracking
        self._suggestion_metrics = {
            "total_suggestions": 0,
            "total_observations_processed": 0,
            "total_processing_time": 0.0,
            "last_suggestion_at": None,
            "rate_limit_hits": 0,
            "errors": 0,
            "timeouts": 0,
            "validation_failures": 0,
            "specificity_scores": [],  # Track quality over time
            "retry_attempts": 0,
            "successful_retries": 0
        }
        
        logger.info(f"ProactiveEngine initialized with config: specificity_threshold={self.config.min_specificity_score}")
    
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
            
            # Step 3: Analyze transcription content with AI
            suggestions = await self._analyze_transcription(observation.content)
            
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
        session: AsyncSession, 
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
    
    async def _analyze_transcription(self, transcription_content: str) -> List[Dict[str, Any]]:
        """
        Enhanced transcription analysis with structured context extraction and retry logic.
        
        Args:
            transcription_content: Raw transcription data from observation.content
            
        Returns:
            List of suggestion dictionaries
        """
        max_retries = self.config.max_retries if self.config.enable_retry_logic else 0
        retry_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                # Parse transcription data for structured context (if enabled)
                if self.config.enable_context_parsing:
                    parsed_context = parse_transcription_data(transcription_content)
                    
                    # Use string replacement instead of format() to avoid curly brace issues
                    prompt = PROACTIVE_ANALYSIS_PROMPT.replace('{parsed_transcription}', transcription_content[:self.config.max_transcription_length])
                    prompt = prompt.replace('{current_app}', parsed_context["current_app"])
                    prompt = prompt.replace('{active_window}', parsed_context["active_window"])
                    prompt = prompt.replace('{visible_content}', parsed_context["visible_content"][:self.config.max_visible_content_length])
                    prompt = prompt.replace('{user_actions}', parsed_context["user_actions"])
                    prompt = prompt.replace('{time_context}', parsed_context["time_context"])
                else:
                    # Fallback to simple prompt
                    parsed_context = {"current_app": "Unknown", "active_window": "Unknown"}
                    prompt = f"Analyze this transcription and provide 1-3 specific suggestions: {transcription_content[:self.config.max_transcription_length]}"
                
                logger.info(f"🔍 Enhanced context extracted: {parsed_context['current_app']} | {parsed_context['active_window']}")
                
                # Call AI for suggestion generation with configurable settings
                response_content = await asyncio.wait_for(
                    self.ai_client.text_completion(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature
                    ),
                    timeout=self.config.timeout_seconds
                )
                
                logger.debug(f"Raw AI response for proactive suggestions: {response_content[:500]}...")
                
                # Parse JSON response
                try:
                    suggestions_data = self._parse_json_response(response_content)
                    suggestions = suggestions_data.get("suggestions", [])
                    logger.debug(f"Parsed {len(suggestions)} suggestions from AI response")
                    
                    if not suggestions:
                        logger.warning("No suggestions found in AI response")
                        continue
                        
                except Exception as parse_error:
                    logger.error(f"JSON parsing failed: {parse_error}")
                    logger.error(f"Response content: {response_content[:500]}...")
                    continue
                
                # Convert confidence to int if it's a string
                for suggestion in suggestions:
                    if "confidence" in suggestion and isinstance(suggestion["confidence"], str):
                        try:
                            suggestion["confidence"] = int(suggestion["confidence"])
                        except ValueError:
                            suggestion["confidence"] = 5  # Default fallback
                
                # Enhanced validation with context awareness (if enabled)
                valid_suggestions = []
                for suggestion in suggestions:
                    if self.config.enable_enhanced_validation:
                        if self._validate_enhanced_suggestion(suggestion, transcription_content, parsed_context):
                            # Add enhanced metadata
                            suggestion["source_app"] = parsed_context["current_app"]
                            suggestion["source_window"] = parsed_context["active_window"]
                            suggestion["generated_at"] = datetime.now(timezone.utc).isoformat()
                            valid_suggestions.append(suggestion)
                        else:
                            self._suggestion_metrics["validation_failures"] += 1
                    else:
                        # Basic validation only
                        if self._validate_basic_suggestion(suggestion):
                            valid_suggestions.append(suggestion)
                
                if valid_suggestions:
                    logger.info(f"💡 Generated {len(valid_suggestions)} enhanced proactive suggestions")
                    return valid_suggestions
                elif attempt < max_retries:
                    logger.warning(f"No valid suggestions on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.info("No valid suggestions generated after all attempts")
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
                logger.error(f"Proactive transcription analysis failed on attempt {attempt + 1}: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception details: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                if attempt < max_retries:
                    self._suggestion_metrics["retry_attempts"] += 1
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error("Proactive transcription analysis failed after all retry attempts")
                    return []
        
        return []
    
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
        """Parse JSON response from AI with comprehensive error handling."""
        try:
            # Clean up the response
            response = response.strip()
            logger.debug(f"Raw AI response: {response[:200]}...")
            
            # Method 1: Try direct JSON parsing first
            try:
                data = json.loads(response)
                if "suggestions" in data:
                    logger.debug("Direct JSON parsing successful - suggestions found")
                    return data
                elif "propositions" in data:
                    logger.debug("Direct JSON parsing successful - propositions found, converting to suggestions")
                    return self._convert_propositions_to_suggestions(data)
            except json.JSONDecodeError:
                logger.debug("Direct JSON parsing failed, trying markdown extraction")
            
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
                                logger.debug(f"Extracted JSON from markdown: {json_str[:200]}...")
                                try:
                                    data = json.loads(json_str)
                                    if "suggestions" in data:
                                        logger.debug("Markdown JSON parsing successful - suggestions found")
                                        return data
                                    elif "propositions" in data:
                                        logger.debug("Markdown JSON parsing successful - propositions found, converting to suggestions")
                                        return self._convert_propositions_to_suggestions(data)
                                except json.JSONDecodeError as e:
                                    logger.debug(f"Markdown JSON parsing failed: {e}")
                                    continue
            
            # Method 3: Find JSON by looking for opening and closing braces
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                logger.debug(f"Extracted JSON by brace matching: {json_str[:200]}...")
                try:
                    data = json.loads(json_str)
                    if "suggestions" in data:
                        logger.debug("Brace matching JSON parsing successful - suggestions found")
                        return data
                    elif "propositions" in data:
                        logger.debug("Brace matching JSON parsing successful - propositions found, converting to suggestions")
                        return self._convert_propositions_to_suggestions(data)
                except json.JSONDecodeError as e:
                    logger.debug(f"Brace matching JSON parsing failed: {e}")
            
            # If all methods fail
            logger.error("All JSON parsing methods failed")
            logger.error(f"Response content: {response[:500]}...")
            return {"suggestions": []}
                
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            logger.error(f"Response content: {response[:500]}...")
            return {"suggestions": []}
    
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
        """Save proactive suggestions to database."""
        try:
            suggestion_ids = []
            batch_id = str(uuid.uuid4())
            
            for suggestion_data in suggestions:
                # Create database record with category="proactive"
                db_suggestion = Suggestion(
                    title=suggestion_data.get("title", "Proactive Suggestion")[:200],
                    description=suggestion_data.get("description", "")[:1000],
                    category="proactive",  # Key differentiator from Gumbo suggestions
                    rationale=suggestion_data.get("rationale", "")[:500],
                    expected_utility=suggestion_data.get("confidence", 5) / 10.0,  # Convert to 0-1 scale
                    probability_useful=suggestion_data.get("confidence", 5) / 10.0,
                    trigger_proposition_id=None,  # Proactive suggestions don't have propositions
                    batch_id=batch_id,
                    delivered=False  # Will be marked True when delivered via SSE
                )
                
                session.add(db_suggestion)
                await session.flush()  # Get the ID
                suggestion_ids.append(db_suggestion.id)
            
            await session.commit()
            
            logger.info(f"Saved {len(suggestion_ids)} proactive suggestions to database")
            return suggestion_ids
            
        except Exception as e:
            logger.error(f"Failed to save proactive suggestions to database: {e}")
            await session.rollback()
            return []
    
    def _update_metrics(self, suggestion_count: int, processing_time: float):
        """Update internal metrics tracking."""
        self._suggestion_metrics["total_suggestions"] += suggestion_count
        self._suggestion_metrics["total_observations_processed"] += 1
        self._suggestion_metrics["total_processing_time"] += processing_time
        self._suggestion_metrics["last_suggestion_at"] = datetime.now(timezone.utc)
    
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