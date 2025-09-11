#!/usr/bin/env python3
"""
Brutal Reality Check - Expose All Implementation Flaws

This test is designed to BREAK the enhanced proactive system and expose
every flaw, magical thinking, and half-assed implementation.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from gum.models import init_db, Observation, Proposition
from gum.services.proactive_engine import ProactiveEngine


async def test_expose_implementation_flaws():
    """Brutal test designed to expose every flaw in the implementation."""
    
    print("🔥 BRUTAL REALITY CHECK - Exposing Implementation Flaws")
    print("=" * 70)
    
    # Setup
    engine, Session = await init_db(":memory:")
    proactive_engine = ProactiveEngine()
    await proactive_engine.start()
    
    flaws_found = []
    
    # FLAW TEST 1: Context Path Confusion
    print("\n💥 FLAW TEST 1: Context Path Confusion")
    async with Session() as session:
        # Create observation with realistic transcription
        obs = Observation(
            observer_name="screen",
            content="User is in Canva working on marketing flyer, editing text 'Summer Sale'",
            content_type="input_text"
        )
        session.add(obs)
        await session.commit()
        
        # Test if enhanced context is actually used
        enhanced_context = await proactive_engine._get_enhanced_context_with_propositions(
            obs.content, obs.id, session
        )
        
        # Check if app extraction actually works
        extracted_app = enhanced_context['current_app']
        print(f"   Extracted app: '{extracted_app}'")
        
        if extracted_app == "Unknown":
            flaws_found.append("FLAW: App extraction broken - doesn't parse 'User is in Canva' format")
            print("   ❌ FLAW: App extraction completely broken")
        else:
            print("   ✅ App extraction working")
    
    # FLAW TEST 2: Proposition Integration Actually Working?
    print("\n💥 FLAW TEST 2: Proposition Integration Reality Check")
    async with Session() as session:
        # Add propositions
        props = [
            Proposition(
                text="User creates multiple design iterations",
                reasoning="Observed pattern",
                confidence=9,
                revision_group=str(uuid4()),
                version=1
            )
        ]
        session.add_all(props)
        await session.commit()
        
        # Test if propositions are actually retrieved
        enhanced_context = await proactive_engine._get_enhanced_context_with_propositions(
            "User working in Canva", 1, session
        )
        
        props_count = len(enhanced_context['behavioral_propositions'])
        print(f"   Propositions retrieved: {props_count}")
        
        if props_count == 0:
            flaws_found.append("FLAW: Proposition retrieval broken - no propositions found")
            print("   ❌ FLAW: Proposition retrieval completely broken")
        else:
            print("   ✅ Proposition retrieval working")
            print(f"   First proposition: {enhanced_context['behavioral_propositions'][0].text}")
    
    # FLAW TEST 3: Grounding Score Meaningfulness
    print("\n💥 FLAW TEST 3: Grounding Score Bullshit Detection")
    
    # Test with completely unrelated suggestion
    bullshit_suggestion = {
        "title": "I created a quantum blockchain solution",
        "description": "Advanced AI-powered cryptocurrency mining optimization system"
    }
    
    # Test with well-grounded suggestion
    grounded_suggestion = {
        "title": "I analyzed your Canva design workflow",
        "description": "Created version control for your marketing flyer iterations based on design patterns"
    }
    
    enhanced_context = {
        'current_transcription': "User is in Canva working on marketing flyer",
        'behavioral_propositions': props,
        'grounding_evidence': {
            'specific_apps': ['Canva'],
            'specific_actions': ['working'],
            'specific_content': ['marketing flyer']
        }
    }
    
    bullshit_score = proactive_engine._calculate_grounding_score(bullshit_suggestion, enhanced_context)
    grounded_score = proactive_engine._calculate_grounding_score(grounded_suggestion, enhanced_context)
    
    print(f"   Bullshit suggestion score: {bullshit_score:.3f}")
    print(f"   Grounded suggestion score: {grounded_score:.3f}")
    
    if bullshit_score >= grounded_score * 0.8:  # If bullshit scores within 80% of grounded
        flaws_found.append("FLAW: Grounding score is meaningless - doesn't distinguish quality")
        print("   ❌ FLAW: Grounding score is bullshit - doesn't distinguish quality")
    else:
        print("   ✅ Grounding score shows meaningful difference")
    
    # FLAW TEST 4: JSON Validation Actually Strict?
    print("\n💥 FLAW TEST 4: JSON Validation Strictness Reality Check")
    
    # Test with edge cases that should fail
    edge_case_items = [
        # Empty arrays (should fail per prompt rules)
        {
            "title": "Test",
            "description": "Test desc",
            "category": "completed_work",
            "rationale": "Test rationale",
            "priority": "high",
            "confidence": 9,
            "has_completed_work": True,
            "completed_work": {
                "content": "Test content",
                "content_type": "text",
                "preview": "Test preview",
                "action_label": "Test action",
                "metadata": {
                    "evidence_used": [],  # EMPTY ARRAY - should fail
                    "behavioral_patterns_applied": ["test"],
                    "current_context_references": ["test"],
                    "anti_hallucination_check": "test"
                }
            }
        },
        # Invalid confidence (should fail)
        {
            "title": "Test",
            "description": "Test desc", 
            "category": "completed_work",
            "rationale": "Test rationale",
            "priority": "high",
            "confidence": 7,  # Should fail - not 8, 9, or 10
            "has_completed_work": True,
            "completed_work": {
                "content": "Test",
                "content_type": "text",
                "preview": "Test",
                "action_label": "Test",
                "metadata": {
                    "evidence_used": ["test"],
                    "behavioral_patterns_applied": ["test"],
                    "current_context_references": ["test"],
                    "anti_hallucination_check": "test"
                }
            }
        }
    ]
    
    validation_working = True
    for i, item in enumerate(edge_case_items):
        is_valid = proactive_engine._validate_strict_json_structure(item)
        print(f"   Edge case {i+1} validation: {'PASSED' if is_valid else 'FAILED'}")
        
        if i == 0 and is_valid:  # Empty array should fail
            flaws_found.append("FLAW: JSON validation allows empty arrays despite prompt rules")
            validation_working = False
        
        if i == 1 and is_valid:  # Invalid confidence should fail
            flaws_found.append("FLAW: JSON validation allows invalid confidence values")
            validation_working = False
    
    if validation_working:
        print("   ✅ JSON validation working correctly")
    else:
        print("   ❌ FLAW: JSON validation is not actually strict")
    
    # FLAW TEST 5: Evidence Extraction Robustness
    print("\n💥 FLAW TEST 5: Evidence Extraction Edge Cases")
    
    # Test with edge case transcriptions
    edge_transcriptions = [
        "",  # Empty
        "User doing something vague",  # No specific details
        "Application: SomeWeirdApp\nUser clicking randomly",  # Unknown app
        "User is in VS Code debugging main.py line 47 ImportError",  # Rich content
    ]
    
    for i, transcription in enumerate(edge_transcriptions):
        evidence = proactive_engine._extract_grounding_evidence(transcription, [], [])
        evidence_count = sum(len(items) for items in evidence.values())
        
        print(f"   Transcription {i+1}: {evidence_count} evidence items")
        
        if i == 0 and evidence_count > 0:  # Empty should give no evidence
            flaws_found.append("FLAW: Evidence extraction hallucinates evidence from empty input")
        
        if i == 3 and evidence_count == 0:  # Rich content should give evidence
            flaws_found.append("FLAW: Evidence extraction fails on rich content")
    
    # FINAL VERDICT
    print("\n" + "=" * 70)
    if flaws_found:
        print("❌ IMPLEMENTATION IS BROKEN - CRITICAL FLAWS FOUND:")
        for i, flaw in enumerate(flaws_found, 1):
            print(f"   {i}. {flaw}")
        
        print("\n🔧 WHAT NEEDS TO BE FIXED:")
        print("   - Fix context path confusion")
        print("   - Remove duplicate code paths") 
        print("   - Fix app extraction regex")
        print("   - Make JSON validation actually strict")
        print("   - Improve evidence extraction robustness")
        
        return False
    else:
        print("✅ NO CRITICAL FLAWS FOUND - Implementation appears solid")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_expose_implementation_flaws())
    
    if not success:
        print("\n🔥 IMPLEMENTATION NEEDS MAJOR FIXES BEFORE PRODUCTION")
    else:
        print("\n🎯 IMPLEMENTATION PASSES BRUTAL REALITY CHECK")