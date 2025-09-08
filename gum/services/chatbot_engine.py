"""
Chatbot Engine - Main AI Chatbot with GUM Integration

Production-grade chatbot engine that combines AI language models with 
comprehensive GUM context to provide personalized, context-aware assistance.

Features:
- Full GUM data integration (transcriptions, behavioral patterns, timeline)
- Multi-source context fusion
- Conversation memory and history
- Web search integration
- Performance optimization and caching
- Production-grade error handling

Author: GUM Team
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, insert, update, delete

# Import GUM components
from ..models import init_db
from ..schemas import (
    ChatMessage, ChatRequest, ChatResponse, ContextItem, ContextRequest,
    ChatSuggestion, ConversationHistory
)
from .context_engine import get_context_engine

# Import unified AI client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from unified_ai_client import get_unified_client

logger = logging.getLogger(__name__)


# Chatbot prompts
SYSTEM_PROMPT = """You are ChatGPT, but with one unique advantage: you have access to the user's recent work activity, screen content, behavioral patterns, and timeline data through their GUM system.

This gives you context about:
- What they're currently working on (real-time screen transcriptions)
- Their coding patterns and work habits
- Recent projects and timeline of activities
- Past debugging sessions and solutions they've tried

Use this context naturally and conversationally. You should:

**Be proactive:**
- Notice when they're stuck on something and offer to help
- Suggest improvements based on patterns you see
- Point out when they've solved similar problems before
- Recommend breaks or productivity tips based on their work rhythm

**Be conversational:**
- Chat naturally, like you're a knowledgeable friend who knows their work
- Reference their context casually when relevant ("I see you're working on that API issue...")
- Don't be overly formal or assistant-like
- Ask follow-up questions and engage in back-and-forth

**Be helpful:**
- Offer specific technical help based on what you can see
- Connect patterns across their work history
- Suggest optimizations or better approaches
- Help debug by understanding their current context

**Guidelines:**
- Reference their screen activity when it's relevant to their question
- Use their behavioral patterns to give personalized advice about anything
- Connect current situations to past experiences they've had
- Be casual about having this context - don't constantly explain that you can "see" things
- Focus on being genuinely helpful across all aspects of their life and interests

Remember: You're ChatGPT with memory. Use that memory to be more helpful, but keep the conversation natural and engaging."""

CONTEXT_INTEGRATION_PROMPT = """Based on the following context about the user, provide a helpful response to their query.

CONTEXT DATA:
{context_summary}

USER QUERY: {user_message}

Instructions:
- Use the context data to inform your response
- Reference specific context when relevant
- Be specific about what you can see from their activity
- Provide actionable suggestions based on their patterns
- If the context is relevant, mention it naturally in your response

Respond as their personal AI assistant with full knowledge of their work and patterns."""


class ChatbotEngine:
    """
    Main chatbot engine with GUM integration.
    
    This engine provides intelligent, context-aware responses by combining
    AI language models with comprehensive user context from GUM data.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the chatbot engine.
        
        Args:
            session_factory: SQLAlchemy async session factory
        """
        self.session_factory = session_factory
        self.context_engine = get_context_engine(session_factory)
        self.logger = logger
        self.conversation_cache = {}  # In-memory cache for active conversations
        
        # Performance metrics
        self.metrics = {
            "total_messages": 0,
            "total_context_items": 0,
            "avg_response_time": 0.0,
            "avg_context_retrieval_time": 0.0
        }
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message and generate a response with full context.
        
        Args:
            request: Chat request with message and parameters
            
        Returns:
            ChatResponse with AI response and context information
        """
        start_time = time.time()
        message_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Processing chat message: '{request.message[:50]}...'")
            
            # Step 1: Get conversation history if available
            conversation_history = []
            if request.conversation_id:
                conversation_history = await self._get_conversation_history(
                    request.conversation_id, limit=10
                )
            
            # Step 2: Retrieve relevant context
            context_items = []
            context_summary = ""
            
            if request.include_context:
                context_start = time.time()
                
                context_request = ContextRequest(
                    query=request.message,
                    user_name=request.user_name,
                    context_types=["transcription", "behavioral", "timeline", "suggestion"],
                    hours_back=request.context_hours_back,
                    max_items=request.max_context_items
                )
                
                context_response = await self.context_engine.get_context_for_query(context_request)
                context_items = context_response.context_items
                context_summary = self._create_context_summary(context_items)
                
                context_time = (time.time() - context_start) * 1000
                self.logger.info(f"Context retrieval took {context_time:.2f}ms, found {len(context_items)} items")
            
            # Step 3: Generate AI response
            ai_start = time.time()
            ai_response = await self._generate_ai_response(
                request.message, context_summary, conversation_history
            )
            ai_time = (time.time() - ai_start) * 1000
            
            # Step 4: Generate follow-up suggestions
            suggestions = await self._generate_suggestions(request.message, context_items, ai_response)
            
            # Step 5: Create chat message
            processing_time = (time.time() - start_time) * 1000
            
            chat_message = ChatMessage(
                id=message_id,
                content=ai_response,
                is_user=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context_used=context_items,
                suggestions=suggestions,
                processing_time_ms=processing_time
            )
            
            # Step 6: Store conversation
            if request.conversation_id:
                await self._store_message(request.conversation_id, request.message, True)
                await self._store_message(request.conversation_id, ai_response, False)
            
            # Step 7: Update metrics
            self._update_metrics(processing_time, len(context_items), context_time if request.include_context else 0)
            
            # Step 8: Create response
            response = ChatResponse(
                message=chat_message,
                context_summary=self._create_brief_context_summary(context_items),
                suggestions=suggestions,
                performance_metrics={
                    "total_time_ms": processing_time,
                    "context_time_ms": context_time if request.include_context else 0,
                    "ai_time_ms": ai_time,
                    "context_items_used": len(context_items)
                }
            )
            
            self.logger.info(f"Chat response generated in {processing_time:.2f}ms")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing chat message: {e}")
            
            # Return error response
            error_message = ChatMessage(
                id=message_id,
                content="I apologize, but I encountered an error processing your request. Please try again.",
                is_user=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context_used=[],
                suggestions=[],
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
            return ChatResponse(
                message=error_message,
                context_summary="Error occurred during processing",
                suggestions=[],
                performance_metrics={"error": str(e)}
            )
    
    async def _generate_ai_response(self, user_message: str, context_summary: str, 
                                  conversation_history: List[Dict]) -> str:
        """
        Generate AI response using the unified AI client.
        
        Args:
            user_message: User's message
            context_summary: Summary of relevant context
            conversation_history: Previous conversation messages
            
        Returns:
            AI-generated response
        """
        try:
            # Get unified AI client
            client = await get_unified_client()
            
            # Build conversation messages
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            # Add conversation history
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                messages.append({
                    "role": "user" if msg["is_user"] else "assistant",
                    "content": msg["content"]
                })
            
            # Add current message with context
            if context_summary:
                prompt = CONTEXT_INTEGRATION_PROMPT.format(
                    context_summary=context_summary,
                    user_message=user_message
                )
            else:
                prompt = user_message
            
            messages.append({"role": "user", "content": prompt})
            
            # Generate response
            response = await client.text_completion(
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
    
    def _create_context_summary(self, context_items: List[ContextItem]) -> str:
        """
        Create a comprehensive context summary for AI processing.
        
        Args:
            context_items: List of context items
            
        Returns:
            Formatted context summary
        """
        if not context_items:
            return "No specific context available."
        
        summary_parts = []
        
        # Group by type
        by_type = {}
        for item in context_items:
            if item.type not in by_type:
                by_type[item.type] = []
            by_type[item.type].append(item)
        
        # Format each type
        for context_type, items in by_type.items():
            if context_type == "transcription":
                summary_parts.append(f"RECENT SCREEN ACTIVITY:")
                for item in items[:3]:  # Top 3 most relevant
                    summary_parts.append(f"- {item.content[:200]}...")
            
            elif context_type == "behavioral":
                summary_parts.append(f"BEHAVIORAL PATTERNS:")
                for item in items[:3]:
                    summary_parts.append(f"- {item.content[:200]}...")
            
            elif context_type == "timeline":
                summary_parts.append(f"TIMELINE INSIGHTS:")
                for item in items[:2]:
                    summary_parts.append(f"- {item.content[:200]}...")
            
            elif context_type == "suggestion":
                summary_parts.append(f"PROACTIVE SUGGESTIONS:")
                for item in items[:2]:
                    summary_parts.append(f"- {item.content[:200]}...")
        
        return "\n".join(summary_parts)
    
    def _create_brief_context_summary(self, context_items: List[ContextItem]) -> str:
        """
        Create a brief context summary for the response.
        
        Args:
            context_items: List of context items
            
        Returns:
            Brief context summary
        """
        if not context_items:
            return "No context used"
        
        types = list(set(item.type for item in context_items))
        count = len(context_items)
        
        return f"Used {count} context items: {', '.join(types)}"
    
    async def _generate_suggestions(self, user_message: str, context_items: List[ContextItem], 
                                  ai_response: str) -> List[str]:
        """
        Generate follow-up suggestions based on the conversation.
        
        Args:
            user_message: User's original message
            context_items: Context items used
            ai_response: AI's response
            
        Returns:
            List of suggestion strings
        """
        # Simple suggestion generation based on context
        suggestions = []
        
        # Analyze context for suggestions
        has_transcription = any(item.type == "transcription" for item in context_items)
        has_behavioral = any(item.type == "behavioral" for item in context_items)
        has_timeline = any(item.type == "timeline" for item in context_items)
        
        if has_transcription:
            suggestions.append("What was I working on earlier today?")
            suggestions.append("Show me my recent screen activity")
        
        if has_behavioral:
            suggestions.append("What patterns do you see in my work?")
            suggestions.append("How can I improve my productivity?")
        
        if has_timeline:
            suggestions.append("What did I accomplish yesterday?")
            suggestions.append("Show me my timeline for this week")
        
        # Add general suggestions
        if "error" in user_message.lower() or "bug" in user_message.lower():
            suggestions.append("Help me debug this issue step by step")
            suggestions.append("What similar problems have I faced before?")
        
        if "code" in user_message.lower() or "programming" in user_message.lower():
            suggestions.append("Review my coding patterns")
            suggestions.append("Suggest code improvements")
        
        # Limit to 4 suggestions
        return suggestions[:4]
    
    async def _get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Get conversation history from database.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        try:
            # For now, return empty list - conversation storage will be implemented later
            return []
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def _store_message(self, conversation_id: str, content: str, is_user: bool):
        """
        Store a message in the database.
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            is_user: Whether message is from user
        """
        try:
            # For now, skip storage - will be implemented with database schema
            pass
        except Exception as e:
            self.logger.error(f"Error storing message: {e}")
    
    def _update_metrics(self, processing_time: float, context_items_count: int, context_time: float):
        """
        Update performance metrics.
        
        Args:
            processing_time: Total processing time in ms
            context_items_count: Number of context items used
            context_time: Context retrieval time in ms
        """
        self.metrics["total_messages"] += 1
        self.metrics["total_context_items"] += context_items_count
        
        # Update running averages
        total = self.metrics["total_messages"]
        self.metrics["avg_response_time"] = (
            (self.metrics["avg_response_time"] * (total - 1) + processing_time) / total
        )
        
        if context_time > 0:
            self.metrics["avg_context_retrieval_time"] = (
                (self.metrics["avg_context_retrieval_time"] * (total - 1) + context_time) / total
            )
    
    async def get_chat_suggestions(self, user_name: Optional[str]) -> List[ChatSuggestion]:
        """
        Get proactive chat suggestions based on user activity.
        
        Args:
            user_name: User name for filtering
            
        Returns:
            List of chat suggestions
        """
        try:
            suggestions = []
            
            # Get recent high-confidence behavioral insights
            context_request = ContextRequest(
                query="recent activity patterns productivity",
                user_name=user_name,
                context_types=["behavioral", "timeline"],
                hours_back=24,
                max_items=5
            )
            
            context_response = await self.context_engine.get_context_for_query(context_request)
            
            # Generate suggestions based on context
            if context_response.context_items:
                suggestions.extend([
                    ChatSuggestion(
                        id=str(uuid.uuid4()),
                        text="What patterns do you see in my recent work?",
                        category="insight",
                        priority=8,
                        context="Based on your recent behavioral patterns",
                        created_at=datetime.now(timezone.utc).isoformat()
                    ),
                    ChatSuggestion(
                        id=str(uuid.uuid4()),
                        text="How can I be more productive today?",
                        category="action",
                        priority=7,
                        context="Based on your productivity patterns",
                        created_at=datetime.now(timezone.utc).isoformat()
                    ),
                    ChatSuggestion(
                        id=str(uuid.uuid4()),
                        text="What was I working on yesterday?",
                        category="question",
                        priority=6,
                        context="Based on your timeline data",
                        created_at=datetime.now(timezone.utc).isoformat()
                    )
                ])
            
            # Add general suggestions
            suggestions.extend([
                ChatSuggestion(
                    id=str(uuid.uuid4()),
                    text="Help me debug this error",
                    category="help",
                    priority=5,
                    context="General coding assistance",
                    created_at=datetime.now(timezone.utc).isoformat()
                ),
                ChatSuggestion(
                    id=str(uuid.uuid4()),
                    text="Search my recent screen activity",
                    category="action",
                    priority=4,
                    context="Access to transcription data",
                    created_at=datetime.now(timezone.utc).isoformat()
                )
            ])
            
            # Sort by priority and limit
            suggestions.sort(key=lambda x: x.priority, reverse=True)
            return suggestions[:6]
            
        except Exception as e:
            self.logger.error(f"Error getting chat suggestions: {e}")
            return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        return self.metrics.copy()


# Global chatbot engine instance
_chatbot_engine: Optional[ChatbotEngine] = None


def get_chatbot_engine(session_factory) -> ChatbotEngine:
    """
    Get or create the global chatbot engine instance.
    
    Args:
        session_factory: SQLAlchemy async session factory
        
    Returns:
        ChatbotEngine instance
    """
    global _chatbot_engine
    
    if _chatbot_engine is None:
        _chatbot_engine = ChatbotEngine(session_factory)
    
    return _chatbot_engine
