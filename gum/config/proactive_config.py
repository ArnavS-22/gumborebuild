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
    min_specificity_score: int = 6  # Out of 10
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
    rate_limit_refill_rate: float = 1.0 / 45.0  # 1 token per 45 seconds
    
    # Feature Flags
    enable_context_parsing: bool = True
    enable_specificity_scoring: bool = True
    enable_retry_logic: bool = True
    enable_enhanced_validation: bool = True
    
    @classmethod
    def from_environment(cls) -> 'ProactiveEngineConfig':
        """Create configuration from environment variables."""
        return cls(
            max_tokens=int(os.getenv('PROACTIVE_MAX_TOKENS', 1200)),
            temperature=float(os.getenv('PROACTIVE_TEMPERATURE', 0.05)),
            timeout_seconds=float(os.getenv('PROACTIVE_TIMEOUT', 30.0)),
            max_retries=int(os.getenv('PROACTIVE_MAX_RETRIES', 2)),
            retry_delay_seconds=float(os.getenv('PROACTIVE_RETRY_DELAY', 1.0)),
            min_specificity_score=int(os.getenv('PROACTIVE_MIN_SPECIFICITY', 6)),
            processing_timeout_seconds=float(os.getenv('PROACTIVE_PROCESSING_TIMEOUT', 5.0)),
            rate_limit_capacity=int(os.getenv('PROACTIVE_RATE_CAPACITY', 3)),
            rate_limit_refill_rate=float(os.getenv('PROACTIVE_RATE_REFILL', 1.0/45.0)),
            enable_context_parsing=os.getenv('PROACTIVE_ENABLE_CONTEXT_PARSING', 'true').lower() == 'true',
            enable_specificity_scoring=os.getenv('PROACTIVE_ENABLE_SPECIFICITY', 'true').lower() == 'true',
            enable_retry_logic=os.getenv('PROACTIVE_ENABLE_RETRY', 'true').lower() == 'true',
            enable_enhanced_validation=os.getenv('PROACTIVE_ENABLE_VALIDATION', 'true').lower() == 'true'
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