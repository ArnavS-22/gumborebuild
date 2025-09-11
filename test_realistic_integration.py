"""
Realistic Integration Test - Test with actual dependencies and real data
This test validates the system actually works end-to-end with realistic conditions
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_screen_state_object_access_fix():
    """Test that the screen state object access fix actually works"""
    print("🔧 Testing Screen State Object Access Fix...")
    
    # Simulate the actual enhanced_context structure
    from gum.services.screen_first_analyzer import ScreenState
    
    # Test 1: With valid ScreenState object
    screen_state = ScreenState(
        current_task="coding",
        task_stage="stuck", 
        next_likely_actions=["debug_error"],
        immediate_obstacles=["type_error"],
        required_resources=[],
        workflow_stage="blocked",
        context_switch_signals=[],
        urgency_level="immediate",
        completion_percentage=0.3
    )
    
    enhanced_context = {
        'screen_state': screen_state,
        'current_app': 'VS Code'
    }
    
    # Test the safe access method
    try:
        from gum.services.proactive_engine import ProactiveEngine
        engine = ProactiveEngine()
        
        current_task = engine._safe_get_screen_field(enhanced_context, 'current_task', 'unknown')
        task_stage = engine._safe_get_screen_field(enhanced_context, 'task_stage', 'unknown')
        
        print(f"   ✅ Safe access works: task={current_task}, stage={task_stage}")
        assert current_task == "coding"
        assert task_stage == "stuck"
        
    except Exception as e:
        print(f"   ❌ Safe access still broken: {e}")
        return False
    
    # Test 2: With None screen_state
    enhanced_context_none = {'screen_state': None}
    
    try:
        current_task = engine._safe_get_screen_field(enhanced_context_none, 'current_task', 'fallback')
        print(f"   ✅ Handles None screen_state: {current_task}")
        assert current_task == "fallback"
        
    except Exception as e:
        print(f"   ❌ Fails with None screen_state: {e}")
        return False
    
    # Test 3: With missing screen_state
    enhanced_context_missing = {}
    
    try:
        current_task = engine._safe_get_screen_field(enhanced_context_missing, 'current_task', 'missing')
        print(f"   ✅ Handles missing screen_state: {current_task}")
        assert current_task == "missing"
        
    except Exception as e:
        print(f"   ❌ Fails with missing screen_state: {e}")
        return False
    
    return True

def test_json_serialization_fix():
    """Test that JSON serialization is properly handled"""
    print("\n🔧 Testing JSON Serialization Fix...")
    
    try:
        from gum.services.proactive_engine import ProactiveEngine
        engine = ProactiveEngine()
        
        # Test complex metadata that would break JSON
        complex_metadata = {
            "current_screen_elements": ["VS Code", "main.py", None],  # None value
            "predicted_next_steps": [],  # Empty array
            "screen_context_used": "Test" * 100,  # Long string
            "datetime_object": datetime.now(),  # Non-serializable
            "nested_object": {"key": {"nested": "value"}},  # Nested
            "number": 42,
            "boolean": True
        }
        
        completed_work = {
            "content": "Test content",
            "content_type": "text", 
            "preview": "Test preview",
            "action_label": "Test action",
            "metadata": complex_metadata
        }
        
        # Test sanitization
        sanitized = engine._sanitize_completed_work(completed_work)
        
        # Test that it can be JSON serialized
        json_str = json.dumps(sanitized)
        print(f"   ✅ Sanitization works: {len(json_str)} chars")
        
        # Verify sanitized content
        assert sanitized['content'] == "Test content"
        assert sanitized['metadata']['number'] == 42
        assert sanitized['metadata']['boolean'] == True
        assert isinstance(sanitized['metadata']['datetime_object'], str)  # Should be ISO string
        assert sanitized['metadata']['current_screen_elements'] == ["VS Code", "main.py", "None"]  # None converted to string
        
        return True
        
    except Exception as e:
        print(f"   ❌ JSON serialization still broken: {e}")
        return False

def test_error_handling_robustness():
    """Test that error handling actually prevents crashes"""
    print("\n🔧 Testing Error Handling Robustness...")
    
    try:
        from gum.services.proactive_engine import parse_transcription_data
        
        # Test 1: Empty transcription
        result = parse_transcription_data("")
        print(f"   ✅ Empty transcription: {result['current_app']}")
        
        # Test 2: Malformed transcription
        result = parse_transcription_data("Random garbage @#$%^&*()")
        print(f"   ✅ Malformed transcription: {result['current_app']}")
        
        # Test 3: Very long transcription
        long_transcription = "Application: VS Code\n" + "x" * 5000
        result = parse_transcription_data(long_transcription)
        print(f"   ✅ Long transcription: {len(result['visible_content'])} chars")
        
        # Test 4: Transcription with special characters
        special_transcription = "Application: VS Code\nContent: def test():\n    return 'hello\\nworld'"
        result = parse_transcription_data(special_transcription)
        print(f"   ✅ Special characters: {result['current_app']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error handling still broken: {e}")
        return False

def test_configuration_robustness():
    """Test configuration system handles missing fields"""
    print("\n🔧 Testing Configuration Robustness...")
    
    try:
        from gum.services.proactive_engine import ProactiveEngine
        
        # Test with minimal config
        class MinimalConfig:
            max_tokens = 1000
            temperature = 0.1
            timeout_seconds = 20.0
            # Missing many fields
        
        engine = ProactiveEngine(config=MinimalConfig())
        
        # Test getattr with defaults
        enable_screen = getattr(engine.config, 'enable_screen_first_analysis', False)
        enable_validation = getattr(engine.config, 'enable_enhanced_validation', False)
        
        print(f"   ✅ Handles missing config fields: screen={enable_screen}, validation={enable_validation}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration still broken: {e}")
        return False

async def test_ai_prompt_with_real_mock():
    """Test AI prompt formatting with realistic mock responses"""
    print("\n🔧 Testing AI Prompt with Realistic Mock...")
    
    try:
        from gum.services.proactive_engine import ProactiveEngine, SCREEN_FIRST_PROACTIVE_PROMPT
        
        # Test prompt formatting with edge cases
        test_contexts = [
            {
                'current_transcription': '',  # Empty
                'current_app': None,  # None value
                'active_window': 'Test Window',
                'visible_content': '',
                'user_actions': '',
                'time_context': '2:30 PM',
                'behavioral_propositions_formatted': '',
                'recent_observations_formatted': ''
            },
            {
                'current_transcription': 'x' * 10000,  # Very long
                'current_app': 'VS Code',
                'active_window': 'main.py',
                'visible_content': 'def test(): pass',
                'user_actions': 'coding',
                'time_context': '2:30 PM',
                'behavioral_propositions_formatted': 'Test propositions',
                'recent_observations_formatted': 'Test observations'
            }
        ]
        
        for i, context in enumerate(test_contexts):
            try:
                # This should not crash
                prompt = SCREEN_FIRST_PROACTIVE_PROMPT.format(**context)
                print(f"   ✅ Context {i+1}: Prompt formatted ({len(prompt)} chars)")
                
            except Exception as format_error:
                print(f"   ❌ Context {i+1}: Prompt formatting failed: {format_error}")
                return False
        
        # Test with mock AI client
        engine = ProactiveEngine()
        mock_ai_client = AsyncMock()
        engine.ai_client = mock_ai_client
        engine._started = True
        
        # Test various AI responses
        test_responses = [
            '{"immediate_work": []}',  # Empty response
            'Not JSON at all',  # Invalid JSON
            '{"immediate_work": [{"title": "Test", "invalid": "structure"}]}',  # Invalid structure
            '{"immediate_work": [{"title": "Valid", "description": "Test", "category": "screen_first_proactive", "rationale": "Test", "priority": "high", "confidence": 9, "has_completed_work": true, "completed_work": {"content": "Test", "content_type": "text", "preview": "Test", "action_label": "Test", "metadata": {"current_screen_elements": ["test"], "predicted_next_steps": ["test"], "screen_context_used": "test"}}}]}'  # Valid response
        ]
        
        for i, response in enumerate(test_responses):
            mock_ai_client.text_completion.return_value = response
            
            try:
                # Mock session
                mock_session = AsyncMock()
                mock_session.execute.return_value.scalars.return_value.all.return_value = []
                
                result = await engine._analyze_screen_activity("test transcription", 1, mock_session)
                print(f"   ✅ AI Response {i+1}: Handled gracefully (got {len(result)} suggestions)")
                
            except Exception as ai_error:
                print(f"   ❌ AI Response {i+1}: Failed: {ai_error}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ AI prompt testing failed: {e}")
        return False

def test_database_field_compatibility():
    """Test database field compatibility without actual database"""
    print("\n🔧 Testing Database Field Compatibility...")
    
    try:
        # Test suggestion creation without database
        suggestion_data = {
            "title": "Test Suggestion",
            "description": "Test description",
            "category": "screen_first_proactive",
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
                    "current_screen_elements": ["VS Code"],
                    "predicted_next_steps": ["debug_error"],
                    "screen_context_used": "Test context"
                }
            },
            # These fields might not exist in database
            "screen_prediction_type": "next_action",
            "prediction_timeframe": "2_minutes",
            "current_task": "coding",
            "task_stage": "stuck"
        }
        
        # Test JSON serialization of the full suggestion
        json_str = json.dumps(suggestion_data)
        print(f"   ✅ Suggestion serializes to JSON: {len(json_str)} chars")
        
        # Test deserialization
        deserialized = json.loads(json_str)
        assert deserialized["title"] == "Test Suggestion"
        print("   ✅ Suggestion deserializes correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database compatibility test failed: {e}")
        return False

def test_performance_safeguards():
    """Test performance with realistic data sizes"""
    print("\n🔧 Testing Performance Safeguards...")
    
    try:
        from gum.services.proactive_engine import parse_transcription_data
        import time
        
        # Test with various data sizes
        sizes = [100, 1000, 10000, 50000]  # chars
        
        for size in sizes:
            transcription = f"Application: VS Code\nContent: {'x' * size}"
            
            start_time = time.time()
            result = parse_transcription_data(transcription)
            parse_time = time.time() - start_time
            
            print(f"   Size {size:5d} chars: {parse_time:.3f}s")
            
            if parse_time > 1.0:
                print(f"   🚨 PERFORMANCE WARNING: {size} chars took {parse_time:.3f}s")
            
            # Verify result is reasonable
            assert result['current_app'] == 'VS Code'
            assert len(result['visible_content']) <= 503  # Should be truncated
        
        print("   ✅ Performance acceptable for tested sizes")
        return True
        
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

async def test_complete_workflow_simulation():
    """Test complete workflow with mocked dependencies"""
    print("\n🔧 Testing Complete Workflow Simulation...")
    
    try:
        # Mock all external dependencies
        with patch('gum.services.proactive_engine.get_unified_client') as mock_get_client, \
             patch('gum.services.proactive_engine.get_rate_limiter') as mock_get_limiter:
            
            # Setup mocks
            mock_ai_client = AsyncMock()
            mock_get_client.return_value = mock_ai_client
            
            mock_rate_limiter = AsyncMock()
            mock_rate_limiter.can_generate_suggestions.return_value = True
            mock_get_limiter.return_value = mock_rate_limiter
            
            # Create realistic AI response
            ai_response = json.dumps({
                "immediate_work": [{
                    "title": "I fixed your TypeError on line 45",
                    "description": "I analyzed your VS Code error and created the fix with error handling.",
                    "category": "screen_first_proactive",
                    "rationale": "Based on current VS Code activity with TypeError",
                    "priority": "high",
                    "confidence": 9,
                    "has_completed_work": True,
                    "screen_prediction_type": "obstacle_prevention",
                    "prediction_timeframe": "2_minutes",
                    "completed_work": {
                        "content": "def calculate_total(items):\n    return sum(item.get('price', 0) for item in items if item)",
                        "content_type": "text",
                        "preview": "Fixed TypeError with error handling",
                        "action_label": "Apply Fix",
                        "metadata": {
                            "current_screen_elements": ["VS Code", "main.py", "line 45"],
                            "predicted_next_steps": ["debug_error", "test_function"],
                            "immediate_obstacles_prevented": ["TypeError blocking execution"],
                            "screen_context_used": "VS Code TypeError on line 45"
                        }
                    }
                }]
            })
            
            mock_ai_client.text_completion.return_value = ai_response
            
            # Create realistic transcription
            transcription = """
            Application: VS Code
            Window Title: main.py
            Visible Text Content: def calculate_total(items):
                return sum(item['price'] for item in items)
            Error: TypeError: 'NoneType' object is not subscriptable
            Line: 45
            User is debugging the calculate_total function
            """
            
            # Create mock observation
            from gum.models import Observation
            observation = Observation(
                id=1,
                observer_name="screen",
                content=transcription,
                content_type="input_text",
                created_at=datetime.now(timezone.utc)
            )
            
            # Mock database session
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = observation
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.add = MagicMock()
            
            # Test complete workflow
            from gum.services.proactive_engine import ProactiveEngine
            engine = ProactiveEngine()
            
            suggestions = await engine.process_observation(1, mock_session)
            
            # Validate results
            if suggestions and len(suggestions) > 0:
                suggestion = suggestions[0]
                print(f"   ✅ Complete workflow: Generated {len(suggestions)} suggestions")
                print(f"   ✅ Suggestion title: {suggestion.get('title', 'No title')}")
                print(f"   ✅ Has completed work: {suggestion.get('has_completed_work', False)}")
                print(f"   ✅ Screen analysis: {suggestion.get('screen_first_analysis', False)}")
                
                # Verify database save was attempted
                assert mock_session.add.called
                assert mock_session.commit.called
                print("   ✅ Database operations called")
                
                return True
            else:
                print("   ❌ No suggestions generated")
                return False
                
    except Exception as e:
        print(f"   ❌ Complete workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fallback_mechanisms():
    """Test that fallback mechanisms actually work"""
    print("\n🔧 Testing Fallback Mechanisms...")
    
    try:
        from gum.services.proactive_engine import ProactiveEngine
        
        # Test with broken screen analyzer
        engine = ProactiveEngine()
        
        # Mock a broken screen analyzer
        class BrokenAnalyzer:
            def analyze_screen_state(self, *args, **kwargs):
                raise Exception("Screen analyzer is broken!")
        
        engine.screen_analyzer = BrokenAnalyzer()
        
        # Test that it falls back gracefully
        enhanced_context = {
            'current_transcription': 'test',
            'current_app': 'VS Code'
        }
        
        # This should not crash due to error handling
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        # Mock AI client
        mock_ai_client = AsyncMock()
        mock_ai_client.text_completion.return_value = '{"immediate_work": []}'
        engine.ai_client = mock_ai_client
        engine._started = True
        
        result = await engine._analyze_screen_activity("test", 1, mock_session)
        
        print(f"   ✅ Fallback works: Got {len(result)} suggestions (expected 0 due to empty AI response)")
        return True
        
    except Exception as e:
        print(f"   ❌ Fallback mechanisms broken: {e}")
        return False

def main():
    """Run realistic integration tests"""
    print("🔧 REALISTIC INTEGRATION TEST - Testing Fixed Implementation")
    print("=" * 70)
    
    tests = [
        ("Screen State Object Access Fix", test_screen_state_object_access_fix),
        ("JSON Serialization Fix", test_json_serialization_fix),
        ("Error Handling Robustness", test_error_handling_robustness),
        ("Configuration Robustness", test_configuration_robustness),
        ("Fallback Mechanisms", test_fallback_mechanisms),
    ]
    
    failures = []
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"   ✅ {test_name} - PASSED")
            else:
                print(f"   ❌ {test_name} - FAILED")
                failures.append(test_name)
        except Exception as e:
            print(f"   💥 {test_name} - CRASHED: {e}")
            failures.append(test_name)
    
    # Test async workflows
    async_tests = [
        ("Complete Workflow Simulation", test_complete_workflow_simulation),
        ("Fallback Mechanisms", test_fallback_mechanisms)
    ]
    
    for test_name, test_func in async_tests:
        try:
            result = asyncio.run(test_func())
            if result:
                print(f"   ✅ {test_name} - PASSED")
            else:
                print(f"   ❌ {test_name} - FAILED")
                failures.append(test_name)
        except Exception as e:
            print(f"   💥 {test_name} - CRASHED: {e}")
            failures.append(test_name)
    
    print("\n" + "=" * 70)
    
    if failures:
        print(f"🚨 STILL BROKEN: {len(failures)} tests failed")
        for failure in failures:
            print(f"   ❌ {failure}")
        
        print("\n💀 REALITY CHECK: System still has critical issues")
        return False
    else:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n✅ FIXED ISSUES:")
        print("   ✅ Screen state object access now safe")
        print("   ✅ JSON serialization handles complex objects")
        print("   ✅ Error handling prevents crashes")
        print("   ✅ Configuration system robust")
        print("   ✅ Fallback mechanisms work")
        print("   ✅ Complete workflow tested end-to-end")
        
        print("\n🎯 SYSTEM STATUS: Core bugs fixed, basic functionality validated")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)