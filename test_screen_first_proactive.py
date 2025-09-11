"""
Comprehensive tests for Screen-First Proactive AI System
Tests immediate next-step prediction based on current screen activity
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Import the screen-first components
from gum.services.screen_first_analyzer import (
    ScreenFirstAnalyzer, ScreenState, ScreenFirstValidator,
    ValidationResult, GroundingResult, ExecutionResult
)
from gum.services.proactive_engine import ProactiveEngine, parse_transcription_data
from gum.models import Observation, Proposition, Suggestion


class TestScreenFirstAnalyzer:
    """Test the screen-first analysis framework"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = ScreenFirstAnalyzer()
    
    def test_coding_task_identification(self):
        """Test identification of coding tasks"""
        transcription = """
        Application: VS Code
        Window Title: main.py
        Visible Text Content: def calculate_total(items):
            return sum(item['price'] for item in items)
        Error: TypeError: 'NoneType' object is not subscriptable
        Line: 45
        """
        
        context = parse_transcription_data(transcription)
        screen_state = self.analyzer.analyze_screen_state(transcription, context)
        
        assert screen_state.current_task == 'coding'
        assert screen_state.task_stage == 'stuck'  # Due to error
        assert 'debug_error' in screen_state.next_likely_actions
        assert 'current_error_blocking_progress' in screen_state.immediate_obstacles
        assert screen_state.urgency_level == 'immediate'
    
    def test_email_composition_prediction(self):
        """Test prediction during email composition"""
        transcription = """
        Application: Gmail
        Window: Compose
        Visible Text Content: Subject: Project Update
        To: sarah@company.com
        Body: Hi Sarah, I wanted to update you on the Q4 project...
        """
        
        context = parse_transcription_data(transcription)
        screen_state = self.analyzer.analyze_screen_state(transcription, context)
        
        assert screen_state.current_task == 'email'
        assert screen_state.task_stage == 'in_progress'
        assert 'send_email' in screen_state.next_likely_actions
        assert screen_state.urgency_level in ['soon', 'later']
    
    def test_presentation_slide_prediction(self):
        """Test prediction during presentation editing"""
        transcription = """
        Application: Canva
        Window: Q4 Report - Slide 3 of 12
        Visible Text Content: Revenue Analysis
        Chart: Bar chart showing Q1-Q3 data
        """
        
        context = parse_transcription_data(transcription)
        screen_state = self.analyzer.analyze_screen_state(transcription, context)
        
        assert screen_state.current_task == 'presentation'
        assert screen_state.task_stage == 'in_progress'
        assert 'work_on_slide_4' in screen_state.next_likely_actions
        assert screen_state.completion_percentage == 3/12  # Slide 3 of 12
    
    def test_task_completion_prediction(self):
        """Test prediction when task is nearly complete"""
        transcription = """
        Application: Word
        Document: Final Report.docx
        Visible Text Content: Conclusion section completed
        Status: Document ready for review
        """
        
        context = parse_transcription_data(transcription)
        screen_state = self.analyzer.analyze_screen_state(transcription, context)
        
        assert screen_state.current_task == 'writing'
        assert screen_state.task_stage == 'completing'
        assert 'final_review' in screen_state.next_likely_actions
        assert screen_state.urgency_level == 'soon'
        assert screen_state.completion_percentage > 0.8
    
    def test_context_switch_detection(self):
        """Test detection of imminent context switches"""
        transcription = """
        Application: VS Code
        Action: Saving file main.py
        Visible Text Content: File saved successfully
        User has been coding for 45 minutes
        """
        
        context = parse_transcription_data(transcription)
        screen_state = self.analyzer.analyze_screen_state(transcription, context)
        
        assert 'preparing_to_switch_apps' in screen_state.context_switch_signals
        assert 'commit_changes' in screen_state.next_likely_actions


class TestScreenFirstValidator:
    """Test the screen-first validation system"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = ScreenFirstValidator()
    
    def test_valid_screen_first_suggestion(self):
        """Test validation of a good screen-first suggestion"""
        suggestion = {
            "title": "I fixed your TypeError on line 45 in calculate_total()",
            "description": "I analyzed your TypeError and created the fix: change 'item['price']' to 'item.get('price', 0)'. Also generated 3 test cases.",
            "category": "screen_first_proactive",
            "rationale": "Based on current VS Code activity with TypeError on line 45 + predicted next step: debug and test",
            "priority": "high",
            "confidence": 9,
            "has_completed_work": True,
            "screen_prediction_type": "obstacle_prevention",
            "prediction_timeframe": "2_minutes",
            "completed_work": {
                "content": "def calculate_total(items):\n    return sum(item.get('price', 0) for item in items)\n\n# Test cases:\ntest_items = [{'price': 10}, {'price': 20}, {}]\nassert calculate_total(test_items) == 30",
                "content_type": "text",
                "preview": "Fixed TypeError with error handling and test cases",
                "action_label": "Apply Fix",
                "metadata": {
                    "current_screen_elements": ["VS Code", "main.py", "line 45", "TypeError"],
                    "predicted_next_steps": ["debug_error", "test_function", "run_code"],
                    "immediate_obstacles_prevented": ["TypeError blocking execution"],
                    "screen_context_used": "Current VS Code session with TypeError on line 45 in calculate_total function"
                }
            }
        }
        
        context = {
            "current_transcription": "Application: VS Code\nWindow: main.py\nError: TypeError on line 45",
            "current_app": "VS Code",
            "visible_content": "def calculate_total(items): return sum(item['price'] for item in items)",
            "screen_state": ScreenState(
                current_task="coding",
                task_stage="stuck",
                next_likely_actions=["debug_error", "test_function"],
                immediate_obstacles=["current_error_blocking_progress"],
                required_resources=["error_documentation"],
                workflow_stage="blocked",
                context_switch_signals=[],
                urgency_level="immediate",
                completion_percentage=0.3
            )
        }
        
        result = self.validator.validate_suggestion(suggestion, context)
        
        assert result.valid == True
        assert result.specificity_score >= 7
        assert result.grounding_score >= 4.0
    
    def test_invalid_generic_suggestion(self):
        """Test rejection of generic suggestions"""
        suggestion = {
            "title": "Debug your code",
            "description": "You should look into best practices for debugging and consider using helpful tools.",
            "category": "screen_first_proactive",
            "rationale": "Generic debugging advice",
            "priority": "medium",
            "confidence": 8,
            "has_completed_work": True,
            "completed_work": {
                "content": "Here are some debugging tips...",
                "content_type": "text",
                "preview": "Generic debugging advice",
                "action_label": "View Tips",
                "metadata": {
                    "current_screen_elements": [],
                    "predicted_next_steps": [],
                    "screen_context_used": "Generic advice"
                }
            }
        }
        
        context = {
            "current_transcription": "Application: VS Code\nWindow: main.py\nError: TypeError on line 45",
            "current_app": "VS Code",
            "visible_content": "def calculate_total(items): return sum(item['price'] for item in items)",
            "screen_state": ScreenState(
                current_task="coding",
                task_stage="stuck",
                next_likely_actions=["debug_error"],
                immediate_obstacles=["current_error_blocking_progress"],
                required_resources=[],
                workflow_stage="blocked",
                context_switch_signals=[],
                urgency_level="immediate",
                completion_percentage=0.3
            )
        }
        
        result = self.validator.validate_suggestion(suggestion, context)
        
        assert result.valid == False
        assert "generic phrases" in result.reason.lower()


class TestProactiveEngineIntegration:
    """Test the integrated screen-first proactive engine"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = None
    
    async def setup_engine(self):
        """Setup engine with mocked dependencies"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.enable_screen_first_analysis = True
        mock_config.enable_enhanced_validation = True
        mock_config.max_retries = 1
        mock_config.retry_delay_seconds = 0.1
        mock_config.timeout_seconds = 30.0
        mock_config.min_specificity_score = 7
        
        self.engine = ProactiveEngine(config=mock_config)
        
        # Mock AI client
        mock_ai_client = AsyncMock()
        self.engine.ai_client = mock_ai_client
        self.engine._started = True
        
        return mock_ai_client
    
    @pytest.mark.asyncio
    async def test_screen_first_coding_scenario(self):
        """Test complete screen-first flow for coding scenario"""
        mock_ai_client = await self.setup_engine()
        
        # Mock AI response for coding error scenario
        ai_response = json.dumps({
            "immediate_work": [{
                "title": "I fixed your TypeError on line 45 in calculate_total()",
                "description": "I analyzed your TypeError and created the fix with error handling and test cases.",
                "category": "screen_first_proactive",
                "rationale": "Based on current VS Code activity with TypeError on line 45 + predicted next step: debug and test",
                "priority": "high",
                "confidence": 9,
                "has_completed_work": True,
                "screen_prediction_type": "obstacle_prevention",
                "prediction_timeframe": "2_minutes",
                "completed_work": {
                    "content": "def calculate_total(items):\n    return sum(item.get('price', 0) for item in items)",
                    "content_type": "text",
                    "preview": "Fixed TypeError with error handling",
                    "action_label": "Apply Fix",
                    "metadata": {
                        "current_screen_elements": ["VS Code", "main.py", "line 45", "TypeError"],
                        "predicted_next_steps": ["debug_error", "test_function", "run_code"],
                        "immediate_obstacles_prevented": ["TypeError blocking execution"],
                        "screen_context_used": "Current VS Code session with TypeError"
                    }
                }
            }]
        })
        
        mock_ai_client.text_completion.return_value = ai_response
        
        # Test transcription
        transcription = """
        Application: VS Code
        Window Title: main.py
        Visible Text Content: def calculate_total(items):
            return sum(item['price'] for item in items)
        Error: TypeError: 'NoneType' object is not subscriptable
        Line: 45
        """
        
        # Mock session and database operations
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Test the analysis
        suggestions = await self.engine._analyze_screen_activity(transcription, 1, mock_session)
        
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        
        assert suggestion["category"] == "screen_first_proactive"
        assert suggestion["has_completed_work"] == True
        assert "TypeError" in suggestion["title"]
        assert "line 45" in suggestion["title"]
        assert suggestion["screen_first_analysis"] == True
        assert suggestion["executor_type"] == "screen_first_proactive"
    
    @pytest.mark.asyncio
    async def test_screen_first_email_scenario(self):
        """Test screen-first flow for email composition"""
        mock_ai_client = await self.setup_engine()
        
        # Mock AI response for email scenario
        ai_response = json.dumps({
            "immediate_work": [{
                "title": "I drafted your project update email to Sarah",
                "description": "I completed your email with status updates, milestones, and action items based on your project context.",
                "category": "screen_first_proactive",
                "rationale": "Based on Gmail compose activity to sarah@company.com + predicted next step: send professional update",
                "priority": "high",
                "confidence": 9,
                "has_completed_work": True,
                "screen_prediction_type": "next_action",
                "prediction_timeframe": "30_seconds",
                "completed_work": {
                    "content": "Subject: Q4 Project Update\n\nHi Sarah,\n\nI wanted to provide you with an update on our Q4 project progress...",
                    "content_type": "text",
                    "preview": "Professional project update email ready to send",
                    "action_label": "Copy Email",
                    "metadata": {
                        "current_screen_elements": ["Gmail", "Compose", "sarah@company.com", "Project Update"],
                        "predicted_next_steps": ["send_email", "add_attachment", "schedule_send"],
                        "immediate_obstacles_prevented": ["Missing professional formatting"],
                        "screen_context_used": "Gmail compose window with recipient and subject"
                    }
                }
            }]
        })
        
        mock_ai_client.text_completion.return_value = ai_response
        
        transcription = """
        Application: Gmail
        Window: Compose
        Visible Text Content: Subject: Project Update
        To: sarah@company.com
        Body: Hi Sarah, I wanted to update you on the Q4 project...
        """
        
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        
        suggestions = await self.engine._analyze_screen_activity(transcription, 1, mock_session)
        
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        
        assert "email" in suggestion["title"].lower()
        assert "sarah" in suggestion["title"].lower()
        assert suggestion["screen_prediction_type"] == "next_action"
        assert suggestion["prediction_timeframe"] == "30_seconds"
    
    @pytest.mark.asyncio
    async def test_presentation_slide_scenario(self):
        """Test screen-first flow for presentation editing"""
        mock_ai_client = await self.setup_engine()
        
        ai_response = json.dumps({
            "immediate_work": [{
                "title": "I created slides 4-7 for your Q4 Report",
                "description": "I generated the next 4 slides: Market Analysis, Cost Breakdown, Profit Margins, and Q1 Projections based on your revenue chart.",
                "category": "screen_first_proactive",
                "rationale": "Based on Canva Q4 Report slide 3 revenue work + predicted next step: continue with analysis slides",
                "priority": "high",
                "confidence": 9,
                "has_completed_work": True,
                "screen_prediction_type": "workflow_acceleration",
                "prediction_timeframe": "5_minutes",
                "completed_work": {
                    "content": "Slide 4: Market Analysis\n- Key market trends\n- Competitive landscape\n\nSlide 5: Cost Breakdown...",
                    "content_type": "markdown",
                    "preview": "Next 4 slides with market analysis and projections",
                    "action_label": "Import Slides",
                    "metadata": {
                        "current_screen_elements": ["Canva", "Q4 Report", "Slide 3", "Revenue Analysis"],
                        "predicted_next_steps": ["work_on_slide_4", "add_chart", "format_slide"],
                        "immediate_obstacles_prevented": ["Content planning for remaining slides"],
                        "screen_context_used": "Canva presentation slide 3 of 12 with revenue focus"
                    }
                }
            }]
        })
        
        mock_ai_client.text_completion.return_value = ai_response
        
        transcription = """
        Application: Canva
        Window: Q4 Report - Slide 3 of 12
        Visible Text Content: Revenue Analysis
        Chart: Bar chart showing Q1-Q3 data
        User working on revenue visualization
        """
        
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        
        suggestions = await self.engine._analyze_screen_activity(transcription, 1, mock_session)
        
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        
        assert "slides 4-7" in suggestion["title"].lower()
        assert "q4 report" in suggestion["title"].lower()
        assert suggestion["screen_prediction_type"] == "workflow_acceleration"


class TestScreenFirstValidation:
    """Test screen-first validation rules"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = ScreenFirstValidator()
    
    def test_specificity_scoring(self):
        """Test screen-first specificity scoring"""
        suggestion = {
            "title": "I fixed your TypeError on line 45 in main.py",
            "description": "Based on your VS Code session, I created the fix for calculate_total() function with error handling.",
            "category": "screen_first_proactive",
            "rationale": "Current screen shows TypeError on line 45",
            "priority": "high",
            "confidence": 9,
            "has_completed_work": True,
            "prediction_timeframe": "2_minutes",
            "completed_work": {
                "content": "Fixed code here",
                "content_type": "text",
                "preview": "Error fix",
                "action_label": "Apply",
                "metadata": {
                    "current_screen_elements": ["VS Code", "main.py", "line 45"],
                    "predicted_next_steps": ["debug_error"],
                    "screen_context_used": "VS Code TypeError context"
                }
            }
        }
        
        context = {
            "current_app": "VS Code",
            "visible_content": "def calculate_total(items): return sum(item['price'] for item in items)",
            "screen_state": ScreenState(
                current_task="coding",
                task_stage="stuck",
                next_likely_actions=["debug_error", "test_function"],
                immediate_obstacles=["current_error_blocking_progress"],
                required_resources=[],
                workflow_stage="blocked",
                context_switch_signals=[],
                urgency_level="immediate",
                completion_percentage=0.3
            )
        }
        
        score = self.validator._calculate_screen_specificity_score(suggestion, context)
        
        # Should score high due to:
        # +2 for app reference (VS Code)
        # +2 for visible content reference (calculate_total, TypeError)
        # +2 for next action prediction (debug_error)
        # +1 for immediate timeframe (2_minutes)
        # +1 for task stage appropriateness (stuck -> debug)
        assert score >= 7
    
    def test_grounding_evidence_validation(self):
        """Test anti-hallucination grounding validation"""
        suggestion = {
            "title": "I fixed your TypeError on line 45",
            "description": "Based on your VS Code session with calculate_total() function, I created the error handling fix."
        }
        
        context = {
            "current_transcription": "Application: VS Code Window: main.py Error: TypeError line 45 calculate_total",
            "current_app": "VS Code",
            "visible_content": "def calculate_total(items): return sum(item['price'] for item in items)",
            "screen_state": ScreenState(
                current_task="coding",
                task_stage="stuck",
                next_likely_actions=["debug_error"],
                immediate_obstacles=[],
                required_resources=[],
                workflow_stage="blocked",
                context_switch_signals=[],
                urgency_level="immediate",
                completion_percentage=0.3
            )
        }
        
        result = self.validator._validate_grounding_evidence(suggestion, context)
        
        assert result.valid == True
        assert result.grounding_score >= 4.0
        assert any("VS Code" in evidence for evidence in result.evidence_found)
        assert any("calculate_total" in evidence for evidence in result.evidence_found)


class TestEndToEndScreenFirst:
    """Test complete end-to-end screen-first proactive system"""
    
    @pytest.mark.asyncio
    async def test_complete_coding_workflow(self):
        """Test complete workflow from observation to suggestion delivery"""
        
        # Mock all dependencies
        with patch('gum.services.proactive_engine.get_unified_client') as mock_get_client, \
             patch('gum.services.proactive_engine.get_rate_limiter') as mock_get_limiter:
            
            # Setup mocks
            mock_ai_client = AsyncMock()
            mock_get_client.return_value = mock_ai_client
            
            mock_rate_limiter = AsyncMock()
            mock_rate_limiter.can_generate_suggestions.return_value = True
            mock_get_limiter.return_value = mock_rate_limiter
            
            # Mock AI response
            ai_response = json.dumps({
                "immediate_work": [{
                    "title": "I fixed your TypeError on line 45 in calculate_total()",
                    "description": "I analyzed your TypeError and created the fix with error handling and test cases ready to use.",
                    "category": "screen_first_proactive",
                    "rationale": "Based on current VS Code activity with TypeError on line 45 + predicted next step: debug and test",
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
                            "current_screen_elements": ["VS Code", "main.py", "line 45", "TypeError"],
                            "predicted_next_steps": ["debug_error", "test_function", "run_code"],
                            "immediate_obstacles_prevented": ["TypeError blocking execution"],
                            "screen_context_used": "Current VS Code session with TypeError on line 45"
                        }
                    }
                }]
            })
            
            mock_ai_client.text_completion.return_value = ai_response
            
            # Create test observation
            observation = Observation(
                id=1,
                observer_name="screen",
                content="""
                Application: VS Code
                Window Title: main.py
                Visible Text Content: def calculate_total(items):
                    return sum(item['price'] for item in items)
                Error: TypeError: 'NoneType' object is not subscriptable
                Line: 45
                User is debugging the calculate_total function
                """,
                content_type="input_text",
                created_at=datetime.now(timezone.utc)
            )
            
            # Mock session
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = observation
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()
            
            # Test the complete flow
            suggestions = await self.engine.process_observation(1, mock_session)
            
            # Validate results
            assert suggestions is not None
            assert len(suggestions) == 1
            
            suggestion = suggestions[0]
            assert suggestion["category"] == "screen_first_proactive"
            assert suggestion["has_completed_work"] == True
            assert "TypeError" in suggestion["title"]
            assert "line 45" in suggestion["title"]
            assert suggestion["screen_first_analysis"] == True
            
            # Validate completed work
            completed_work = suggestion["completed_work"]
            assert "def calculate_total" in completed_work["content"]
            assert "get('price', 0)" in completed_work["content"]  # Error handling fix
            
            # Validate metadata
            metadata = completed_work["metadata"]
            assert "VS Code" in metadata["current_screen_elements"]
            assert "debug_error" in metadata["predicted_next_steps"]


if __name__ == "__main__":
    # Run basic tests
    import sys
    
    async def run_basic_tests():
        """Run basic functionality tests"""
        print("🧪 Testing Screen-First Proactive AI System...")
        
        # Test 1: Screen state analysis
        analyzer = ScreenFirstAnalyzer()
        
        coding_transcription = """
        Application: VS Code
        Window: main.py
        Visible Text: def calculate_total(items): return sum(item['price'] for item in items)
        Error: TypeError on line 45
        """
        
        context = parse_transcription_data(coding_transcription)
        screen_state = analyzer.analyze_screen_state(coding_transcription, context)
        
        print(f"✅ Coding task identified: {screen_state.current_task}")
        print(f"✅ Task stage detected: {screen_state.task_stage}")
        print(f"✅ Next actions predicted: {screen_state.next_likely_actions}")
        print(f"✅ Urgency level: {screen_state.urgency_level}")
        
        # Test 2: Validation
        validator = ScreenFirstValidator()
        
        good_suggestion = {
            "title": "I fixed your TypeError on line 45",
            "description": "Based on your VS Code session, I created the fix for calculate_total() with error handling.",
            "category": "screen_first_proactive",
            "rationale": "Current screen shows TypeError",
            "priority": "high",
            "confidence": 9,
            "has_completed_work": True,
            "completed_work": {
                "content": "Fixed code",
                "content_type": "text",
                "preview": "Error fix",
                "action_label": "Apply",
                "metadata": {
                    "current_screen_elements": ["VS Code", "line 45"],
                    "predicted_next_steps": ["debug_error"],
                    "screen_context_used": "VS Code error context"
                }
            }
        }
        
        enhanced_context = {
            "current_app": "VS Code",
            "visible_content": "def calculate_total TypeError line 45",
            "screen_state": screen_state
        }
        
        validation = validator.validate_suggestion(good_suggestion, enhanced_context)
        print(f"✅ Validation result: {validation.valid} (score: {validation.specificity_score})")
        
        print("\n🎯 Screen-First Proactive AI System tests completed successfully!")
    
    # Run the tests
    asyncio.run(run_basic_tests())