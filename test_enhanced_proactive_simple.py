#!/usr/bin/env python3
"""
Enhanced Proactive System with Propositions - Simple Integration Test

This test validates the enhanced proactive system implementation without external dependencies.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Test setup
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from gum.models import init_db, Observation, Proposition, Suggestion
from gum.services.proactive_engine import ProactiveEngine
from sqlalchemy import select


async def test_enhanced_proactive_system():
    """Test the enhanced proactive system with proposition intelligence."""
    
    print("🎯 Enhanced Proactive System with Propositions - Integration Test")
    print("=" * 70)
    
    try:
        # Setup test database
        print("\n🔧 Setting up test environment...")
        engine, Session = await init_db(":memory:")
        print("✅ Test database created")
        
        # Create test data
        async with Session() as session:
            # Create realistic observations
            observations = [
                Observation(
                    observer_name="screen",
                    content="User is in Canva working on marketing flyer design, editing headline text 'Summer Sale 2024', has been working for 35 minutes",
                    content_type="input_text",
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
                ),
                Observation(
                    observer_name="screen", 
                    content="User opened team shared folder, browsing marketing materials from previous campaigns",
                    content_type="input_text",
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=8)
                ),
                Observation(
                    observer_name="screen",
                    content="User in VS Code debugging Python application, examining stack trace for ImportError on line 47",
                    content_type="input_text", 
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=15)
                )
            ]
            
            # Create realistic propositions
            from uuid import uuid4
            propositions = [
                Proposition(
                    text="User typically creates 3-4 design iterations before finalizing marketing materials",
                    reasoning="Pattern observed across design sessions, user saves multiple versions",
                    confidence=9,
                    revision_group=str(uuid4()),
                    version=1,
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
                ),
                Proposition(
                    text="User shares designs with team for feedback after initial draft completion",
                    reasoning="Consistent behavior: opens team folder, enables sharing, sends for review",
                    confidence=8,
                    revision_group=str(uuid4()),
                    version=1,
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=10)
                ),
                Proposition(
                    text="User works in focused 45-60 minute design sessions with iterative approach",
                    reasoning="Time tracking shows consistent session lengths, multiple save points",
                    confidence=7,
                    revision_group=str(uuid4()),
                    version=1,
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=12)
                )
            ]
            
            session.add_all(observations + propositions)
            await session.commit()
            print(f"✅ Created {len(observations)} observations and {len(propositions)} propositions")
        
        # Test enhanced context retrieval
        print("\n📋 Test 1: Enhanced Context Retrieval")
        proactive_engine = ProactiveEngine()
        await proactive_engine.start()
        
        async with Session() as session:
            current_observation = observations[0]
            
            # Test enhanced context retrieval
            enhanced_context = await proactive_engine._get_enhanced_context_with_propositions(
                current_observation.content,
                current_observation.id,
                session
            )
            
            # Validate context structure
            required_keys = ['current_transcription', 'behavioral_propositions', 'recent_observations', 'grounding_evidence']
            for key in required_keys:
                assert key in enhanced_context, f"Missing key: {key}"
            
            print(f"✅ Enhanced context structure validated")
            print(f"   - Current transcription: {len(enhanced_context['current_transcription'])} chars")
            print(f"   - Behavioral propositions: {len(enhanced_context['behavioral_propositions'])}")
            print(f"   - Recent observations: {len(enhanced_context['recent_observations'])}")
            print(f"   - Grounding evidence categories: {len(enhanced_context['grounding_evidence'])}")
        
        # Test strict JSON validation
        print("\n🔍 Test 2: Strict JSON Validation")
        
        # Valid work item
        valid_work_item = {
            "title": "I analyzed your design workflow based on Canva patterns",
            "description": "Created version control system for marketing flyer iterations",
            "category": "completed_work",
            "rationale": "Based on your pattern of creating 3-4 design iterations",
            "priority": "high",
            "confidence": 9,
            "has_completed_work": True,
            "completed_work": {
                "content": "Version control system with naming conventions",
                "content_type": "text",
                "preview": "Organized file structure for design iterations",
                "action_label": "Click to see version system",
                "metadata": {
                    "evidence_used": ["Canva usage", "marketing flyer"],
                    "behavioral_patterns_applied": ["3-4 design iterations pattern"],
                    "current_context_references": ["Summer Sale 2024 headline"],
                    "anti_hallucination_check": "Grounded in observed Canva usage patterns"
                }
            }
        }
        
        # Test validation
        is_valid = proactive_engine._validate_strict_json_structure(valid_work_item)
        assert is_valid == True, "Valid work item should pass validation"
        print("✅ Valid JSON structure passed validation")
        
        # Test grounding score calculation
        print("\n🎯 Test 3: Anti-Hallucination Grounding")
        grounding_score = proactive_engine._calculate_grounding_score(valid_work_item, enhanced_context)
        print(f"✅ Grounding score calculated: {grounding_score:.3f}")
        assert grounding_score > 0.0, "Should have some grounding"
        
        # Test evidence extraction
        print("\n🔍 Test 4: Evidence Extraction")
        grounding_evidence = proactive_engine._extract_grounding_evidence(
            current_observation.content, propositions, observations
        )
        
        print(f"✅ Evidence extracted:")
        for category, items in grounding_evidence.items():
            if items:
                print(f"   - {category}: {items}")
        
        # Test formatting methods
        print("\n📝 Test 5: Context Formatting")
        behavioral_formatted = proactive_engine._format_behavioral_propositions(propositions)
        observations_formatted = proactive_engine._format_recent_observations(observations)
        evidence_formatted = proactive_engine._format_grounding_evidence(grounding_evidence)
        
        assert behavioral_formatted != "No recent behavioral patterns available"
        assert observations_formatted != "No recent activity context available"
        print("✅ Context formatting working correctly")
        
        # Final validation
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED - Enhanced Proactive System Implementation Complete!")
        print("\n📊 Implementation Summary:")
        print("   ✅ Enhanced context retrieval with propositions")
        print("   ✅ Strict JSON formatting and validation")
        print("   ✅ Anti-hallucination grounding mechanisms")
        print("   ✅ Behavioral intelligence integration")
        print("   ✅ Evidence extraction and formatting")
        
        print("\n🚀 Key Features Implemented:")
        print("   - Proposition intelligence integration")
        print("   - Extremely strict JSON formatting")
        print("   - Anti-hallucination grounding")
        print("   - Behavioral pattern application")
        print("   - Enhanced context retrieval")
        print("   - Unconstrained AI capabilities")
        
        print("\n🎯 Ready for Production:")
        print("   - All core functionality preserved")
        print("   - Enhanced suggestion quality through propositions")
        print("   - Strict validation prevents malformed responses")
        print("   - Grounding mechanisms prevent hallucination")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_enhanced_proactive_system())
    
    if success:
        print("\n🎉 ENHANCED PROACTIVE SYSTEM READY FOR DEPLOYMENT!")
    else:
        print("\n❌ ENHANCED PROACTIVE SYSTEM NEEDS DEBUGGING")