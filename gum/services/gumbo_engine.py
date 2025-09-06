"""
Gumbo Engine - Core Intelligent Suggestion System

Production-grade implementation of the Gumbo algorithm for automated,
context-aware suggestion generation based on user behavior patterns.

Algorithm Flow:
1. Automatic Trigger: New proposition with confidence ≥ 8
2. Contextual Retrieval: LLM-based semantic similarity search
3. Multi-Candidate Generation: Generate 5 suggestions using context
4. Mixed-Initiative Filtering: Score suggestions using Expected Utility
5. Rate Limiting: Token bucket prevents spam
6. Real-Time Push: SSE delivery to frontend
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func, literal_column
from sqlalchemy.orm import selectinload

# Import existing GUM components
from ..db_utils import search_propositions_bm25
from ..models import Proposition, Observation, observation_proposition
from ..suggestion_models import (
    SuggestionData, SuggestionBatch, UtilityScores, 
    ContextualProposition, ContextRetrievalResult,
    SSEEvent, SSEEventType
)
from .rate_limiter import get_rate_limiter

# Import unified AI client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)


# Production-grade prompts for Gumbo algorithm
CONTEXTUAL_RETRIEVAL_PROMPT = """You are a behavioral pattern AND content analyst. Analyze the trigger proposition and generate a semantic search query to find related behavioral insights and content.

TRIGGER PROPOSITION:
"{trigger_text}"

REASONING: {trigger_reasoning}

Generate a focused search query (2-4 keywords) that will find related propositions with relevant behavioral patterns and content context.

Return only the search query, no explanation."""

MULTI_CANDIDATE_GENERATION_PROMPT = """You are a HYPER-SPECIFIC AI assistant that MUST provide concrete, actionable solutions based on behavioral patterns + current screen activity + raw observation data. NO GENERIC ADVICE ALLOWED.

CURRENT BEHAVIORAL TRIGGER:
The user just demonstrated: "{trigger_text}"

RELATED BEHAVIORAL PATTERNS (Multi-Context):
{related_context}

RAW OBSERVATION DATA (Concrete Content Details):
{raw_observations}

CURRENT SCREEN CONTEXT:
{current_screen_context}

CRITICAL RULES - VIOLATION MEANS REJECTION:
1. **MUST reference specific apps/tools** you see in screen context (Canva, Instagram, Clash Royale, etc.)
2. **MUST mention specific projects/content** (Sequestron, DECA events, specific Instagram profiles, etc.)
3. **MUST connect to behavioral patterns** (short gaming sessions, iterative design work, multiple profile management, etc.)
4. **MUST reference specific content from observations** (exact text, documents, UI elements mentioned)
5. **MUST provide immediate, actionable solutions** (not generic productivity tips)
6. **MUST predict next 5-30 minute needs** based on current activity + patterns

ANTICIPATION FRAMEWORK:
You must PREDICT the user's next needs by analyzing:

1. **Current State Analysis**: What specific app/project is the user currently using? What are they doing RIGHT NOW?
2. **Pattern Progression**: What typically happens after this specific behavior based on their history?
3. **Timing Predictions**: When will they likely need help next based on their patterns?
4. **Workflow Anticipation**: What specific tools/resources will they need for their current project?
5. **Content Prediction**: What specific information will they search for based on their current activity?
6. **Obstacle Prevention**: What specific problems can you prevent based on their behavioral patterns?
7. **Current vs. Optimal Assessment**: Is what they're currently using optimal? What specific changes would improve their current situation?

CRITICAL INSTRUCTION: You MUST provide specific, actionable solutions that reference their current activity, behavioral patterns, AND specific content from the raw observation data. Use the exact text, document names, and UI elements mentioned in the observations to make suggestions hyper-specific. 

IMPORTANT: Connect multiple behavioral patterns and observations to create rich, contextual suggestions. Combine high-confidence patterns with medium/low-confidence context to understand the complete user situation. NO GENERIC ADVICE.

ANTICIPATION REQUIREMENTS:
1. **Analyze Current State**: What specific app/project is the user currently using? Is it optimal?
2. **Predict Next Steps**: What will the user need in the next 5-30 minutes based on their patterns?
3. **Prevent Future Problems**: What specific obstacles can you eliminate now based on their history?
4. **Prepare Resources**: What specific tools/info will they need soon for their current project?
5. **Timing Optimization**: When should they do what for maximum efficiency based on their patterns?
6. **Pattern-Based Prediction**: Use behavioral history to predict future needs
7. **Current Optimization**: What specific changes would improve their current situation RIGHT NOW?

ABSOLUTELY FORBIDDEN SUGGESTIONS (Too Generic):
❌ "Utilize deck building guides" (generic advice)
❌ "Research techniques for improvement" (generic research)
❌ "Look up best practices" (generic best practices)
❌ "Find helpful tools" (generic tool discovery)
❌ "Schedule breaks to enhance focus" (generic productivity)
❌ "Check internet stability" (generic troubleshooting)
❌ "Use elixir wisely" (generic gaming advice)
❌ "Enable collaboration features" (generic feature suggestion)

REQUIRED HYPER-SPECIFIC FORMAT:
Each suggestion MUST:
- Reference the specific app/project they're currently using
- Connect to their specific behavioral patterns
- Reference specific content from observation data (exact text, documents, UI elements)
- Predict what they'll need next based on their history
- Provide specific, actionable solutions they can do RIGHT NOW
- Prevent specific problems based on their patterns
- Optimize timing based on their behavioral insights

TASK: Generate 5 HYPER-SPECIFIC suggestions that:
- Reference specific apps/projects from current screen activity
- Connect to specific behavioral patterns from their history
- Predict future needs based on current activity + patterns
- Provide specific solutions they can implement RIGHT NOW
- Prevent specific problems based on their patterns
- Include specific resources/tools they'll need soon

SUGGESTION CATEGORIES:
- predictive_solution: Anticipates needs 5-30 minutes ahead
- obstacle_prevention: Prevents specific problems based on patterns
- resource_preparation: Prepares specific tools/info they'll need soon
- timing_optimization: Schedules tasks based on behavioral patterns
- workflow_anticipation: Predicts next workflow steps

Return JSON in this exact format:
{{
  "suggestions": [
    {{
      "title": "Hyper-specific title referencing current activity (max 60 chars)",
      "description": "Specific solution based on current activity + behavioral patterns (max 300 chars)",
      "category": "predictive_solution|obstacle_prevention|resource_preparation|timing_optimization|workflow_anticipation",
      "rationale": "Evidence-based prediction using specific behavioral patterns + current activity (max 200 chars)",
      "priority": "high|medium|low"
    }},
    ...
  ]
}}

EXAMPLES OF HYPER-SPECIFIC SUGGESTIONS USING OBSERVATION DATA:
❌ "Use elixir wisely in Clash Royale"
✅ "You're in a Clash Royale match. Based on your pattern of losing to air units, you'll need a counter-deck in the next 2-3 games. Here's your anti-air deck: Giant + Witch + Valkyrie + Fireball. Deploy Giant first, then Witch behind for air coverage."

❌ "Schedule breaks to enhance focus"
✅ "You're working on the Sequestron project in Canva. Based on your pattern of creating multiple copies for iterations, enable Canva's collaboration features now so you can share with your team and get feedback on the current version before making more copies."

❌ "Improve your writing"
✅ "Based on the observation showing you're working on the 'Auditing Observations' section of your GUMs paper, and your advisor's feedback about emphasizing privacy protections, rewrite the contextual norm violation detection part to highlight privacy more clearly. This addresses the specific feedback while maintaining your current workflow."

❌ "Check your documents"
✅ "The observation shows you're in the 'Auditing Observations' section of your GUMs paper. Based on your pattern of iterative document editing, save your current version now and create a backup before making the privacy-focused revisions your advisor suggested."

❌ "Enable collaboration features"
✅ "You're in Canva working on Sequestron. Based on your pattern of managing multiple profiles (PleasantonUSD, John, Arnav), switch to your main profile now and enable collaboration so your team can access the project directly instead of you having to share copies."

❌ "Check internet stability"
✅ "You're trying to message Krish on Instagram about the slideshow. Based on your pattern of communication challenges due to privacy settings, send Krish a follow request now so you can message him directly about the project instead of waiting for him to see your story."

❌ "Research productivity techniques"
✅ "You're working on DECA events research. Based on your pattern of using ChatGPT for information, open ChatGPT now and ask 'What are the key DECA events and dates for this year?' to get the specific information you'll need for planning."
"""

UTILITY_SCORING_PROMPT = """You are a suggestion utility evaluator. Score each suggestion based on expected value for the user.

USER CONTEXT: {user_context}

SUGGESTIONS TO SCORE:
{suggestions_json}

For each suggestion, provide scores (1-10 scale):
- benefit: Expected positive impact if implemented
- false_positive_cost: Harm if suggestion is wrong/irrelevant  
- false_negative_cost: Opportunity cost if user ignores good suggestion
- decay: How long the suggestion stays relevant (10=weeks, 1=minutes)
- probability_useful: Likelihood user finds this genuinely helpful (0.0-1.0)

Return JSON:
{{
  "scored_suggestions": [
    {{
      "index": 0,
      "benefit": 8.5,
      "false_positive_cost": 2.0,
      "false_negative_cost": 6.0,
      "decay": 7.0,
      "probability_useful": 0.85,
      "probability_false_positive": 0.15,
      "probability_false_negative": 0.10
    }},
    ...
  ]
}}"""


class GumboEngine:
    """
    Production-grade Gumbo suggestion engine.
    
    Implements the complete Gumbo algorithm with error handling,
    rate limiting, and real-time delivery capabilities.
    """
    
    def __init__(self):
        """Initialize the Gumbo engine."""
        self.rate_limiter = None
        self.ai_client = None
        self._active_sse_connections: set = set()
        self._suggestion_metrics = {
            "total_suggestions": 0,
            "total_batches": 0,
            "total_processing_time": 0.0,
            "last_batch_at": None,
            "rate_limit_hits": 0
        }
        
        # Engine lifecycle
        self._started = False
        self._startup_time = None
        
        logger.info("GumboEngine initialized")
    
    async def start(self):
        """Start the Gumbo engine with proper initialization."""
        if self._started:
            return
        
        try:
            # Initialize rate limiter
            self.rate_limiter = await get_rate_limiter()
            
            # Initialize AI client
            self.ai_client = await get_unified_client()
            
            self._started = True
            self._startup_time = datetime.now(timezone.utc)
            
            logger.info("GumboEngine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start GumboEngine: {e}")
            raise
    
    async def stop(self):
        """Stop the Gumbo engine with proper cleanup."""
        if not self._started:
            return
        
        try:
            # Close all SSE connections
            for connection in list(self._active_sse_connections):
                await self._close_sse_connection(connection)
            
            # Shutdown rate limiter
            if self.rate_limiter:
                await self.rate_limiter.stop()
            
            self._started = False
            logger.info("GumboEngine stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping GumboEngine: {e}")
    
    async def trigger_gumbo_suggestions(
        self, 
        proposition_id: int, 
        session: AsyncSession
    ) -> Optional[SuggestionBatch]:
        """
        Main Gumbo algorithm entry point.
        
        Triggered when a new high-confidence proposition is created.
        Implements the complete Gumbo flow with error handling.
        
        Args:
            proposition_id: ID of the trigger proposition
            session: Database session
            
        Returns:
            SuggestionBatch if successful, None if failed/rate limited
        """
        if not self._started:
            await self.start()
        
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        try:
            logger.info(f"🎯 Gumbo triggered for proposition {proposition_id}")
            
            # Step 1: Rate limiting check
            if not await self.rate_limiter.can_generate_suggestions():
                wait_time = await self.rate_limiter.get_wait_time()
                logger.info(f"⏰ Gumbo rate limited, next available in {wait_time:.1f}s")
                
                self._suggestion_metrics["rate_limit_hits"] += 1
                
                # Notify SSE clients about rate limiting
                await self._broadcast_sse_event(SSEEvent(
                    event=SSEEventType.RATE_LIMITED,
                    data={
                        "wait_time_seconds": wait_time,
                        "next_available_at": (datetime.now(timezone.utc) + 
                                            timedelta(seconds=wait_time)).isoformat(),
                        "message": f"Suggestion generation rate limited. Next batch available in {wait_time:.0f} seconds."
                    }
                ))
                
                return None
            
            # Step 2: Retrieve trigger proposition
            trigger_prop = await self._get_trigger_proposition(session, proposition_id)
            if not trigger_prop:
                logger.error(f"Trigger proposition {proposition_id} not found")
                return None
            
            # Step 3: Contextual retrieval
            context_result = await self._contextual_retrieval(session, trigger_prop)
            
            # Step 4: Multi-candidate generation
            suggestions = await self._generate_suggestion_candidates(trigger_prop, context_result)
            
            # Step 5: Mixed-initiative filtering (utility scoring)
            scored_suggestions = await self._score_suggestions(trigger_prop, suggestions, context_result)
            
            # Step 6: Create suggestion batch
            processing_time = time.time() - start_time
            batch = SuggestionBatch(
                suggestions=scored_suggestions,
                trigger_proposition_id=proposition_id,
                generated_at=datetime.now(timezone.utc),
                processing_time_seconds=processing_time,
                context_propositions_used=len(context_result.related_propositions),
                batch_id=batch_id
            )
            
            # Step 7: Save to database
            suggestion_ids = await self._save_suggestions_to_database(batch, session)
            
            # Step 8: Update metrics
            self._update_metrics(batch)
            
            # Step 9: Real-time delivery via SSE
            await self._broadcast_suggestion_batch(batch)
            
            # Step 10: Mark as delivered
            if suggestion_ids:
                await self._mark_suggestions_delivered(suggestion_ids, session)
            
            logger.info(f"✅ Gumbo completed for proposition {proposition_id} in {processing_time:.2f}s")
            return batch
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Gumbo failed for proposition {proposition_id} after {processing_time:.2f}s: {e}")
            
            # Notify SSE clients about error
            await self._broadcast_sse_event(SSEEvent(
                event=SSEEventType.ERROR,
                data={
                    "error_type": "suggestion_generation_failed",
                    "message": f"Failed to generate suggestions: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "proposition_id": proposition_id
                }
            ))
            
            return None
    
    async def _get_trigger_proposition(
        self, 
        session: AsyncSession, 
        proposition_id: int
    ) -> Optional[Proposition]:
        """Retrieve the trigger proposition from database."""
        try:
            stmt = select(Proposition).where(Proposition.id == proposition_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to retrieve trigger proposition {proposition_id}: {e}")
            return None
    
    async def _contextual_retrieval(
        self, 
        session: AsyncSession, 
        trigger_prop: Proposition
    ) -> ContextRetrievalResult:
        """
        Step 2: Contextual Retrieval
        
        Use LLM to generate semantic search query, then retrieve related propositions
        AND their attached observations for concrete content details.
        """
        start_time = time.time()
        
        try:
            # Generate semantic search query using LLM
            query_prompt = CONTEXTUAL_RETRIEVAL_PROMPT.format(
                trigger_text=trigger_prop.text,
                trigger_reasoning=trigger_prop.reasoning[:300]  # Truncate for prompt size
            )
            
            # Call LLM for semantic query generation  
            semantic_query = await asyncio.wait_for(
                self.ai_client.text_completion([{"role": "user", "content": query_prompt}], max_tokens=50),
                timeout=30.0
            )
            
            semantic_query = semantic_query.strip().strip('"').strip("'")
            logger.info(f"🔍 Generated semantic query: '{semantic_query}'")
            
            # Search for related propositions using BM25 - INCLUDE observations this time
            search_results = await search_propositions_bm25(
                session,
                semantic_query,
                mode="OR",
                limit=20,
                include_observations=True,  # CRITICAL: Get the raw observation data
                enable_mmr=True,
                enable_decay=True
            )
            
            # FALLBACK: If BM25 search doesn't return observations, use direct query
            if not search_results or all(not hasattr(prop, 'observations') or not prop.observations for prop, _ in search_results):
                logger.warning("BM25 search returned no observations, using direct database query fallback")
                
                # Get multiple types of propositions for rich context
                # 1. Propositions with observations (concrete data)
                stmt_with_obs = (
                    select(Proposition, func.count(observation_proposition.c.observation_id).label('obs_count'))
                    .outerjoin(observation_proposition, Proposition.id == observation_proposition.c.proposition_id)
                    .group_by(Proposition.id, Proposition.text, Proposition.reasoning, Proposition.confidence, Proposition.created_at)
                    .having(func.count(observation_proposition.c.observation_id) > 0)
                    .order_by(func.count(observation_proposition.c.observation_id).desc())
                    .limit(10)
                )
                
                # 2. Recent propositions (current context)
                stmt_recent = (
                    select(Proposition, literal_column("0").label('obs_count'))
                    .order_by(Proposition.created_at.desc())
                    .limit(10)
                )
                
                # Execute both queries
                result_with_obs = await session.execute(stmt_with_obs)
                result_recent = await session.execute(stmt_recent)
                
                # Combine results
                propositions_with_obs = [(prop, obs_count) for prop, obs_count in result_with_obs.fetchall()]
                recent_propositions = [(prop, 0) for prop, _ in result_recent.fetchall()]
                
                # Merge and deduplicate
                all_props = {}
                for prop, obs_count in propositions_with_obs + recent_propositions:
                    if prop.id not in all_props:
                        all_props[prop.id] = (prop, obs_count)
                
                search_results = list(all_props.values())
                logger.info(f"Multi-proposition query returned {len(search_results)} propositions (with observations + recent context)")
            
            # Convert to contextual propositions with their observations
            related_propositions = []
            all_observations = []
            
            for prop, score in search_results:
                if prop.id != trigger_prop.id:  # Exclude trigger proposition
                    # Manually load observations for this proposition
                    try:
                        # Get observation IDs from junction table first
                        stmt = select(observation_proposition.c.observation_id).where(
                            observation_proposition.c.proposition_id == prop.id
                        )
                        result = await session.execute(stmt)
                        obs_ids = [row[0] for row in result.fetchall()]
                        
                        if obs_ids:
                            # Check if observations actually exist
                            stmt = select(Observation).where(Observation.id.in_(obs_ids))
                            result = await session.execute(stmt)
                            actual_observations = result.scalars().all()
                            
                            # Extract observations
                            prop_observations = []
                            for obs in actual_observations:
                                prop_observations.append({
                                    'content': obs.content,
                                    'content_type': obs.content_type,
                                    'created_at': obs.created_at.isoformat() if obs.created_at else None
                                })
                                all_observations.append({
                                    'content': obs.content,
                                    'content_type': obs.content_type,
                                    'created_at': obs.created_at.isoformat() if obs.created_at else None,
                                    'proposition_id': prop.id
                                })
                        else:
                            prop_observations = []
                            
                    except Exception as e:
                        logger.warning(f"Failed to load observations for proposition {prop.id}: {e}")
                        prop_observations = []
                    
                    related_propositions.append(ContextualProposition(
                        id=prop.id,
                        text=prop.text,
                        reasoning=prop.reasoning,
                        confidence=prop.confidence or 0.0,
                        created_at=prop.created_at,
                        similarity_score=float(score),
                        observations=prop_observations
                    ))
            
            # Limit to top 10 for context management
            related_propositions = related_propositions[:10]
            
            # NEW: Get current screen content for enhanced context
            screen_content_start = time.time()
            current_screen_content = None
            
            try:
                current_screen_content = await self._get_current_screen_content(session)
                screen_content_time = time.time() - screen_content_start
                
                if current_screen_content:
                    logger.info(f"📱 Screen content retrieved in {screen_content_time:.3f}s ({len(current_screen_content)} chars)")
                else:
                    logger.info(f"📱 No screen content available (retrieved in {screen_content_time:.3f}s)")
                    
            except Exception as e:
                screen_content_time = time.time() - screen_content_start
                logger.warning(f"📱 Screen content retrieval failed after {screen_content_time:.3f}s: {e}")
                # Continue without screen content - this won't break suggestions
                current_screen_content = None
            
            retrieval_time = time.time() - start_time
            
            # Debug logging for observation data
            total_obs_content = sum(len(obs.get('content', '')) for obs in all_observations)
            logger.info(f"📋 Enhanced context: {len(related_propositions)} propositions + {len(all_observations)} observations ({total_obs_content} chars total) + screen content in {retrieval_time:.2f}s")
            
            if all_observations:
                sample_obs = all_observations[0]
                logger.info(f"📋 Sample observation: [{sample_obs.get('content_type', 'unknown')}] {sample_obs.get('content', '')[:100]}...")
            else:
                logger.warning("📋 No observations found - suggestions may be generic")
            
            return ContextRetrievalResult(
                related_propositions=related_propositions,
                total_found=len(search_results),
                retrieval_time_seconds=retrieval_time,
                semantic_query=semantic_query,
                screen_content=current_screen_content,  # Current screen content
                all_observations=all_observations  # NEW: Include all raw observations
            )
            
        except Exception as e:
            logger.error(f"Contextual retrieval failed: {e}")
            # Return empty result on failure
            return ContextRetrievalResult(
                related_propositions=[],
                total_found=0,
                retrieval_time_seconds=time.time() - start_time,
                semantic_query="fallback_query"
            )
    
    async def _generate_suggestion_candidates(
        self, 
        trigger_prop: Proposition, 
        context_result: ContextRetrievalResult
    ) -> List[Dict[str, Any]]:
        """
        Step 3: Multi-Candidate Generation
        
        Generate 5 suggestion candidates using trigger proposition, context, and raw observations.
        """
        try:
            # Prepare multi-proposition context for LLM
            related_context = ""
            context_props = context_result.related_propositions[:8]  # More propositions for rich context
            
            # Group by type for better organization
            high_confidence_props = [p for p in context_props if p.confidence and p.confidence >= 8]
            medium_confidence_props = [p for p in context_props if p.confidence and 5 <= p.confidence < 8]
            low_confidence_props = [p for p in context_props if p.confidence and p.confidence < 5]
            
            if high_confidence_props:
                related_context += "**High-Confidence Patterns:**\n"
                for prop in high_confidence_props[:3]:
                    related_context += f"- {prop.text} (confidence: {prop.confidence:.1f})\n"
            
            if medium_confidence_props:
                related_context += "\n**Medium-Confidence Context:**\n"
                for prop in medium_confidence_props[:3]:
                    related_context += f"- {prop.text} (confidence: {prop.confidence:.1f})\n"
            
            if low_confidence_props:
                related_context += "\n**Additional Context:**\n"
                for prop in low_confidence_props[:2]:
                    related_context += f"- {prop.text} (confidence: {prop.confidence:.1f})\n"
            
            if not related_context:
                related_context = "No directly related behavioral patterns found."
            
            # Prepare raw observations for LLM
            raw_observations = ""
            if context_result.all_observations:
                for i, obs in enumerate(context_result.all_observations[:10]):  # Top 10 observations
                    content_preview = obs.get('content', '')[:200]  # Limit length
                    obs_type = obs.get('content_type', 'unknown')
                    raw_observations += f"- [{obs_type}] {content_preview}...\n"
            else:
                raw_observations = "No raw observation data available."
            
            # Generate suggestion candidates
            generation_prompt = MULTI_CANDIDATE_GENERATION_PROMPT.format(
                trigger_text=trigger_prop.text,
                related_context=related_context,
                raw_observations=raw_observations,
                current_screen_context=context_result.screen_content if context_result.screen_content else "No current screen context available."
            )
            
            # Call LLM for suggestion generation
            response = await asyncio.wait_for(
                self.ai_client.text_completion([{"role": "user", "content": generation_prompt}], max_tokens=1000),
                timeout=30.0
            )
            
            # Parse JSON response
            suggestions_data = self._parse_json_response(response, "suggestions")
            suggestions = suggestions_data.get("suggestions", [])
            
            if len(suggestions) != 5:
                logger.warning(f"Expected 5 suggestions, got {len(suggestions)}")
            
            logger.info(f"💡 Generated {len(suggestions)} suggestion candidates")
            return suggestions
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            # Return fallback suggestions
            return [
                {
                    "title": "Review recent behavioral patterns",
                    "description": "Take a moment to review your recent activity patterns for optimization opportunities.",
                    "category": "productivity",
                    "rationale": "Fallback suggestion due to generation error",
                    "priority": "medium"
                }
            ]
    
    async def _score_suggestions(
        self, 
        trigger_prop: Proposition, 
        suggestions: List[Dict[str, Any]], 
        context_result: ContextRetrievalResult
    ) -> List[SuggestionData]:
        """
        Step 4: Mixed-Initiative Filtering
        
        Score suggestions using Expected Utility formula and return filtered results.
        """
        try:
            if not suggestions:
                return []
            
            # Prepare context for utility scoring
            user_context = f"Recent behavior: {trigger_prop.text}"
            if context_result.related_propositions:
                user_context += f"\nRelated patterns: {len(context_result.related_propositions)} behavioral insights"
            
            # Call LLM for utility scoring
            scoring_prompt = UTILITY_SCORING_PROMPT.format(
                user_context=user_context,
                suggestions_json=json.dumps(suggestions, indent=2)
            )
            
            response = await asyncio.wait_for(
                self.ai_client.text_completion([{"role": "user", "content": scoring_prompt}], max_tokens=800),
                timeout=30.0
            )
            
            # Parse scoring response
            scoring_data = self._parse_json_response(response, "scored_suggestions")
            scored_items = scoring_data.get("scored_suggestions", [])
            
            # Create final suggestion list with utility scores
            final_suggestions = []
            
            for i, suggestion in enumerate(suggestions):
                # Find corresponding score
                score_data = None
                for scored in scored_items:
                    if scored.get("index") == i:
                        score_data = scored
                        break
                
                if score_data:
                    # Calculate Expected Utility using the research formula
                    # EU = (Benefit × P_useful) - (FP_Cost × P_false_positive) - (FN_Cost × P_false_negative) × Decay_factor
                    benefit = score_data.get("benefit", 5.0)
                    fp_cost = score_data.get("false_positive_cost", 3.0)
                    fn_cost = score_data.get("false_negative_cost", 4.0)
                    decay = score_data.get("decay", 5.0)
                    p_useful = score_data.get("probability_useful", 0.5)
                    p_fp = score_data.get("probability_false_positive", 0.2)
                    p_fn = score_data.get("probability_false_negative", 0.3)
                    
                    # Expected Utility calculation
                    expected_utility = (
                        (benefit * p_useful) - 
                        (fp_cost * p_fp) - 
                        (fn_cost * p_fn)
                    ) * (decay / 10.0)  # Normalize decay to 0-1 range
                    
                    utility_scores = UtilityScores(
                        benefit=benefit,
                        false_positive_cost=fp_cost,
                        false_negative_cost=fn_cost,
                        decay=decay,
                        probability_useful=p_useful,
                        probability_false_positive=p_fp,
                        probability_false_negative=p_fn
                    )
                else:
                    # Fallback scoring
                    expected_utility = 5.0
                    utility_scores = None
                    p_useful = 0.5
                
                # Create final suggestion
                final_suggestion = SuggestionData(
                    title=suggestion.get("title", "Untitled Suggestion")[:200],
                    description=suggestion.get("description", "No description provided")[:1000],
                    probability_useful=p_useful,
                    rationale=suggestion.get("rationale", "No rationale provided")[:500],
                    category=suggestion.get("category", "general")[:100],
                    utility_scores=utility_scores,
                    expected_utility=expected_utility
                )
                
                final_suggestions.append(final_suggestion)
            
            # Sort by expected utility (highest first) and limit to top 5
            final_suggestions.sort(key=lambda x: x.expected_utility or 0, reverse=True)
            final_suggestions = final_suggestions[:5]
            
            logger.info(f"📊 Scored {len(final_suggestions)} suggestions, top utility: {final_suggestions[0].expected_utility:.2f}")
            
            return final_suggestions
            
        except Exception as e:
            logger.error(f"Suggestion scoring failed: {e}")
            
            # Create fallback scored suggestions
            fallback_suggestions = []
            for i, suggestion in enumerate(suggestions[:5]):
                fallback_suggestion = SuggestionData(
                    title=suggestion.get("title", f"Suggestion {i+1}")[:200],
                    description=suggestion.get("description", "Fallback suggestion")[:1000],
                    probability_useful=0.5,
                    rationale=suggestion.get("rationale", "Fallback rationale")[:500],
                    category=suggestion.get("category", "general")[:100],
                    expected_utility=5.0
                )
                fallback_suggestions.append(fallback_suggestion)
            
            return fallback_suggestions
    
    def _parse_json_response(self, response: str, expected_key: str) -> Dict[str, Any]:
        """Parse JSON response from LLM with error handling."""
        try:
            # Clean up the response
            response = response.strip()
            
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx >= 0 and end_idx >= 0:
                json_str = response[start_idx:end_idx+1]
                data = json.loads(json_str)
                
                if expected_key in data:
                    return data
                else:
                    logger.warning(f"Expected key '{expected_key}' not found in response")
                    return {expected_key: []}
            else:
                logger.error("No valid JSON found in LLM response")
                return {expected_key: []}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {expected_key: []}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return {expected_key: []}
    
    def _update_metrics(self, batch: SuggestionBatch):
        """Update internal metrics tracking."""
        self._suggestion_metrics["total_suggestions"] += len(batch.suggestions)
        self._suggestion_metrics["total_batches"] += 1
        self._suggestion_metrics["total_processing_time"] += batch.processing_time_seconds
        self._suggestion_metrics["last_batch_at"] = batch.generated_at
    
    async def _save_suggestions_to_database(
        self, 
        batch: SuggestionBatch, 
        session: AsyncSession
    ) -> List[int]:
        """Save suggestion batch to database and return suggestion IDs."""
        try:
            from ..models import Suggestion
            
            suggestion_ids = []
            
            for suggestion_data in batch.suggestions:
                # Create database record
                db_suggestion = Suggestion(
                    title=suggestion_data.title,
                    description=suggestion_data.description,
                    category=suggestion_data.category,
                    rationale=suggestion_data.rationale,
                    expected_utility=suggestion_data.expected_utility or 0.0,
                    probability_useful=suggestion_data.probability_useful or 0.0,
                    trigger_proposition_id=batch.trigger_proposition_id,
                    batch_id=batch.batch_id,
                    delivered=False  # Will be marked True when delivered via SSE
                )
                
                session.add(db_suggestion)
                await session.flush()  # Get the ID
                suggestion_ids.append(db_suggestion.id)
            
            await session.commit()
            
            logger.info(f"Saved {len(suggestion_ids)} suggestions to database")
            return suggestion_ids
            
        except Exception as e:
            logger.error(f"Failed to save suggestions to database: {e}")
            await session.rollback()
            return []

    async def _mark_suggestions_delivered(
        self, 
        suggestion_ids: List[int], 
        session: AsyncSession
    ):
        """Mark suggestions as delivered in database."""
        try:
            from ..models import Suggestion
            from sqlalchemy import update
            
            stmt = (
                update(Suggestion)
                .where(Suggestion.id.in_(suggestion_ids))
                .values(delivered=True)
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"Marked {len(suggestion_ids)} suggestions as delivered")
            
        except Exception as e:
            logger.error(f"Failed to mark suggestions as delivered: {e}")
            await session.rollback()

    async def _broadcast_suggestion_batch(self, batch: SuggestionBatch):
        """Broadcast suggestion batch via global SSE manager."""
        try:
            from .sse_manager import get_sse_manager
            sse_manager = get_sse_manager()
            
            await sse_manager.broadcast_event("suggestion_batch", {
                "suggestions": [s.dict() for s in batch.suggestions],
                "trigger_proposition_id": batch.trigger_proposition_id,
                "generated_at": batch.generated_at.isoformat(),
                "processing_time_seconds": batch.processing_time_seconds,
                "batch_id": batch.batch_id
            })
            
            logger.info(f"Broadcasted suggestion batch {batch.batch_id} via global SSE manager")
            
        except Exception as e:
            logger.error(f"Failed to broadcast suggestion batch via SSE: {e}")

    async def _broadcast_sse_event(self, event: SSEEvent):
        """Broadcast SSE event via global SSE manager."""
        try:
            from .sse_manager import get_sse_manager
            sse_manager = get_sse_manager()
            
            await sse_manager.broadcast_event(event.event.value, event.data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast SSE event via global manager: {e}")

    # Legacy methods - kept for compatibility but no longer used
    async def register_sse_connection(self, connection):
        """Legacy method - no longer used with global SSE manager."""
        logger.warning("register_sse_connection called but not used with global SSE manager")
    
    async def _close_sse_connection(self, connection):
        """Legacy method - no longer used with global SSE manager."""
        logger.warning("_close_sse_connection called but not used with global SSE manager")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current engine health status."""
        if not self._started:
            return {
                "status": "stopped",
                "uptime_seconds": 0,
                "metrics": self._suggestion_metrics,
                "rate_limit_status": None
            }
        
        uptime = (datetime.now(timezone.utc) - self._startup_time).total_seconds()
        
        # Calculate average processing time
        avg_processing_time = 0.0
        if self._suggestion_metrics["total_batches"] > 0:
            avg_processing_time = (
                self._suggestion_metrics["total_processing_time"] / 
                self._suggestion_metrics["total_batches"]
            )
        
        status = "healthy"
        if avg_processing_time > 10.0:  # Slow processing
            status = "degraded"
        
        return {
            "status": status,
            "uptime_seconds": uptime,
            "metrics": {
                **self._suggestion_metrics,
                "average_processing_time_seconds": avg_processing_time,
                "active_sse_connections": len(self._active_sse_connections)
            },
            "rate_limit_status": self.rate_limiter.get_status() if self.rate_limiter else None
        }

    async def _get_current_screen_content(
        self, 
        session: AsyncSession, 
        minutes_back: int = 5,
        max_content_length: int = 1000
    ) -> Optional[str]:
        """
        Get current screen content from recent observations for enhanced suggestions.
        
        This method safely retrieves recent screen observations and transcription data
        to provide context about what the user is currently working on.
        
        Args:
            session: Database session for querying observations
            minutes_back: How far back to look for recent observations (default: 5 minutes)
            max_content_length: Maximum content length to return (prevents prompt bloat)
            
        Returns:
            Formatted screen content string, or None if unavailable
            
        Raises:
            None - All errors are handled gracefully with fallbacks
        """
        start_time = time.time()
        
        try:
            # Calculate cutoff time for recent observations
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
            
            # Query for recent observations with proper indexing and limits
            stmt = (
                select(Observation)
                .where(
                    Observation.created_at >= cutoff_time,
                    Observation.content_type == "input_text"  # Only text observations
                )
                .order_by(Observation.created_at.desc())
                .limit(3)  # Limit to prevent performance issues
            )
            
            result = await session.execute(stmt)
            recent_observations = result.scalars().all()
            
            if not recent_observations:
                logger.info("📱 No recent screen observations found for context")
                return None
            
            # Build context string from recent observations
            context_parts = []
            total_length = 0
            
            for obs in recent_observations:
                # Extract key information from observation content
                content = obs.content.strip()
                if not content:
                    continue
                
                # Format timestamp for context
                time_str = obs.created_at.strftime("%I:%M %p")
                
                # Extract app name and key content if available
                app_info = ""
                key_content = ""
                
                # Parse structured content (if available)
                if "Application Name:" in content:
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if "Application Name:" in line:
                            app_info = line
                        elif any(indicator in line for indicator in ["Visible Text:", "Text Content:", "Browsing:", "Window Viewing:"]):
                            key_content = line
                            break
                    
                    # Format the context part
                    if app_info and key_content:
                        context_part = f"[{time_str}] {app_info} | {key_content}"
                    elif app_info:
                        context_part = f"[{time_str}] {app_info}"
                    else:
                        context_part = f"[{time_str}] {content[:100]}..."
                else:
                    # Fallback for unstructured content
                    context_part = f"[{time_str}] {content[:150]}..."
                
                # Check if adding this would exceed our length limit
                if total_length + len(context_part) > max_content_length:
                    context_parts.append(f"[{time_str}] {content[:100]}... (truncated)")
                    break
                
                context_parts.append(context_part)
                total_length += len(context_part)
            
            # Combine into readable context
            if not context_parts:
                logger.warning("📱 No valid context parts extracted from observations")
                return None
            
            screen_context = "\n".join(context_parts)
            processing_time = time.time() - start_time
            
            logger.info(f"📱 Retrieved {len(recent_observations)} recent observations for screen context in {processing_time:.3f}s")
            logger.debug(f"📱 Screen context length: {len(screen_context)} chars")
            
            return screen_context
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"📱 Failed to retrieve screen content after {processing_time:.3f}s: {e}")
            
            # Return None on failure - this won't break the suggestion system
            # The existing flow will continue without screen context
            return None


# Global engine instance (singleton pattern)
_global_engine: Optional[GumboEngine] = None


async def get_gumbo_engine() -> GumboEngine:
    """
    Get the global Gumbo engine instance.
    
    Returns:
        Initialized GumboEngine instance
    """
    global _global_engine
    
    if _global_engine is None:
        _global_engine = GumboEngine()
        await _global_engine.start()
    
    return _global_engine


async def trigger_gumbo_suggestions(proposition_id: int, session: AsyncSession) -> Optional[SuggestionBatch]:
    """
    Convenience function to trigger Gumbo suggestions.
    
    This is the main entry point called from gum/gum.py when a high-confidence
    proposition is created.
    """
    try:
        engine = await get_gumbo_engine()
        return await engine.trigger_gumbo_suggestions(proposition_id, session)
    except Exception as e:
        logger.error(f"Failed to trigger Gumbo suggestions: {e}")
        return None


async def shutdown_gumbo_engine():
    """Shutdown the global Gumbo engine (for cleanup)."""
    global _global_engine
    
    if _global_engine is not None:
        await _global_engine.stop()
        _global_engine = None
        logger.info("Global GumboEngine shutdown complete")
