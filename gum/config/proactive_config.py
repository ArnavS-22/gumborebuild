"""
Proactive Engine Configuration

Production-grade configuration management for the proactive suggestion engine.
Allows for easy tuning of behavior, rate limits, and quality thresholds.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProactiveEngineConfig:
    """Configuration settings for the proactive suggestion engine."""
    
    # AI Analysis Settings
    max_tokens: int = 1200
    temperature: float = 0.05
    timeout_seconds: float = 30.0
    
    # Retry Logic
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    
    # Quality Thresholds
    min_specificity_score: int = 7  # Raised for screen-first standards
    max_title_length: int = 60
    max_description_length: int = 300
    max_rationale_length: int = 200
    
    # Content Limits
    max_transcription_length: int = 1500
    max_visible_content_length: int = 800
    
    # Performance Settings
    processing_timeout_seconds: float = 5.0  # Max time before marking as degraded
    
    # Rate Limiting (separate from Gumbo)
    rate_limit_capacity: int = 3  # Allow burst of 3 suggestions
    rate_limit_refill_rate: float = 1.0 / 10.0  # 1 token per 10 seconds
    
    # Feature Flags
    enable_context_parsing: bool = True
    enable_specificity_scoring: bool = True
    enable_retry_logic: bool = True
    enable_enhanced_validation: bool = True
    enable_autonomous_execution: bool = True
    
    # Screen-First Analysis Settings
    enable_screen_first_analysis: bool = True
    screen_prediction_timeframe_seconds: int = 300  # 5 minutes max prediction
    min_screen_grounding_score: float = 4.0
    enable_next_step_prediction: bool = True
    enable_obstacle_prevention: bool = True
    enable_context_switch_detection: bool = True
    
    # Screen-First Validation Settings
    require_screen_element_references: bool = True
    require_next_step_predictions: bool = True
    require_immediate_timeframe: bool = True
    min_content_overlap_ratio: float = 0.1  # 10% minimum overlap with visible content
    
    @classmethod
    def from_environment(cls) -> 'ProactiveEngineConfig':
        """Create configuration from environment variables."""
        return cls(
            max_tokens=int(os.getenv('PROACTIVE_MAX_TOKENS', 1200)),
            temperature=float(os.getenv('PROACTIVE_TEMPERATURE', 0.05)),
            timeout_seconds=float(os.getenv('PROACTIVE_TIMEOUT', 30.0)),
            max_retries=int(os.getenv('PROACTIVE_MAX_RETRIES', 2)),
            retry_delay_seconds=float(os.getenv('PROACTIVE_RETRY_DELAY', 1.0)),
            min_specificity_score=int(os.getenv('PROACTIVE_MIN_SPECIFICITY', 7)),
            processing_timeout_seconds=float(os.getenv('PROACTIVE_PROCESSING_TIMEOUT', 5.0)),
            rate_limit_capacity=int(os.getenv('PROACTIVE_RATE_CAPACITY', 3)),
            rate_limit_refill_rate=float(os.getenv('PROACTIVE_RATE_REFILL', 1.0/45.0)),
            enable_context_parsing=os.getenv('PROACTIVE_ENABLE_CONTEXT_PARSING', 'true').lower() == 'true',
            enable_specificity_scoring=os.getenv('PROACTIVE_ENABLE_SPECIFICITY', 'true').lower() == 'true',
            enable_retry_logic=os.getenv('PROACTIVE_ENABLE_RETRY', 'true').lower() == 'true',
            enable_enhanced_validation=os.getenv('PROACTIVE_ENABLE_VALIDATION', 'true').lower() == 'true',
            enable_autonomous_execution=os.getenv('PROACTIVE_ENABLE_EXECUTION', 'true').lower() == 'true',
            
            # Screen-First Analysis Settings
            enable_screen_first_analysis=os.getenv('PROACTIVE_ENABLE_SCREEN_FIRST', 'true').lower() == 'true',
            screen_prediction_timeframe_seconds=int(os.getenv('PROACTIVE_PREDICTION_TIMEFRAME', 300)),
            min_screen_grounding_score=float(os.getenv('PROACTIVE_MIN_GROUNDING_SCORE', 4.0)),
            enable_next_step_prediction=os.getenv('PROACTIVE_ENABLE_NEXT_STEP', 'true').lower() == 'true',
            enable_obstacle_prevention=os.getenv('PROACTIVE_ENABLE_OBSTACLE_PREVENTION', 'true').lower() == 'true',
            enable_context_switch_detection=os.getenv('PROACTIVE_ENABLE_CONTEXT_SWITCH', 'true').lower() == 'true',
            
            # Screen-First Validation Settings
            require_screen_element_references=os.getenv('PROACTIVE_REQUIRE_SCREEN_REFS', 'true').lower() == 'true',
            require_next_step_predictions=os.getenv('PROACTIVE_REQUIRE_NEXT_STEPS', 'true').lower() == 'true',
            require_immediate_timeframe=os.getenv('PROACTIVE_REQUIRE_IMMEDIATE', 'true').lower() == 'true',
            min_content_overlap_ratio=float(os.getenv('PROACTIVE_MIN_CONTENT_OVERLAP', 0.1))
        )


# Global configuration instance
_config: Optional[ProactiveEngineConfig] = None


def get_config() -> ProactiveEngineConfig:
    """Get the global proactive engine configuration."""
    global _config
    if _config is None:
        _config = ProactiveEngineConfig.from_environment()
    return _config


def update_config(new_config: ProactiveEngineConfig):
    """Update the global configuration (for testing/runtime changes)."""
    global _config
    _config = new_config