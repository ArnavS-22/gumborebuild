"""
Brutal Reality Check - Test what actually breaks in the Screen-First System
This test is designed to find all the ways the system fails with real data
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_broken_screen_state_access():
    """Test the broken screen state access in proactive engine"""
    print("🔥 Testing Broken Screen State Access...")
    
    # This is what the proactive engine actually does
    enhanced_context = {
        'screen_state': {}  # This is a dict, not a ScreenState object!
    }
    
    try:
        # This line from proactive_engine.py will crash
        current_task = enhanced_context.get('screen_state', {}).current_task if enhanced_context.get('screen_state') else 'unknown'
        print(f"   ❌ SHOULD HAVE CRASHED: Got {current_task}")
        return False
    except AttributeError as e:
        print(f"   ✅ CRASHED AS EXPECTED: {e}")
        print("   🚨 CRITICAL BUG: Proactive engine tries to access .current_task on dict")
        return True

def test_malformed_transcription_data():
    """Test how system handles malformed transcription data"""
    print("\n🔥 Testing Malformed Transcription Data...")
    
    from gum.services.proactive_engine import parse_transcription_data
    
    # Test 1: Empty transcription
    try:
        result = parse_transcription_data("")
        print(f"   Empty transcription: {result}")
        assert result['current_app'] == 'Unknown'
        print("   ✅ Handles empty transcription")
    except Exception as e:
        print(f"   ❌ CRASHES on empty transcription: {e}")
        return False
    
    # Test 2: Malformed transcription
    try:
        malformed = "Random garbage text with no structure @#$%^&*()"
        result = parse_transcription_data(malformed)
        print(f"   Malformed transcription: {result}")
        print("   ✅ Handles malformed transcription")
    except Exception as e:
        print(f"   ❌ CRASHES on malformed transcription: {e}")
        return False
    
    # Test 3: Very long transcription
    try:
        long_transcription = "Application: VS Code\n" + "x" * 10000
        result = parse_transcription_data(long_transcription)
        print(f"   Long transcription visible_content length: {len(result['visible_content'])}")
        print("   ✅ Handles very long transcription")
    except Exception as e:
        print(f"   ❌ CRASHES on long transcription: {e}")
        return False
    
    return True

def test_screen_analyzer_edge_cases():
    """Test screen analyzer with edge cases that will break it"""
    print("\n🔥 Testing Screen Analyzer Edge Cases...")
    
    try:
        from gum.services.screen_first_analyzer import ScreenFirstAnalyzer
        analyzer = ScreenFirstAnalyzer()
        
        # Test 1: Empty context
        try:
            screen_state = analyzer.analyze_screen_state("", {})
            print(f"   Empty context result: {screen_state.current_task}")
            print("   ✅ Handles empty context")
        except Exception as e:
            print(f"   ❌ CRASHES on empty context: {e}")
            return False
        
        # Test 2: Missing context fields
        try:
            incomplete_context = {"current_app": "VS Code"}  # Missing other fields
            screen_state = analyzer.analyze_screen_state("Some text", incomplete_context)
            print(f"   Incomplete context result: {screen_state.current_task}")
            print("   ✅ Handles incomplete context")
        except Exception as e:
            print(f"   ❌ CRASHES on incomplete context: {e}")
            return False
        
        # Test 3: Weird app names
        try:
            weird_context = {"current_app": "Visual Studio Code.exe (64-bit)"}
            screen_state = analyzer.analyze_screen_state("coding stuff", weird_context)
            print(f"   Weird app name result: {screen_state.current_task}")
            # This will probably return 'general_work' instead of 'coding'
            if screen_state.current_task != 'coding':
                print("   🚨 BUG: Doesn't recognize 'Visual Studio Code.exe' as coding app")
            print("   ✅ Doesn't crash on weird app names")
        except Exception as e:
            print(f"   ❌ CRASHES on weird app names: {e}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"   ❌ CAN'T EVEN IMPORT: {e}")
        return False

def test_ai_prompt_format_assumptions():
    """Test if the AI prompt format actually works"""
    print("\n🔥 Testing AI Prompt Format Assumptions...")
    
    from gum.services.proactive_engine import SCREEN_FIRST_PROACTIVE_PROMPT
    
    # Test 1: Missing format parameters
    try:
        # This should crash if any format parameter is missing
        incomplete_format = SCREEN_FIRST_PROACTIVE_PROMPT.format(
            current_transcription="test",
            current_app="VS Code"
            # Missing other required parameters
        )
        print("   ❌ SHOULD HAVE CRASHED: Missing format parameters didn't cause error")
        return False
    except KeyError as e:
        print(f"   ✅ CRASHES AS EXPECTED on missing format params: {e}")
        print("   🚨 BUG: Prompt will crash if any context is missing")
    
    # Test 2: None values in format
    try:
        format_with_nones = SCREEN_FIRST_PROACTIVE_PROMPT.format(
            current_transcription=None,  # This will break
            current_app="VS Code",
            active_window="main.py",
            visible_content="code",
            user_actions="coding",
            time_context="2:30 PM",
            behavioral_propositions_formatted="none",
            recent_observations_formatted="none"
        )
        print("   ❌ SHOULD HAVE CRASHED: None values didn't cause error")
        return False
    except (TypeError, AttributeError) as e:
        print(f"   ✅ CRASHES AS EXPECTED on None values: {e}")
        print("   🚨 BUG: Prompt will crash if context contains None")
    
    return True

def test_database_integration_assumptions():
    """Test database integration assumptions"""
    print("\n🔥 Testing Database Integration Assumptions...")
    
    # Test 1: Check if new fields actually exist in Suggestion model
    try:
        from gum.models import Suggestion
        
        # Check if the model has the fields I'm trying to use
        suggestion = Suggestion()
        
        # These fields might not exist
        test_fields = [
            'screen_prediction_type', 'prediction_timeframe', 'current_task',
            'task_stage', 'urgency_level', 'predicted_next_actions'
        ]
        
        missing_fields = []
        for field in test_fields:
            if not hasattr(suggestion, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   🚨 CRITICAL: Missing database fields: {missing_fields}")
            print("   ❌ Database integration will fail - fields don't exist")
            return False
        else:
            print("   ✅ All expected database fields exist")
            
    except ImportError as e:
        print(f"   ❌ CAN'T IMPORT MODELS: {e}")
        return False
    
    return True

def test_json_serialization_edge_cases():
    """Test JSON serialization with complex objects"""
    print("\n🔥 Testing JSON Serialization Edge Cases...")
    
    # Test 1: Complex metadata serialization
    try:
        complex_metadata = {
            "current_screen_elements": ["VS Code", "main.py", None],  # None value
            "predicted_next_steps": [],  # Empty array
            "screen_context_used": "Test" * 1000,  # Very long string
            "nested_object": {"key": {"nested": "value"}},  # Nested objects
            "datetime_object": datetime.now()  # Non-serializable object
        }
        
        serialized = json.dumps(complex_metadata)
        print("   ❌ SHOULD HAVE CRASHED: Complex metadata serialized without error")
        return False
        
    except (TypeError, ValueError) as e:
        print(f"   ✅ CRASHES AS EXPECTED on complex metadata: {e}")
        print("   🚨 BUG: Metadata serialization will fail with datetime objects")
    
    return True

def test_performance_with_large_data():
    """Test performance assumptions with large data"""
    print("\n🔥 Testing Performance with Large Data...")
    
    # Test 1: Very long transcription
    huge_transcription = "Application: VS Code\n" + "def function():\n    pass\n" * 1000
    print(f"   Huge transcription size: {len(huge_transcription)} chars")
    
    try:
        from gum.services.proactive_engine import parse_transcription_data
        import time
        
        start_time = time.time()
        result = parse_transcription_data(huge_transcription)
        parse_time = time.time() - start_time
        
        print(f"   Parse time: {parse_time:.3f}s")
        if parse_time > 1.0:
            print("   🚨 PERFORMANCE ISSUE: Parsing takes >1 second")
        else:
            print("   ✅ Parsing performance acceptable")
            
    except Exception as e:
        print(f"   ❌ CRASHES on large transcription: {e}")
        return False
    
    return True

def test_configuration_fallbacks():
    """Test configuration fallback assumptions"""
    print("\n🔥 Testing Configuration Fallback Assumptions...")
    
    try:
        from gum.services.proactive_engine import get_config
        
        # Test if fallback config has all required fields
        config = get_config()
        
        required_fields = [
            'enable_screen_first_analysis', 'enable_enhanced_validation',
            'max_retries', 'timeout_seconds', 'min_specificity_score'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(config, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"   🚨 CRITICAL: Missing config fields: {missing_fields}")
            print("   ❌ Configuration fallback is incomplete")
            return False
        else:
            print("   ✅ Configuration fallback has required fields")
            
    except Exception as e:
        print(f"   ❌ Configuration system broken: {e}")
        return False
    
    return True

async def test_real_ai_integration():
    """Test if the AI integration actually works"""
    print("\n🔥 Testing Real AI Integration...")
    
    try:
        # Mock the AI client to test integration
        from gum.services.proactive_engine import ProactiveEngine
        
        engine = ProactiveEngine()
        
        # Test if initialization works
        mock_ai_client = AsyncMock()
        engine.ai_client = mock_ai_client
        engine._started = True
        
        # Test malformed AI response
        mock_ai_client.text_completion.return_value = "This is not JSON at all!"
        
        result = await engine._analyze_screen_activity("test transcription", 1, None)
        
        if result == []:
            print("   ✅ Handles malformed AI response gracefully")
        else:
            print("   ❌ Should return empty list for malformed AI response")
            return False
            
    except Exception as e:
        print(f"   ❌ AI integration broken: {e}")
        return False
    
    return True

def main():
    """Run brutal reality checks"""
    print("💀 BRUTAL REALITY CHECK - Finding What Actually Breaks")
    print("=" * 70)
    
    tests = [
        ("Broken Screen State Access", test_broken_screen_state_access),
        ("Malformed Transcription Data", test_malformed_transcription_data),
        ("Screen Analyzer Edge Cases", test_screen_analyzer_edge_cases),
        ("AI Prompt Format Assumptions", test_ai_prompt_format_assumptions),
        ("Database Integration Assumptions", test_database_integration_assumptions),
        ("JSON Serialization Edge Cases", test_json_serialization_edge_cases),
        ("Performance with Large Data", test_performance_with_large_data),
        ("Configuration Fallbacks", test_configuration_fallbacks),
    ]
    
    failures = []
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"   ✅ {test_name} - Issues found but handled")
            else:
                print(f"   ❌ {test_name} - CRITICAL FAILURE")
                failures.append(test_name)
        except Exception as e:
            print(f"   💥 {test_name} - CRASHED: {e}")
            failures.append(test_name)
    
    # Test async function
    try:
        result = asyncio.run(test_real_ai_integration())
        if not result:
            failures.append("Real AI Integration")
    except Exception as e:
        print(f"   💥 Real AI Integration - CRASHED: {e}")
        failures.append("Real AI Integration")
    
    print("\n" + "=" * 70)
    
    if failures:
        print(f"💀 BRUTAL REALITY: {len(failures)} CRITICAL FAILURES FOUND")
        for failure in failures:
            print(f"   🚨 {failure}")
        
        print("\n🔥 WHAT I ACTUALLY DELIVERED:")
        print("   ❌ Broken screen state object access")
        print("   ❌ Missing error handling for edge cases")
        print("   ❌ Untested database field assumptions")
        print("   ❌ Fragile AI prompt formatting")
        print("   ❌ No performance validation")
        print("   ❌ Incomplete configuration fallbacks")
        
        print("\n💡 WHAT NEEDS TO BE FIXED:")
        print("   1. Fix screen state object access in proactive engine")
        print("   2. Add comprehensive error handling")
        print("   3. Test database integration with real schema")
        print("   4. Validate AI prompt with real responses")
        print("   5. Add performance safeguards")
        print("   6. Complete configuration system")
        
        return False
    else:
        print("🎉 ALL BRUTAL TESTS PASSED - System is actually robust")
        return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💀 CONCLUSION: The 'production ready' system is actually broken")
        print("🔧 Need to fix critical issues before claiming completion")
    sys.exit(0 if success else 1)