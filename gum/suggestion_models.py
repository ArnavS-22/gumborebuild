"""
Gumbo Suggestion Models

Production-grade Pydantic models for the intelligent suggestion system.
Defines data structures for suggestions, SSE events, and utility scoring.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class SSEEventType(str, Enum):
    """Server-Sent Event types for real-time suggestion delivery."""
    SUGGESTIONS_AVAILABLE = "suggestions_available"
    SUGGESTION_BATCH = "suggestion_batch"
    HEARTBEAT = "heartbeat"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class UtilityScores(BaseModel):
    """Expected utility scoring components for suggestion filtering."""
    benefit: float = Field(..., ge=0, le=10, description="Expected benefit score (0-10)")
    false_positive_cost: float = Field(..., ge=0, le=10, description="Cost of false positive (0-10)")
    false_negative_cost: float = Field(..., ge=0, le=10, description="Cost of false negative (0-10)")
    decay: float = Field(..., ge=0, le=10, description="Time decay factor (0-10)")
    probability_useful: float = Field(..., ge=0, le=1, description="Probability suggestion is useful (0-1)")
    probability_false_positive: float = Field(..., ge=0, le=1, description="Probability of false positive (0-1)")
    probability_false_negative: float = Field(..., ge=0, le=1, description="Probability of false negative (0-1)")


class SuggestionData(BaseModel):
    """Individual suggestion with utility scoring and metadata."""
    title: str = Field(..., max_length=200, description="Short, actionable suggestion title")
    description: str = Field(..., max_length=1000, description="Detailed suggestion description")
    probability_useful: float = Field(..., ge=0, le=1, description="AI-estimated probability this suggestion is useful")
    rationale: str = Field(..., max_length=500, description="AI reasoning for this suggestion")
    category: str = Field(..., max_length=100, description="Suggestion category (e.g., 'productivity', 'workflow')")
    utility_scores: Optional[UtilityScores] = Field(None, description="Detailed utility scoring breakdown")
    expected_utility: Optional[float] = Field(None, description="Final expected utility score")
    
    @validator('title', 'description', 'rationale')
    def sanitize_text(cls, v):
        """Basic XSS protection - strip potential HTML/JS."""
        if not v:
            return v
        # Remove potential script tags and HTML
        import re
        v = re.sub(r'<[^>]*>', '', v)  # Remove HTML tags
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)  # Remove javascript:
        return v.strip()


class SuggestionBatch(BaseModel):
    """Batch of suggestions with metadata."""
    suggestions: List[SuggestionData] = Field(..., description="List of generated suggestions")
    trigger_proposition_id: int = Field(..., description="ID of proposition that triggered this batch")
    generated_at: datetime = Field(..., description="Timestamp when suggestions were generated")
    processing_time_seconds: float = Field(..., ge=0, description="Time taken to generate suggestions")
    context_propositions_used: int = Field(..., ge=0, description="Number of context propositions used")
    batch_id: str = Field(..., description="Unique identifier for this suggestion batch")


class SuggestionMetrics(BaseModel):
    """System health and performance metrics."""
    total_suggestions_generated: int = Field(..., ge=0)
    total_batches_processed: int = Field(..., ge=0)
    average_processing_time_seconds: float = Field(..., ge=0)
    last_batch_generated_at: Optional[datetime] = None
    rate_limit_hits_today: int = Field(..., ge=0)


class RateLimitStatus(BaseModel):
    """Rate limiter status information."""
    tokens_available: int = Field(..., ge=0)
    tokens_capacity: int = Field(..., ge=0)
    next_refill_at: datetime
    is_rate_limited: bool
    wait_time_seconds: float = Field(..., ge=0)


class SuggestionHealthResponse(BaseModel):
    """Health check response for suggestion system."""
    status: str = Field(..., description="Overall system status: 'healthy', 'degraded', 'unhealthy'")
    metrics: SuggestionMetrics
    rate_limit_status: RateLimitStatus
    last_error: Optional[str] = None
    uptime_seconds: float = Field(..., ge=0)


# SSE Event Data Models
class HeartbeatSSEData(BaseModel):
    """Heartbeat event data."""
    timestamp: datetime
    connections_active: int = Field(..., ge=0)


class RateLimitSSEData(BaseModel):
    """Rate limit event data."""
    wait_time_seconds: float = Field(..., ge=0)
    next_available_at: datetime
    message: str


class ErrorSSEData(BaseModel):
    """Error event data."""
    error_type: str
    message: str
    timestamp: datetime
    retry_after_seconds: Optional[float] = None


class SSEEvent(BaseModel):
    """Server-Sent Event wrapper."""
    event: SSEEventType
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None  # Milliseconds
    
    def to_sse_format(self) -> str:
        """Convert to Server-Sent Events format."""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
            
        lines.append(f"event: {self.event}")
        
        # Convert data to JSON string
        import json
        data_json = json.dumps(self.data, default=str)
        lines.append(f"data: {data_json}")
        
        # Add empty line to end the event
        lines.append("")
        
        return "\n".join(lines)


# Context Retrieval Models
class ContextualProposition(BaseModel):
    """Proposition with similarity score and observations for context retrieval."""
    id: int
    text: str
    reasoning: str
    confidence: float
    created_at: datetime
    similarity_score: float = Field(..., ge=0, le=1)
    observations: List[Dict[str, Any]] = Field(default_factory=list, description="Raw observation data attached to this proposition")


class ContextRetrievalResult(BaseModel):
    """Result of contextual proposition retrieval."""
    related_propositions: List[ContextualProposition]
    total_found: int
    retrieval_time_seconds: float
    semantic_query: str
    screen_content: Optional[str] = Field(None, description="Current screen content for enhanced context")
    all_observations: List[Dict[str, Any]] = Field(default_factory=list, description="All raw observations for context")
# WHISPER Multi-Layer Reasoning Models

class ScenarioUnderstanding(BaseModel):
    """Layer 1: Comprehensive understanding of user's current scenario."""
    current_activity: str = Field(..., description="What the user is currently doing")
    immediate_context: str = Field(..., description="Immediate context of their activity")
    accomplishment_goal: str = Field(..., description="What they're trying to accomplish")
    state_of_mind: str = Field(..., description="Current state of mind/focus")
    challenges: List[str] = Field(default_factory=list, description="Challenges or obstacles they're facing")
    broader_context: str = Field(..., description="Broader context of their activity")


class GoalReasoning(BaseModel):
    """Layer 2: Deep reasoning about user's goals."""
    primary_goal: str = Field(..., description="User's primary goal")
    secondary_goals: List[str] = Field(default_factory=list, description="Secondary goals")
    timeline: str = Field(..., description="Timeline and urgency")
    constraints: List[str] = Field(default_factory=list, description="Constraints and limitations")
    skill_level: str = Field(..., description="User's skill level and experience")
    working_style: str = Field(..., description="Preferred working style")
    immediate_next_steps: List[str] = Field(default_factory=list, description="Immediate next steps")
    most_helpful: str = Field(..., description="What would be most helpful right now")


class NextMovePrediction(BaseModel):
    """Layer 3: Prediction of user's next move."""
    predicted_action: str = Field(..., description="Most likely next action")
    useful_preparation: str = Field(..., description="What would be useful to prepare")
    specific_content: str = Field(..., description="Specific content that would help")
    content_format: str = Field(..., description="Best format for the content")
    detail_level: str = Field(..., description="Appropriate level of detail")
    time_saving: str = Field(..., description="How this saves time")
    stuck_prevention: str = Field(..., description="How this prevents getting stuck")
    confidence_boost: str = Field(..., description="How this builds confidence")


class DeliveryStrategy(BaseModel):
    """Layer 4: Strategy for delivering assistance."""
    delivery_type: str = Field(..., description="Type of delivery (suggestion/prepared_content)")
    message: str = Field(..., description="Message/title to show user")
    content_type: str = Field(..., description="Type of content to generate")
    specific_content: str = Field(..., description="The actual content to show/generate")
    tone: str = Field(..., description="Tone to use in delivery")
    positioning: str = Field(..., description="UI positioning")
    button_text: str = Field(..., description="Button text")
    engagement_strategy: str = Field(..., description="Strategy to engage user")
    safety_check: str = Field(..., description="Safety validation result")
    helpfulness_score: float = Field(..., ge=1, le=10, description="Helpfulness score 1-10")
    timing_score: float = Field(..., ge=1, le=10, description="Timing appropriateness 1-10")


class PreparedContent(BaseModel):
    """Layer 5: Generated prepared content."""
    content: str = Field(..., description="The actual generated content")
    content_type: str = Field(..., description="Type of content generated")
    completeness: str = Field(..., description="Level of completeness")
    production_ready: bool = Field(..., description="Whether it's production-ready")
    includes_documentation: bool = Field(..., description="Includes documentation")
    includes_error_handling: bool = Field(..., description="Includes error handling")
    includes_logging: bool = Field(..., description="Includes logging")
    usage_example: str = Field(..., description="Usage example")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    help_text: str = Field(..., description="Brief description of what this provides")


class WhisperUIData(BaseModel):
    """Layer 6: UI data for frontend rendering."""
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Bubble title")
    message: str = Field(..., description="Main message")
    action_type: str = Field(..., description="Type of action (code_completion, etc.)")
    button_text: str = Field(..., description="Button text")
    positioning: str = Field(..., description="UI positioning")
    content: str = Field(..., description="Content to show")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    helpfulness: float = Field(..., ge=1, le=10, description="Helpfulness score")
    timing: float = Field(..., ge=1, le=10, description="Timing score")
    rationale: str = Field(..., description="AI rationale")
    usage_example: str = Field(..., description="Usage example")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies")


class WhisperSession(BaseModel):
    """Tracks complete WHISPER reasoning session."""
    id: str = Field(..., description="Session ID")
    trigger_proposition_id: int = Field(..., description="Trigger proposition ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    processing_time_seconds: float = Field(..., description="Total processing time")
    session_status: str = Field(..., description="Session status")

    # Reasoning chain results
    scenario_understanding: Optional[ScenarioUnderstanding] = None
    goal_reasoning: Optional[GoalReasoning] = None
    next_move_prediction: Optional[NextMovePrediction] = None
    delivery_strategy: Optional[DeliveryStrategy] = None
    prepared_content: Optional[PreparedContent] = None
    whisper_ui_data: Optional[WhisperUIData] = None

    # Error tracking
    errors: List[str] = Field(default_factory=list, description="Errors encountered during processing")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")


# WHISPER SSE Events
class WhisperBubbleSSEData(BaseModel):
    """WHISPER bubble event data."""
    session_id: str
    whisper_data: WhisperUIData
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Enhanced SSE Event Types
class EnhancedSSEEventType(str, Enum):
    """Enhanced SSE event types including WHISPER."""
    SUGGESTIONS_AVAILABLE = "suggestions_available"
    SUGGESTION_BATCH = "suggestion_batch"
    WHISPER_BUBBLE = "whisper_bubble"
    HEARTBEAT = "heartbeat"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    all_observations: List[Dict[str, Any]] = Field(default_factory=list, description="All raw observations from related propositions")