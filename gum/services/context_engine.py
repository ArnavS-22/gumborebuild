"""
Context Engine - Intelligent Context Retrieval for GUM

Production-grade context retrieval system that intelligently gathers relevant
data from multiple sources to provide comprehensive context for AI suggestions.

Data Sources:
1. Transcription Data - Raw screen content and user interactions
2. Behavioral Data - AI-generated propositions and patterns  
3. Timeline Data - Hourly activity breakdowns
4. Proactive Suggestions - Real-time recommendations
5. Web Search - External information when needed

Author: GUM Team
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func, and_, or_
from sqlalchemy.orm import selectinload

# Import GUM components
from ..models import Observation, Proposition, init_db
from ..db_utils import search_propositions_bm25
from ..schemas import ContextItem, ContextRequest, ContextResponse, SearchRequest, SearchResult, SearchResponse

# Import unified AI client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Intelligent context retrieval and fusion engine.
    
    This engine intelligently retrieves and combines data from multiple sources
    to provide comprehensive context for AI suggestions.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the context engine.
        
        Args:
            session_factory: SQLAlchemy async session factory
        """
        self.session_factory = session_factory
        self.logger = logger
        
    async def get_context_for_query(self, request: ContextRequest) -> ContextResponse:
        """
        Get comprehensive context for a given query.
        
        Args:
            request: Context request with query and parameters
            
        Returns:
            ContextResponse with retrieved context items
        """
        start_time = time.time()
        
        try:
            # Initialize context items list
            context_items = []
            
            # Get context from different sources based on request
            context_tasks = []
            
            if "transcription" in request.context_types:
                context_tasks.append(self._get_transcription_context(
                    request.query, request.user_name, request.hours_back, request.max_items // 4
                ))
                
            if "behavioral" in request.context_types:
                context_tasks.append(self._get_behavioral_context(
                    request.query, request.user_name, request.max_items // 4
                ))
                
            if "timeline" in request.context_types:
                context_tasks.append(self._get_timeline_context(
                    request.query, request.user_name, request.hours_back, request.max_items // 4
                ))
                
            if "suggestion" in request.context_types:
                context_tasks.append(self._get_suggestion_context(
                    request.query, request.user_name, request.max_items // 4
                ))
            
            # Execute all context retrieval tasks in parallel
            if context_tasks:
                context_results = await asyncio.gather(*context_tasks, return_exceptions=True)
                
                # Combine results, handling any exceptions
                for result in context_results:
                    if isinstance(result, Exception):
                        self.logger.warning(f"Context retrieval failed: {result}")
                        continue
                    if isinstance(result, list):
                        context_items.extend(result)
            
            # Sort context items by confidence and recency
            context_items = self._rank_context_items(context_items, request.query)
            
            # Limit to max items
            context_items = context_items[:request.max_items]
            
            processing_time = (time.time() - start_time) * 1000
            
            return ContextResponse(
                query=request.query,
                context_items=context_items,
                total_found=len(context_items),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error getting context for query '{request.query}': {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return ContextResponse(
                query=request.query,
                context_items=[],
                total_found=0,
                processing_time_ms=processing_time
            )
    
    async def _get_transcription_context(self, query: str, user_name: Optional[str], 
                                       hours_back: int, max_items: int) -> List[ContextItem]:
        """
        Retrieve relevant transcription data (observations).
        
        Args:
            query: Search query
            user_name: User name for filtering
            hours_back: Hours to look back
            max_items: Maximum items to return
            
        Returns:
            List of context items from transcription data
        """
        try:
            async with self.session_factory() as session:
                # Calculate time threshold
                time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                
                # Search for relevant observations
                # Use simple text search for now, can be enhanced with vector search later
                stmt = (
                    select(Observation)
                    .where(
                        and_(
                            Observation.created_at >= time_threshold,
                            or_(
                                Observation.content.ilike(f"%{query}%"),
                                Observation.content.ilike(f"%{query.lower()}%"),
                                Observation.content.ilike(f"%{query.upper()}%")
                            )
                        )
                    )
                    .order_by(desc(Observation.created_at))
                    .limit(max_items)
                )
                
                result = await session.execute(stmt)
                observations = result.scalars().all()
                
                context_items = []
                for obs in observations:
                    # Calculate relevance score (simple keyword matching for now)
                    relevance = self._calculate_text_relevance(query, obs.content)
                    
                    context_items.append(ContextItem(
                        type="transcription",
                        content=obs.content[:500] + "..." if len(obs.content) > 500 else obs.content,
                        confidence=relevance,
                        source=f"observation_{obs.id}",
                        timestamp=obs.created_at if isinstance(obs.created_at, str) else str(obs.created_at),
                        metadata={
                            "observer_name": obs.observer_name,
                            "content_type": obs.content_type,
                            "full_length": len(obs.content)
                        }
                    ))
                
                return context_items
                
        except Exception as e:
            self.logger.error(f"Error getting transcription context: {e}")
            return []
    
    async def _get_behavioral_context(self, query: str, user_name: Optional[str], 
                                    max_items: int) -> List[ContextItem]:
        """
        Retrieve relevant behavioral data (propositions).
        
        Args:
            query: Search query
            user_name: User name for filtering
            max_items: Maximum items to return
            
        Returns:
            List of context items from behavioral data
        """
        try:
            async with self.session_factory() as session:
                # Use BM25 search for propositions (existing functionality)
                results = await search_propositions_bm25(session, query, limit=max_items)
                
                context_items = []
                for prop, score in results:
                    context_items.append(ContextItem(
                        type="behavioral",
                        content=f"Insight: {prop.text}\nReasoning: {prop.reasoning}",
                        confidence=min(score, 1.0),  # Normalize score to 0-1
                        source=f"proposition_{prop.id}",
                        timestamp=prop.created_at if isinstance(prop.created_at, str) else str(prop.created_at),
                        metadata={
                            "proposition_confidence": prop.confidence,
                            "decay": prop.decay,
                            "version": prop.version
                        }
                    ))
                
                return context_items
                
        except Exception as e:
            self.logger.error(f"Error getting behavioral context: {e}")
            return []
    
    async def _get_timeline_context(self, query: str, user_name: Optional[str], 
                                  hours_back: int, max_items: int) -> List[ContextItem]:
        """
        Retrieve relevant timeline data.
        
        Args:
            query: Search query  
            user_name: User name for filtering
            hours_back: Hours to look back
            max_items: Maximum items to return
            
        Returns:
            List of context items from timeline data
        """
        try:
            # For timeline context, we'll get recent high-confidence propositions
            # organized by time periods
            async with self.session_factory() as session:
                time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                
                stmt = (
                    select(Proposition)
                    .where(
                        and_(
                            Proposition.created_at >= time_threshold,
                            Proposition.confidence >= 7,  # High confidence only
                            or_(
                                Proposition.text.ilike(f"%{query}%"),
                                Proposition.reasoning.ilike(f"%{query}%")
                            )
                        )
                    )
                    .order_by(desc(Proposition.created_at))
                    .limit(max_items)
                )
                
                result = await session.execute(stmt)
                propositions = result.scalars().all()
                
                context_items = []
                for prop in propositions:
                    # Calculate time-based relevance
                    time_relevance = self._calculate_time_relevance(prop.created_at, hours_back)
                    text_relevance = self._calculate_text_relevance(query, f"{prop.text} {prop.reasoning}")
                    
                    # Combine relevance scores
                    combined_relevance = (time_relevance * 0.3) + (text_relevance * 0.7)
                    
                    context_items.append(ContextItem(
                        type="timeline",
                        content=f"Timeline Insight: {prop.text}",
                        confidence=combined_relevance,
                        source=f"timeline_prop_{prop.id}",
                        timestamp=prop.created_at if isinstance(prop.created_at, str) else str(prop.created_at),
                        metadata={
                            "confidence": prop.confidence,
                            "time_relevance": time_relevance,
                            "text_relevance": text_relevance
                        }
                    ))
                
                return context_items
                
        except Exception as e:
            self.logger.error(f"Error getting timeline context: {e}")
            return []
    
    async def _get_suggestion_context(self, query: str, user_name: Optional[str], 
                                    max_items: int) -> List[ContextItem]:
        """
        Retrieve relevant proactive suggestions.
        
        Args:
            query: Search query
            user_name: User name for filtering  
            max_items: Maximum items to return
            
        Returns:
            List of context items from suggestions
        """
        try:
            # For now, return empty list as suggestions are handled by the existing system
            # This can be enhanced to search through stored suggestions
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting suggestion context: {e}")
            return []
    
    async def search_transcriptions(self, request: SearchRequest) -> SearchResponse:
        """
        Search across transcription data with advanced filtering.
        
        Args:
            request: Search request with query and filters
            
        Returns:
            SearchResponse with results
        """
        start_time = time.time()
        
        try:
            async with self.session_factory() as session:
                # Build query conditions
                conditions = []
                
                # Add content search condition
                conditions.append(
                    or_(
                        Observation.content.ilike(f"%{request.query}%"),
                        Observation.content.ilike(f"%{request.query.lower()}%"),
                        Observation.content.ilike(f"%{request.query.upper()}%")
                    )
                )
                
                # Add content type filter
                if request.content_types:
                    conditions.append(Observation.content_type.in_(request.content_types))
                
                # Add date range filter
                if request.date_range:
                    start_date, end_date = request.date_range
                    conditions.append(
                        and_(
                            Observation.created_at >= start_date,
                            Observation.created_at <= end_date
                        )
                    )
                
                # Build and execute query
                stmt = (
                    select(Observation)
                    .where(and_(*conditions))
                    .order_by(desc(Observation.created_at))
                    .limit(request.limit)
                )
                
                result = await session.execute(stmt)
                observations = result.scalars().all()
                
                # Convert to search results
                search_results = []
                for obs in observations:
                    relevance_score = self._calculate_text_relevance(request.query, obs.content)
                    
                    search_results.append(SearchResult(
                        observation_id=obs.id,
                        content=obs.content[:300] + "..." if len(obs.content) > 300 else obs.content,
                        content_type=obs.content_type,
                        observer_name=obs.observer_name,
                        timestamp=obs.created_at,
                        relevance_score=relevance_score
                    ))
                
                processing_time = (time.time() - start_time) * 1000
                
                return SearchResponse(
                    query=request.query,
                    results=search_results,
                    total_found=len(search_results),
                    processing_time_ms=processing_time
                )
                
        except Exception as e:
            self.logger.error(f"Error searching transcriptions: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return SearchResponse(
                query=request.query,
                results=[],
                total_found=0,
                processing_time_ms=processing_time
            )
    
    def _calculate_text_relevance(self, query: str, text: str) -> float:
        """
        Calculate relevance score between query and text.
        
        Args:
            query: Search query
            text: Text to score
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not query or not text:
            return 0.0
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Simple relevance calculation
        # Can be enhanced with TF-IDF, embeddings, etc.
        
        # Exact match gets highest score
        if query_lower in text_lower:
            return 1.0
        
        # Word overlap scoring
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(text_words))
        return min(overlap / len(query_words), 1.0)
    
    def _calculate_time_relevance(self, timestamp: str, hours_back: int) -> float:
        """
        Calculate time-based relevance score.
        
        Args:
            timestamp: Timestamp to score
            hours_back: Hours back from now
            
        Returns:
            Time relevance score between 0.0 and 1.0
        """
        try:
            # Parse timestamp
            if isinstance(timestamp, str):
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                ts = timestamp
            
            # Calculate age in hours
            now = datetime.now(timezone.utc)
            age_hours = (now - ts).total_seconds() / 3600
            
            # More recent = higher score
            if age_hours <= 1:
                return 1.0
            elif age_hours <= 6:
                return 0.8
            elif age_hours <= 24:
                return 0.6
            elif age_hours <= 72:
                return 0.4
            else:
                return 0.2
                
        except Exception:
            return 0.5  # Default score
    
    def _rank_context_items(self, context_items: List[ContextItem], query: str) -> List[ContextItem]:
        """
        Rank context items by relevance and importance.
        
        Args:
            context_items: List of context items to rank
            query: Original query for relevance calculation
            
        Returns:
            Ranked list of context items
        """
        # Sort by confidence score (descending) and then by type priority
        type_priority = {
            "behavioral": 4,
            "transcription": 3,
            "timeline": 2,
            "suggestion": 1,
            "web": 1
        }
        
        def sort_key(item: ContextItem):
            return (
                item.confidence,  # Primary: confidence score
                type_priority.get(item.type, 0),  # Secondary: type priority
                item.timestamp or "1970-01-01"  # Tertiary: recency
            )
        
        return sorted(context_items, key=sort_key, reverse=True)


# Global context engine instance
_context_engine: Optional[ContextEngine] = None


def get_context_engine(session_factory) -> ContextEngine:
    """
    Get or create the global context engine instance.
    
    Args:
        session_factory: SQLAlchemy async session factory
        
    Returns:
        ContextEngine instance
    """
    global _context_engine
    
    if _context_engine is None:
        _context_engine = ContextEngine(session_factory)
    
    return _context_engine
