"""
Screen-First Analysis Framework
Analyzes current screen state for immediate next-step predictions (30 seconds to 5 minutes ahead)
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ScreenState:
    """Represents the current state of user's screen for proactive predictions"""
    current_task: str
    task_stage: str  # "starting", "in_progress", "completing", "stuck"
    next_likely_actions: List[str]
    immediate_obstacles: List[str]
    required_resources: List[str]
    workflow_stage: str
    context_switch_signals: List[str]
    urgency_level: str  # "immediate", "soon", "later"
    completion_percentage: float

@dataclass
class ValidationResult:
    """Result of screen-first suggestion validation"""
    valid: bool
    reason: str
    specificity_score: Optional[int] = None
    grounding_score: Optional[float] = None
    execution_readiness: Optional[float] = None

@dataclass
class GroundingResult:
    """Result of anti-hallucination grounding validation"""
    valid: bool
    grounding_score: float
    evidence_found: List[str]
    reason: str

@dataclass
class ExecutionResult:
    """Result of execution readiness validation"""
    valid: bool
    readiness_score: float
    reason: str

class ScreenFirstAnalyzer:
    """Analyzes current screen state for immediate next-step predictions"""
    
    def __init__(self):
        self.task_patterns = {
            'coding': {
                'indicators': ['def ', 'class ', 'import ', 'function', 'variable', 'error', 'debug', 'python', 'javascript', 'typescript'],
                'next_actions': ['run_code', 'test_function', 'debug_error', 'commit_changes', 'add_docstring'],
                'obstacles': ['syntax_error', 'missing_import', 'undefined_variable', 'type_error']
            },
            'writing': {
                'indicators': ['document', 'paragraph', 'sentence', 'draft', 'edit', 'word', 'google docs'],
                'next_actions': ['save_document', 'spell_check', 'format_text', 'share_document', 'add_references'],
                'obstacles': ['formatting_issues', 'word_count', 'citation_needed', 'grammar_errors']
            },
            'email': {
                'indicators': ['compose', 'reply', 'subject', 'recipient', '@', 'gmail', 'outlook'],
                'next_actions': ['send_email', 'add_attachment', 'schedule_send', 'save_draft', 'add_recipient'],
                'obstacles': ['missing_attachment', 'unclear_subject', 'wrong_recipient', 'missing_signature']
            },
            'presentation': {
                'indicators': ['slide', 'presentation', 'chart', 'graph', 'bullet', 'canva', 'powerpoint'],
                'next_actions': ['next_slide', 'add_chart', 'format_slide', 'present', 'add_animation'],
                'obstacles': ['missing_data', 'formatting_inconsistency', 'slide_order', 'image_quality']
            },
            'data_analysis': {
                'indicators': ['data', 'chart', 'graph', 'analysis', 'statistics', 'excel', 'csv'],
                'next_actions': ['create_visualization', 'export_data', 'generate_report', 'clean_data'],
                'obstacles': ['data_quality', 'missing_values', 'calculation_error', 'format_issues']
            },
            'web_browsing': {
                'indicators': ['browser', 'website', 'url', 'search', 'chrome', 'safari', 'firefox'],
                'next_actions': ['bookmark_page', 'take_notes', 'share_link', 'download_content'],
                'obstacles': ['slow_loading', 'broken_links', 'paywall', 'mobile_compatibility']
            },
            'design': {
                'indicators': ['design', 'figma', 'sketch', 'photoshop', 'color', 'layout'],
                'next_actions': ['export_design', 'share_prototype', 'create_variant', 'add_components'],
                'obstacles': ['color_contrast', 'alignment_issues', 'missing_assets', 'version_conflicts']
            }
        }
    
    def analyze_screen_state(self, transcription: str, context: Dict[str, Any]) -> ScreenState:
        """Analyze current screen for immediate prediction opportunities"""
        
        # Extract basic screen elements
        current_app = context.get('current_app', 'Unknown')
        visible_content = context.get('visible_content', '')
        active_window = context.get('active_window', '')
        
        # Identify current task type
        current_task = self._identify_current_task(transcription, current_app)
        
        # Determine task stage
        task_stage = self._determine_task_stage(transcription, visible_content)
        
        # Predict next actions
        next_actions = self._predict_next_actions(current_task, transcription, task_stage)
        
        # Identify immediate obstacles
        obstacles = self._identify_immediate_obstacles(current_task, transcription)
        
        # Determine required resources
        resources = self._identify_required_resources(current_task, transcription, next_actions)
        
        # Detect context switch signals
        context_switches = self._detect_context_switches(transcription, current_app)
        
        # Calculate urgency and completion
        urgency = self._calculate_urgency(task_stage, obstacles)
        completion = self._estimate_completion_percentage(current_task, transcription)
        
        return ScreenState(
            current_task=current_task,
            task_stage=task_stage,
            next_likely_actions=next_actions,
            immediate_obstacles=obstacles,
            required_resources=resources,
            workflow_stage=self._determine_workflow_stage(current_task, task_stage),
            context_switch_signals=context_switches,
            urgency_level=urgency,
            completion_percentage=completion
        )
    
    def _identify_current_task(self, transcription: str, current_app: str) -> str:
        """Identify what task the user is currently performing with semantic understanding"""

        transcription_lower = transcription.lower()
        app_lower = current_app.lower()

        # SEMANTIC TASK IDENTIFICATION: Use context and intent signals
        task_scores = {}

        # 1. App-based identification with semantic context
        app_task_mapping = {
            'coding': ['vscode', 'pycharm', 'sublime', 'atom', 'intellij', 'xcode'],
            'writing': ['word', 'docs', 'notion', 'obsidian', 'writer'],
            'email': ['gmail', 'outlook', 'mail', 'thunderbird'],
            'presentation': ['canva', 'powerpoint', 'keynote', 'slides', 'prezi'],
            'data_analysis': ['excel', 'sheets', 'tableau', 'r_studio', 'jupyter'],
            'web_browsing': ['chrome', 'safari', 'firefox', 'edge', 'opera'],
            'design': ['figma', 'sketch', 'photoshop', 'illustrator', 'indesign']
        }

        for task, apps in app_task_mapping.items():
            if any(app in app_lower for app in apps):
                task_scores[task] = 3  # Strong app-based signal

        # 2. Content-based semantic analysis
        semantic_indicators = {
            'coding': {
                'strong': ['def ', 'class ', 'function', 'import ', 'debug', 'error', 'syntax', 'compile'],
                'medium': ['variable', 'method', 'api', 'database', 'test', 'run', 'execute'],
                'weak': ['code', 'programming', 'script', 'algorithm']
            },
            'writing': {
                'strong': ['paragraph', 'sentence', 'draft', 'edit', 'revise', 'proofread'],
                'medium': ['document', 'chapter', 'outline', 'summary', 'content'],
                'weak': ['write', 'text', 'author', 'publish']
            },
            'email': {
                'strong': ['compose', 'reply', 'subject', 'recipient', 'attachment', 'send'],
                'medium': ['message', 'inbox', 'draft', 'forward', 'cc', 'bcc'],
                'weak': ['communication', 'correspondence']
            },
            'presentation': {
                'strong': ['slide', 'presentation', 'chart', 'graph', 'audience', 'pitch'],
                'medium': ['visual', 'design', 'layout', 'transition', 'animation'],
                'weak': ['show', 'display', 'present']
            },
            'data_analysis': {
                'strong': ['data', 'analysis', 'statistics', 'chart', 'graph', 'dataset'],
                'medium': ['visualization', 'insight', 'trend', 'correlation', 'metric'],
                'weak': ['analyze', 'report', 'dashboard']
            },
            'web_browsing': {
                'strong': ['search', 'website', 'url', 'browse', 'navigate', 'link'],
                'medium': ['page', 'site', 'web', 'internet', 'online'],
                'weak': ['browse', 'surf', 'visit']
            },
            'design': {
                'strong': ['design', 'layout', 'color', 'font', 'style', 'mockup'],
                'medium': ['creative', 'visual', 'aesthetic', 'brand', 'prototype'],
                'weak': ['art', 'graphic', 'image']
            }
        }

        for task, indicators in semantic_indicators.items():
            score = 0
            # Strong indicators (3 points each)
            score += sum(3 for ind in indicators['strong'] if ind in transcription_lower)
            # Medium indicators (2 points each)
            score += sum(2 for ind in indicators['medium'] if ind in transcription_lower)
            # Weak indicators (1 point each)
            score += sum(1 for ind in indicators['weak'] if ind in transcription_lower)

            if score > 0:
                task_scores[task] = task_scores.get(task, 0) + score

        # 3. Context and intent analysis
        intent_signals = {
            'exploratory': ['looking', 'checking', 'browsing', 'curious', 'wondering', 'exploring'],
            'focused': ['working on', 'creating', 'building', 'developing', 'implementing'],
            'problem_solving': ['fix', 'debug', 'solve', 'issue', 'problem', 'error', 'troubleshoot'],
            'communication': ['discuss', 'share', 'collaborate', 'coordinate', 'meeting'],
            'learning': ['learn', 'study', 'understand', 'research', 'tutorial']
        }

        for intent, signals in intent_signals.items():
            if any(signal in transcription_lower for signal in signals):
                # Adjust task scores based on intent
                if intent == 'exploratory':
                    # Reduce confidence in specific tasks for exploratory behavior
                    for task in task_scores:
                        task_scores[task] *= 0.7
                elif intent == 'problem_solving':
                    # Boost coding/debugging tasks
                    if 'coding' in task_scores:
                        task_scores['coding'] += 2

        # 4. Determine best task with confidence threshold
        if task_scores:
            best_task = max(task_scores.items(), key=lambda x: x[1])
            if best_task[1] >= 2:  # Minimum confidence threshold
                return best_task[0]

        # 5. Fallback with improved semantic analysis
        task_result = 'general_work'

        # USER INTENT DETECTION: Classify user behavior patterns
        user_intent = self._detect_user_intent(transcription, current_app, task_result)

        # Adjust task identification based on intent
        if user_intent == 'exploratory' and task_result != 'general_work':
            # For exploratory behavior, be more conservative with task identification
            task_result = 'general_work'
            logger.info(f"🔍 INTENT-ADJUSTED TASK: Changed to 'general_work' due to exploratory intent")
        elif user_intent == 'focused' and task_result == 'general_work':
            # For focused behavior, try harder to identify specific tasks
            logger.info(f"🔍 INTENT-ADJUSTED TASK: Maintaining specific task due to focused intent")

        # DIAGNOSTIC LOGGING: Track intent-aware task identification
        if task_result == 'general_work':
            logger.warning(f"🔍 INTENT-AWARE TASK IDENTIFICATION: Could not identify specific task")
            logger.warning(f"   Transcription: '{transcription[:100]}...'")
            logger.warning(f"   App: {current_app}, Intent: {user_intent}")
            logger.warning("   💡 INTENT ANALYSIS: Task identification adjusted based on user intent")

        return task_result
    
    def _determine_task_stage(self, transcription: str, visible_content: str) -> str:
        """Determine what stage of the task the user is in"""
        
        combined_content = f"{transcription} {visible_content}".lower()
        
        # Check for stuck indicators
        stuck_indicators = ['error', 'exception', 'failed', 'not working', 'broken', 'issue', 'problem']
        if any(indicator in combined_content for indicator in stuck_indicators):
            return 'stuck'
        
        # Check for completion indicators
        completion_indicators = ['done', 'finished', 'complete', 'ready', 'final', 'submit', 'send']
        if any(indicator in combined_content for indicator in completion_indicators):
            return 'completing'
        
        # Check for starting indicators
        starting_indicators = ['new', 'create', 'start', 'begin', 'setup', 'initialize', 'blank']
        if any(indicator in combined_content for indicator in starting_indicators):
            return 'starting'
        
        # Default to in progress
        return 'in_progress'
    
    def _predict_next_actions(self, task_type: str, transcription: str, stage: str) -> List[str]:
        """Predict what user will do in next 2-5 minutes based on current screen"""
        
        predictions = []
        transcription_lower = transcription.lower()
        
        if task_type == 'coding':
            if 'error' in transcription_lower or 'exception' in transcription_lower:
                predictions.extend(['debug_error', 'fix_syntax', 'run_tests'])
            elif 'def ' in transcription or 'function' in transcription_lower:
                predictions.extend(['test_function', 'add_docstring', 'run_code'])
            elif stage == 'completing':
                predictions.extend(['commit_changes', 'push_code', 'create_pull_request'])
            elif 'import' in transcription_lower:
                predictions.extend(['install_package', 'check_documentation', 'run_code'])
        
        elif task_type == 'email':
            if 'compose' in transcription_lower:
                if '@' not in transcription:
                    predictions.append('add_recipient')
                if 'subject:' not in transcription_lower:
                    predictions.append('add_subject')
                predictions.extend(['send_email', 'save_draft', 'add_attachment'])
            elif 'reply' in transcription_lower:
                predictions.extend(['send_reply', 'forward_email', 'schedule_send'])
        
        elif task_type == 'presentation':
            slide_match = re.search(r'slide\s+(\d+)', transcription_lower)
            if slide_match:
                current_slide = int(slide_match.group(1))
                predictions.append(f'work_on_slide_{current_slide + 1}')
            predictions.extend(['add_chart', 'format_slide', 'rehearse_presentation'])
        
        elif task_type == 'writing':
            if stage == 'in_progress':
                predictions.extend(['save_document', 'spell_check', 'add_references'])
            elif stage == 'completing':
                predictions.extend(['final_review', 'export_pdf', 'share_document'])
        
        elif task_type == 'data_analysis':
            if 'chart' in transcription_lower or 'graph' in transcription_lower:
                predictions.extend(['format_chart', 'add_labels', 'export_visualization'])
            predictions.extend(['create_summary', 'generate_insights', 'export_data'])
        
        elif task_type == 'web_browsing':
            if 'search' in transcription_lower:
                predictions.extend(['refine_search', 'bookmark_results', 'take_notes'])
            predictions.extend(['bookmark_page', 'share_link', 'download_content'])
        
        elif task_type == 'design':
            predictions.extend(['create_variant', 'export_assets', 'share_prototype', 'add_components'])
        
        return predictions[:3]  # Return top 3 predictions
    
    def _identify_immediate_obstacles(self, task_type: str, transcription: str) -> List[str]:
        """Identify problems user will hit in next 2-5 minutes"""
        
        obstacles = []
        transcription_lower = transcription.lower()
        
        # Common error patterns
        if 'error' in transcription_lower:
            obstacles.append('current_error_blocking_progress')
        
        if task_type == 'coding':
            if 'undefined' in transcription_lower:
                obstacles.append('undefined_variable_or_function')
            if 'import' in transcription and 'error' in transcription_lower:
                obstacles.append('missing_dependency')
            if 'syntax' in transcription_lower:
                obstacles.append('syntax_error_preventing_execution')
            if 'type' in transcription_lower and 'error' in transcription_lower:
                obstacles.append('type_error_needs_fixing')
        
        elif task_type == 'email':
            if 'compose' in transcription_lower and '@' not in transcription:
                obstacles.append('missing_recipient_address')
            if len(transcription) > 1000:  # Very long email
                obstacles.append('email_too_long_needs_editing')
        
        elif task_type == 'presentation':
            if 'chart' in transcription_lower and 'data' not in transcription_lower:
                obstacles.append('missing_data_for_chart')
            if re.search(r'slide\s+\d+.*slide\s+\d+', transcription_lower):
                obstacles.append('inconsistent_slide_formatting')
        
        elif task_type == 'writing':
            if 'word count' in transcription_lower:
                obstacles.append('document_length_requirements')
            if 'citation' in transcription_lower or 'reference' in transcription_lower:
                obstacles.append('missing_citations_or_references')
        
        return obstacles
    
    def _identify_required_resources(self, task_type: str, transcription: str, next_actions: List[str]) -> List[str]:
        """Identify tools/info user will need for their next actions"""
        
        resources = []
        
        for action in next_actions:
            if action == 'debug_error':
                resources.extend(['error_documentation', 'stack_trace_analysis', 'debugging_tools'])
            elif action == 'send_email':
                resources.extend(['recipient_verification', 'attachment_check', 'subject_optimization'])
            elif action == 'add_chart':
                resources.extend(['chart_data', 'visualization_templates', 'color_schemes'])
            elif action == 'test_function':
                resources.extend(['test_cases', 'mock_data', 'assertion_examples'])
            elif action == 'save_document':
                resources.extend(['backup_location', 'version_control', 'format_options'])
        
        # Task-specific resources
        transcription_lower = transcription.lower()
        
        if task_type == 'coding':
            if 'api' in transcription_lower:
                resources.append('api_documentation')
            if 'database' in transcription_lower:
                resources.append('database_schema')
            if 'test' in transcription_lower:
                resources.append('testing_framework_docs')
        
        elif task_type == 'writing':
            if 'citation' in transcription_lower or 'reference' in transcription_lower:
                resources.append('citation_format_guide')
            if 'word count' in transcription_lower:
                resources.append('document_statistics')
        
        elif task_type == 'presentation':
            if 'chart' in transcription_lower:
                resources.append('data_visualization_best_practices')
            if 'design' in transcription_lower:
                resources.append('presentation_templates')
        
        return list(set(resources))  # Remove duplicates
    
    def _detect_context_switches(self, transcription: str, current_app: str) -> List[str]:
        """Detect signals that user is about to switch apps or tasks"""
        
        switch_signals = []
        transcription_lower = transcription.lower()
        
        # App switching indicators
        if 'save' in transcription_lower and current_app in ['VS Code', 'Word', 'Google Docs']:
            switch_signals.append('preparing_to_switch_apps')
        
        # Task completion indicators
        completion_words = ['done', 'finished', 'complete', 'ready', 'final']
        if any(word in transcription_lower for word in completion_words):
            switch_signals.append('task_nearing_completion')
        
        # Communication indicators (switching to email/chat)
        communication_words = ['email', 'message', 'call', 'meeting', 'send']
        if any(word in transcription_lower for word in communication_words):
            switch_signals.append('preparing_communication')
        
        # Research indicators (switching to browser)
        research_words = ['search', 'look up', 'find', 'research', 'documentation']
        if any(word in transcription_lower for word in research_words):
            switch_signals.append('preparing_research')
        
        return switch_signals
    
    def _calculate_urgency(self, task_stage: str, obstacles: List[str]) -> str:
        """Calculate how urgently user needs assistance"""
        
        if obstacles and any('error' in obstacle.lower() for obstacle in obstacles):
            return 'immediate'  # Errors need immediate attention
        
        if task_stage == 'stuck':
            return 'immediate'
        
        if task_stage == 'completing':
            return 'soon'  # Help with final steps
        
        if task_stage == 'starting':
            return 'soon'  # Help with setup
        
        return 'later'  # In progress, no immediate issues
    
    def _estimate_completion_percentage(self, task_type: str, transcription: str) -> float:
        """Estimate how complete the current task is"""
        
        transcription_lower = transcription.lower()
        
        # Look for explicit completion indicators
        if any(word in transcription_lower for word in ['done', 'finished', 'complete']):
            return 0.95
        
        if any(word in transcription_lower for word in ['almost', 'nearly', 'final']):
            return 0.85
        
        # Task-specific completion estimation
        if task_type == 'presentation':
            slide_match = re.search(r'slide\s+(\d+)\s+of\s+(\d+)', transcription_lower)
            if slide_match:
                current_slide = int(slide_match.group(1))
                total_slides = int(slide_match.group(2))
                return current_slide / total_slides
        
        if task_type == 'coding':
            if 'test' in transcription_lower and 'pass' in transcription_lower:
                return 0.8
            elif 'error' in transcription_lower:
                return 0.3
        
        if task_type == 'writing':
            if 'word count' in transcription_lower:
                # Try to extract word count progress
                word_match = re.search(r'(\d+)\s*\/\s*(\d+)\s*words?', transcription_lower)
                if word_match:
                    current_words = int(word_match.group(1))
                    target_words = int(word_match.group(2))
                    return min(current_words / target_words, 1.0)
        
        # Default estimation based on task stage
        stage_completion = {
            'starting': 0.1,
            'in_progress': 0.5,
            'completing': 0.9,
            'stuck': 0.3
        }
        
        return stage_completion.get(self._determine_task_stage(transcription, ''), 0.5)
    
    def _determine_workflow_stage(self, task_type: str, task_stage: str) -> str:
        """Determine the overall workflow stage"""
        
        if task_stage == 'stuck':
            return 'blocked'
        elif task_stage == 'completing':
            return 'finalizing'
        elif task_stage == 'starting':
            return 'initiating'
        else:
            return 'executing'


class ScreenFirstValidator:
    """Enhanced validation with screen-first specificity requirements"""
    
    def __init__(self):
        self.min_specificity_score = 7  # Raised for screen-first standards
        self.required_evidence_types = [
            'specific_apps',
            'specific_content', 
            'screen_activity',
            'next_step_prediction'
        ]
    
    def validate_suggestion(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Comprehensive validation with screen-first anti-hallucination checks"""

        # CONTEXT SENSITIVITY VALIDATION
        suggestion_text = f"{suggestion.get('title', '')} {suggestion.get('description', '')}"
        current_app = context.get('current_app', 'Unknown')
        visible_content = context.get('visible_content', '')
        transcription = context.get('current_transcription', '')

        # Check 1: Application Context Sensitivity
        app_context_issues = self._validate_application_context(suggestion_text, current_app, transcription)
        if app_context_issues:
            for issue in app_context_issues:
                logger.warning(f"🔍 CONTEXT SENSITIVITY ISSUE: {issue}")
                logger.warning(f"   Suggestion: '{suggestion_text[:100]}...'")
                logger.warning(f"   App: {current_app}, Transcription: '{transcription[:100]}...'")

        # Check 2: Content Type Sensitivity (Personal vs Professional)
        content_sensitivity_issues = self._validate_content_sensitivity(suggestion_text, transcription, visible_content)
        if content_sensitivity_issues:
            for issue in content_sensitivity_issues:
                logger.warning(f"🔍 CONTENT SENSITIVITY ISSUE: {issue}")
                logger.warning(f"   Suggestion: '{suggestion_text[:100]}...'")
                logger.warning(f"   Content: '{visible_content[:100]}...'")

        # Check 3: User Intent Awareness
        intent_issues = self._validate_user_intent(suggestion_text, transcription, context)
        if intent_issues:
            for issue in intent_issues:
                logger.warning(f"🔍 INTENT AWARENESS ISSUE: {issue}")
                logger.warning(f"   Suggestion: '{suggestion_text[:100]}...'")
                logger.warning(f"   Transcription: '{transcription[:100]}...'")

        # Layer 1: Structural validation
        if not self._validate_structure(suggestion):
            return ValidationResult(valid=False, reason="Invalid structure")
        
        # Layer 2: Screen-first specificity scoring
        specificity_score = self._calculate_screen_specificity_score(suggestion, context)
        if specificity_score < self.min_specificity_score:
            return ValidationResult(valid=False, reason=f"Specificity too low: {specificity_score}/10")
        
        # Layer 3: Anti-hallucination validation
        hallucination_check = self._validate_grounding_evidence(suggestion, context)
        if not hallucination_check.valid:
            return ValidationResult(valid=False, reason=f"Hallucination detected: {hallucination_check.reason}")
        
        # Layer 4: Execution readiness
        execution_check = self._validate_execution_readiness(suggestion)
        if not execution_check.valid:
            return ValidationResult(valid=False, reason=f"Not execution ready: {execution_check.reason}")
        
        # PREDICTION ACCURACY VALIDATION
        accuracy_issues = self._validate_prediction_accuracy(suggestion, context)
        if accuracy_issues:
            for issue in accuracy_issues:
                logger.warning(f"🔍 PREDICTION ACCURACY ISSUE: {issue}")
                logger.warning(f"   Suggestion: '{suggestion_text[:100]}...'")
                logger.warning(f"   Context: Task={context.get('screen_state', {}).get('current_task', 'unknown') if context.get('screen_state') else 'unknown'}")

        return ValidationResult(
            valid=True,
            specificity_score=specificity_score,
            grounding_score=hallucination_check.grounding_score,
            execution_readiness=execution_check.readiness_score
        )

    def _validate_application_context(self, suggestion_text: str, current_app: str, transcription: str) -> List[str]:
        """Validate that suggestion is appropriate for the current application context."""
        issues = []
        suggestion_lower = suggestion_text.lower()
        app_lower = current_app.lower()
        transcription_lower = transcription.lower()

        # Application-specific validations
        app_validations = {
            'email_apps': ['gmail', 'outlook', 'mail', 'thunderbird'],
            'coding_apps': ['vscode', 'pycharm', 'sublime', 'atom', 'intellij', 'xcode'],
            'writing_apps': ['word', 'docs', 'notion', 'obsidian', 'writer'],
            'presentation_apps': ['canva', 'powerpoint', 'keynote', 'slides', 'prezi'],
            'data_apps': ['excel', 'sheets', 'tableau', 'r_studio', 'jupyter'],
            'design_apps': ['figma', 'sketch', 'photoshop', 'illustrator', 'indesign']
        }

        # Check for inappropriate suggestions based on current app
        if any(email_app in app_lower for email_app in app_validations['email_apps']):
            # In email app, avoid non-email suggestions
            if 'code' in suggestion_lower or 'debug' in suggestion_lower:
                issues.append("Suggesting coding help while user is in email application")
        elif any(coding_app in app_lower for coding_app in app_validations['coding_apps']):
            # In coding app, avoid non-coding suggestions
            if 'email' in suggestion_lower and 'compose' not in transcription_lower:
                issues.append("Suggesting email composition while user is coding")

        return issues

    def _validate_prediction_accuracy(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Validate that predictions are actually likely to occur."""
        issues = []
        suggestion_text = f"{suggestion.get('title', '')} {suggestion.get('description', '')}"
        transcription = context.get('current_transcription', '')
        screen_state = context.get('screen_state')

        if not screen_state:
            return ["Cannot validate prediction accuracy without screen state"]

        current_task = getattr(screen_state, 'current_task', 'general_work')
        task_stage = getattr(screen_state, 'task_stage', 'in_progress')
        completion_percentage = getattr(screen_state, 'completion_percentage', 0.5)

        # ACCURACY CHECK 1: Task-stage appropriateness
        stage_inappropriate_predictions = {
            'starting': ['complete', 'finish', 'finalize', 'submit', 'deploy'],
            'stuck': ['continue', 'proceed', 'next', 'advance'],
            'completing': ['start', 'begin', 'setup', 'initialize']
        }

        if task_stage in stage_inappropriate_predictions:
            inappropriate_actions = stage_inappropriate_predictions[task_stage]
            if any(action in suggestion_text.lower() for action in inappropriate_actions):
                issues.append(f"Predicting '{inappropriate_actions[0]}' actions during {task_stage} stage")

        # ACCURACY CHECK 2: Completion percentage realism
        if completion_percentage < 0.2:  # Just started
            completion_indicators = ['complete', 'finish', 'finalize', 'submit']
            if any(indicator in suggestion_text.lower() for indicator in completion_indicators):
                issues.append("Predicting completion actions when task is just started")

        if completion_percentage > 0.8:  # Nearly done
            starting_indicators = ['start', 'begin', 'setup', 'initialize']
            if any(indicator in suggestion_text.lower() for indicator in starting_indicators):
                issues.append("Predicting starting actions when task is nearly complete")

        # ACCURACY CHECK 3: Task-specific prediction validation
        task_accuracy_rules = {
            'coding': {
                'required_context': ['function', 'class', 'variable', 'error', 'debug'],
                'inappropriate': ['email', 'presentation', 'design']
            },
            'email': {
                'required_context': ['compose', 'reply', 'subject', 'recipient'],
                'inappropriate': ['debug', 'compile', 'deploy']
            },
            'presentation': {
                'required_context': ['slide', 'chart', 'presentation', 'audience'],
                'inappropriate': ['debug', 'compile', 'database']
            },
            'writing': {
                'required_context': ['document', 'paragraph', 'word', 'text'],
                'inappropriate': ['compile', 'deploy', 'database']
            }
        }

        if current_task in task_accuracy_rules:
            rules = task_accuracy_rules[current_task]

            # Check for required context
            has_required_context = any(req in transcription.lower() for req in rules['required_context'])
            if not has_required_context:
                issues.append(f"Predicting {current_task} actions without {current_task} context")

            # Check for inappropriate predictions
            inappropriate_matches = [item for item in rules['inappropriate'] if item in suggestion_text.lower()]
            if inappropriate_matches:
                issues.append(f"Predicting {inappropriate_matches[0]} actions for {current_task} task")

        # ACCURACY CHECK 4: Time-based prediction validation
        prediction_timeframe = suggestion.get('prediction_timeframe', '')
        urgency_level = getattr(screen_state, 'urgency_level', 'later')

        if prediction_timeframe == '30_seconds' and urgency_level == 'later':
            issues.append("Predicting immediate action when urgency is low")

        if prediction_timeframe == '5_minutes' and urgency_level == 'immediate':
            issues.append("Predicting long-term action when urgency is immediate")

        return issues

    def _validate_content_sensitivity(self, suggestion_text: str, transcription: str, visible_content: str) -> List[str]:
        """Validate content sensitivity (personal vs professional)."""
        issues = []
        combined_content = f"{transcription} {visible_content}".lower()
        suggestion_lower = suggestion_text.lower()

        # Personal content indicators
        personal_indicators = [
            'mom', 'dad', 'family', 'birthday', 'love', 'personal', 'private',
            'friend', 'relative', 'vacation', 'holiday', 'party', 'dinner'
        ]

        # Professional content indicators
        professional_indicators = [
            'meeting', 'deadline', 'project', 'client', 'report', 'presentation',
            'business', 'corporate', 'team', 'manager', 'colleague', 'quarterly'
        ]

        is_personal_content = any(indicator in combined_content for indicator in personal_indicators)
        is_professional_content = any(indicator in combined_content for indicator in professional_indicators)

        # Check for inappropriate suggestions
        if is_personal_content and 'professional' in suggestion_lower:
            issues.append("Suggesting professional formatting for personal content")

        if is_professional_content and any(personal in suggestion_lower for personal in ['love', 'birthday', 'family']):
            issues.append("Suggesting personal content for professional context")

        return issues

    def _validate_user_intent(self, suggestion_text: str, transcription: str, context: Dict[str, Any]) -> List[str]:
        """Validate that suggestion aligns with user's current intent."""
        issues = []
        transcription_lower = transcription.lower()
        suggestion_lower = suggestion_text.lower()

        # Intent detection
        exploratory_intent = any(word in transcription_lower for word in [
            'looking', 'checking', 'browsing', 'curious', 'wondering', 'exploring',
            'scrolling', 'reading', 'viewing'
        ])

        focused_intent = any(word in transcription_lower for word in [
            'working on', 'creating', 'building', 'developing', 'implementing',
            'fixing', 'solving', 'completing', 'finishing'
        ])

        # Check for inappropriate suggestions based on intent
        if exploratory_intent:
            # For exploratory behavior, avoid complex suggestions
            complex_indicators = ['implement', 'create', 'build', 'develop', 'optimize']
            if any(indicator in suggestion_lower for indicator in complex_indicators):
                issues.append("Suggesting complex implementation during exploratory browsing")

        if focused_intent:
            # For focused work, avoid generic suggestions
            generic_indicators = ['best practices', 'tips', 'consider using', 'you might want']
            if any(indicator in suggestion_lower for indicator in generic_indicators):
                issues.append("Suggesting generic advice during focused work")

        return issues
    
    def _validate_structure(self, suggestion: Dict[str, Any]) -> bool:
        """Validate basic suggestion structure"""
        required_fields = ["title", "description", "category", "rationale", "has_completed_work", "completed_work"]
        return all(field in suggestion for field in required_fields)
    
    def _calculate_screen_specificity_score(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> int:
        """Calculate specificity score using screen-first standards"""

        score = 1  # Base score
        suggestion_text = f"{suggestion.get('title', '')} {suggestion.get('description', '')}"

        screen_state = context.get('screen_state')
        if not screen_state:
            return score

        # DIAGNOSTIC LOGGING: Track specificity gaming
        original_score = score
        
        # Screen-first Rule 1: Current app references (+2 points)
        current_app = context.get('current_app', '')
        if current_app and current_app.lower() in suggestion_text.lower():
            score += 2
        
        # Screen-first Rule 2: Specific visible content references (+2 points)
        visible_content = context.get('visible_content', '')
        if visible_content:
            content_words = visible_content.lower().split()
            specific_matches = sum(1 for word in content_words 
                                 if len(word) > 4 and word in suggestion_text.lower())
            if specific_matches >= 2:
                score += 2
        
        # Screen-first Rule 3: Next action predictions (+2 points)
        next_actions = screen_state.next_likely_actions
        action_references = sum(1 for action in next_actions 
                              if any(word in suggestion_text.lower() 
                                    for word in action.split('_')))
        if action_references > 0:
            score += 2
        
        # Screen-first Rule 4: Immediate timeframe (+1 point)
        prediction_timeframe = suggestion.get('prediction_timeframe', '')
        if prediction_timeframe in ['30_seconds', '2_minutes']:
            score += 1
        
        # Screen-first Rule 5: Task stage appropriateness (+1 point)
        task_stage = screen_state.task_stage
        stage_keywords = {
            'starting': ['setup', 'begin', 'start', 'initialize'],
            'in_progress': ['continue', 'next', 'proceed', 'advance'],
            'completing': ['finish', 'complete', 'finalize', 'wrap'],
            'stuck': ['fix', 'solve', 'resolve', 'debug']
        }
        
        if task_stage in stage_keywords:
            stage_matches = sum(1 for keyword in stage_keywords[task_stage]
                              if keyword in suggestion_text.lower())
            if stage_matches > 0:
                score += 1
        
        # Screen-first Rule 6: Obstacle addressing (+1 point)
        obstacles = screen_state.immediate_obstacles
        if obstacles:
            obstacle_matches = sum(1 for obstacle in obstacles
                                 if any(word in suggestion_text.lower() 
                                       for word in obstacle.split('_')))
            if obstacle_matches > 0:
                score += 1
        
        final_score = min(score, 10)  # Cap at 10

        # DIAGNOSTIC LOGGING: Track specificity gaming
        if final_score >= 7 and original_score < 3:
            logger.warning(f"🔍 SPECIFICITY SCORE INFLATION: Score jumped from {original_score} to {final_score}")
            logger.warning(f"   Suggestion: '{suggestion_text[:100]}...'")
            logger.warning(f"   Context: App={context.get('current_app', 'Unknown')}, Task={getattr(screen_state, 'current_task', 'unknown')}")
            logger.warning("   ⚠️  POTENTIAL GAMING: Score inflation may indicate keyword matching rather than semantic relevance")

        return final_score
    
    def _validate_grounding_evidence(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> GroundingResult:
        """Validate that suggestion is grounded in actual screen evidence"""
        
        suggestion_text = f"{suggestion.get('title', '')} {suggestion.get('description', '')}"
        grounding_score = 0.0
        evidence_found = []
        
        # Rule 1: Must reference current screen activity
        current_transcription = context.get('current_transcription', '').lower()
        if current_transcription:
            transcription_words = set(current_transcription.split())
            suggestion_words = set(suggestion_text.lower().split())
            overlap = len(transcription_words.intersection(suggestion_words))
            if overlap > 0 and len(transcription_words) > 0:
                overlap_ratio = overlap / len(transcription_words)
                grounding_score += overlap_ratio * 3.0
                evidence_found.append(f"References current screen activity ({overlap_ratio:.1%} overlap)")
        
        # Rule 2: Must reference specific visible content
        visible_content = context.get('visible_content', '').lower()
        if visible_content:
            content_overlap = self._calculate_content_overlap(suggestion_text.lower(), visible_content)
            if content_overlap > 0.1:  # 10% content overlap minimum
                grounding_score += 2.0
                evidence_found.append(f"References specific visible content ({content_overlap:.1%} overlap)")
        
        # Rule 3: Must connect to predicted next actions
        screen_state = context.get('screen_state')
        if screen_state and screen_state.next_likely_actions:
            action_connections = 0
            for action in screen_state.next_likely_actions:
                action_words = action.replace('_', ' ').split()
                if any(word in suggestion_text.lower() for word in action_words):
                    action_connections += 1
            
            if action_connections > 0:
                grounding_score += 2.0
                evidence_found.append(f"Connects to predicted next actions ({action_connections} matches)")
        
        # Rule 4: Must avoid generic language
        generic_phrases = [
            "best practices", "productivity tips", "helpful tools", 
            "research techniques", "optimization strategies", "consider using",
            "you might want to", "it would be good to"
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in suggestion_text.lower())
        if generic_count > 0:
            grounding_score -= generic_count * 1.0
            evidence_found.append(f"WARNING: Contains {generic_count} generic phrases")
        
        # Rule 5: Must reference current app/window
        current_app = context.get('current_app', '')
        active_window = context.get('active_window', '')
        
        if current_app and current_app.lower() in suggestion_text.lower():
            grounding_score += 1.0
            evidence_found.append(f"References current app: {current_app}")
        
        if active_window and active_window.lower() in suggestion_text.lower():
            grounding_score += 1.0
            evidence_found.append(f"References active window: {active_window}")
        
        # Minimum grounding threshold
        min_grounding_score = 4.0
        is_valid = grounding_score >= min_grounding_score and len(evidence_found) >= 2
        
        return GroundingResult(
            valid=is_valid,
            grounding_score=grounding_score,
            evidence_found=evidence_found,
            reason="Insufficient grounding evidence" if not is_valid else "Well grounded in screen activity"
        )
    
    def _validate_execution_readiness(self, suggestion: Dict[str, Any]) -> ExecutionResult:
        """Validate that suggestion has executable completed work"""
        
        if not suggestion.get('has_completed_work'):
            return ExecutionResult(valid=False, readiness_score=0.0, reason="No completed work provided")
        
        completed_work = suggestion.get('completed_work', {})
        
        # Check required fields
        required_fields = ['content', 'content_type', 'preview', 'action_label', 'metadata']
        missing_fields = [field for field in required_fields if not completed_work.get(field)]
        
        if missing_fields:
            return ExecutionResult(valid=False, readiness_score=0.0, reason=f"Missing fields: {missing_fields}")
        
        # Validate content quality
        content = completed_work.get('content', '')
        if len(content) < 50:
            return ExecutionResult(valid=False, readiness_score=0.0, reason="Content too short for meaningful work")
        
        # Validate metadata has evidence
        metadata = completed_work.get('metadata', {})
        evidence_fields = ['current_screen_elements', 'predicted_next_steps', 'screen_context_used']
        
        for field in evidence_fields:
            if not metadata.get(field) or len(metadata[field]) == 0:
                return ExecutionResult(valid=False, readiness_score=0.0, reason=f"Missing screen evidence in metadata: {field}")
        
        # Calculate readiness score
        readiness_score = 10.0
        if len(content) < 100:
            readiness_score -= 1.0
        if not metadata.get('screen_context_used'):
            readiness_score -= 2.0
        
        return ExecutionResult(
            valid=True,
            readiness_score=readiness_score,
            reason="Execution ready with screen-first completed work"
        )
    
    def _calculate_content_overlap(self, text1: str, text2: str) -> float:
        """Calculate semantic overlap between two text strings"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class ScreenStateChangeDetector:
    """Detects significant changes in screen state to trigger proactive assistance"""
    
    def __init__(self):
        self.previous_states = {}  # observation_id -> ScreenState
        self.change_thresholds = {
            'app_switch': 1.0,      # Always trigger on app switch
            'task_change': 0.8,     # High sensitivity to task changes
            'error_state': 1.0,     # Always trigger on errors
            'completion': 0.9,      # High sensitivity to task completion
            'stuck_state': 1.0      # Always trigger when user gets stuck
        }
    
    def detect_significant_changes(self, current_state: ScreenState, 
                                 previous_state: Optional[ScreenState]) -> List[str]:
        """Detect changes that warrant immediate proactive assistance"""
        
        if not previous_state:
            return ['initial_screen_analysis']
        
        significant_changes = []
        
        # App or task change
        if (current_state.current_task != previous_state.current_task or
            current_state.workflow_stage != previous_state.workflow_stage):
            significant_changes.append('task_transition')
        
        # Task stage progression
        if current_state.task_stage != previous_state.task_stage:
            if current_state.task_stage == 'stuck':
                significant_changes.append('user_stuck')
            elif current_state.task_stage == 'completing':
                significant_changes.append('task_nearing_completion')
            elif previous_state.task_stage == 'stuck' and current_state.task_stage != 'stuck':
                significant_changes.append('user_unstuck')
        
        # New obstacles detected
        new_obstacles = set(current_state.immediate_obstacles) - set(previous_state.immediate_obstacles)
        if new_obstacles:
            significant_changes.append('new_obstacles_detected')
        
        # Urgency level increase
        urgency_levels = {'later': 0, 'soon': 1, 'immediate': 2}
        if (urgency_levels.get(current_state.urgency_level, 0) > 
            urgency_levels.get(previous_state.urgency_level, 0)):
            significant_changes.append('urgency_increased')
        
        # Completion percentage jumps
        completion_diff = current_state.completion_percentage - previous_state.completion_percentage
        if completion_diff > 0.2:  # 20% jump in completion
            significant_changes.append('significant_progress')
        elif completion_diff < -0.1:  # Regression in progress
            significant_changes.append('progress_regression')
        
        # Context switch signals
        new_switch_signals = set(current_state.context_switch_signals) - set(previous_state.context_switch_signals)
        if new_switch_signals:
            significant_changes.append('context_switch_imminent')
        
        return significant_changes
    
    def should_trigger_proactive_assistance(self, changes: List[str]) -> bool:
        """Determine if changes warrant immediate proactive assistance"""
        
        high_priority_changes = [
            'user_stuck', 'new_obstacles_detected', 'urgency_increased',
            'task_nearing_completion', 'context_switch_imminent'
        ]
        
        return any(change in high_priority_changes for change in changes)


class ProactiveTimingOptimizer:
    """Optimizes when to deliver proactive suggestions for maximum effectiveness"""
    
    def __init__(self):
        self.timing_rules = {
            'immediate': 0,      # Deliver immediately
            'soon': 30,         # Wait 30 seconds
            'later': 300        # Wait 5 minutes
        }
        
        self.delivery_windows = {
            'task_transition': 10,    # 10 second window during transitions
            'error_state': 5,         # 5 second window for errors
            'completion': 15,         # 15 second window near completion
            'stuck_state': 0          # Immediate delivery when stuck
        }
    
    def calculate_optimal_delivery_time(self, screen_state: ScreenState, 
                                      changes: List[str]) -> float:
        """Calculate optimal time to deliver suggestion (seconds from now)"""
        
        # Immediate delivery conditions
        if (screen_state.urgency_level == 'immediate' or 
            'user_stuck' in changes or 
            'new_obstacles_detected' in changes):
            return 0.0
        
        # Task completion timing
        if 'task_nearing_completion' in changes:
            # Deliver just before they finish
            remaining_time = (1.0 - screen_state.completion_percentage) * 300  # Estimate 5 min max
            return max(remaining_time - 30, 0)  # 30 seconds before completion
        
        # Context switch timing
        if 'context_switch_imminent' in changes:
            return 10.0  # Give them 10 seconds to finish current action
        
        # Default timing based on urgency
        return self.timing_rules.get(screen_state.urgency_level, 60)
    
    def is_good_interruption_moment(self, screen_state: ScreenState) -> bool:
        """Determine if now is a good time to interrupt with suggestions"""
        
        # Good interruption moments
        good_moments = [
            screen_state.task_stage == 'stuck',
            screen_state.task_stage == 'completing',
            'preparing_to_switch_apps' in screen_state.context_switch_signals,
            screen_state.urgency_level == 'immediate'
        ]
        
        # Bad interruption moments
        bad_moments = [
            screen_state.task_stage == 'in_progress' and screen_state.urgency_level == 'later',
            len(screen_state.immediate_obstacles) == 0 and screen_state.completion_percentage < 0.8
        ]
        
        return any(good_moments) and not any(bad_moments)

    def _detect_user_intent(self, transcription: str, current_app: str, identified_task: str) -> str:
        """Detect user's current intent based on behavior patterns."""
        transcription_lower = transcription.lower()
        app_lower = current_app.lower()

        # INTENT CLASSIFICATION SCORES
        intent_scores = {
            'exploratory': 0,
            'focused': 0,
            'problem_solving': 0,
            'communication': 0,
            'learning': 0,
            'maintenance': 0
        }

        # EXPLORATORY INTENT indicators (browsing, casual interaction)
        exploratory_signals = [
            # Browsing behavior
            'looking', 'checking', 'browsing', 'scrolling', 'reading', 'viewing',
            'curious', 'wondering', 'exploring', 'surfing', 'navigating',

            # Casual interaction
            'just', 'quickly', 'briefly', 'casually', 'randomly', 'happened to',

            # Non-committal language
            'maybe', 'perhaps', 'might', 'could', 'possibly', 'thinking about',

            # Time indicators for casual activity
            'while', 'during', 'in between', 'waiting for', 'taking a break'
        ]

        for signal in exploratory_signals:
            if signal in transcription_lower:
                intent_scores['exploratory'] += 1

        # FOCUSED INTENT indicators (deliberate work)
        focused_signals = [
            # Work-oriented language
            'working on', 'creating', 'building', 'developing', 'implementing',
            'fixing', 'solving', 'completing', 'finishing', 'designing',

            # Task-specific language
            'need to', 'have to', 'must', 'should', 'will', 'going to',
            'planning to', 'about to', 'ready to', 'prepared to',

            # Time commitment indicators
            'deadline', 'due', 'schedule', 'timeline', 'priority', 'urgent',
            'important', 'critical', 'focus', 'concentrate'
        ]

        for signal in focused_signals:
            if signal in transcription_lower:
                intent_scores['focused'] += 1

        # PROBLEM SOLVING INTENT indicators
        problem_signals = [
            'fix', 'debug', 'solve', 'issue', 'problem', 'error', 'broken',
            'troubleshoot', 'repair', 'resolve', 'correct', 'address',
            'figure out', 'work out', 'sort out', 'deal with'
        ]

        for signal in problem_signals:
            if signal in transcription_lower:
                intent_scores['problem_solving'] += 2  # Higher weight for problem solving

        # COMMUNICATION INTENT indicators
        communication_signals = [
            'email', 'message', 'call', 'meeting', 'discuss', 'share',
            'collaborate', 'coordinate', 'contact', 'reach out', 'follow up',
            'respond', 'reply', 'send', 'communicate'
        ]

        for signal in communication_signals:
            if signal in transcription_lower:
                intent_scores['communication'] += 1

        # LEARNING INTENT indicators
        learning_signals = [
            'learn', 'study', 'understand', 'research', 'tutorial', 'guide',
            'documentation', 'help', 'how to', 'example', 'reference',
            'training', 'course', 'lesson', 'practice'
        ]

        for signal in learning_signals:
            if signal in transcription_lower:
                intent_scores['learning'] += 1

        # MAINTENANCE INTENT indicators (routine tasks)
        maintenance_signals = [
            'update', 'backup', 'clean', 'organize', 'sort', 'arrange',
            'review', 'check', 'verify', 'test', 'validate', 'maintain'
        ]

        for signal in maintenance_signals:
            if signal in transcription_lower:
                intent_scores['maintenance'] += 1

        # CONTEXT-BASED INTENT ADJUSTMENTS

        # App-based intent hints
        if app_lower in ['chrome', 'safari', 'firefox', 'edge']:
            # Web browsers often indicate exploratory behavior
            intent_scores['exploratory'] += 1
        elif app_lower in ['vscode', 'pycharm', 'intellij']:
            # Development tools indicate focused work
            intent_scores['focused'] += 2
        elif app_lower in ['gmail', 'outlook', 'slack', 'teams']:
            # Communication tools indicate communication intent
            intent_scores['communication'] += 2

        # Task-based intent hints
        if identified_task == 'general_work':
            # Unidentified tasks often indicate exploratory behavior
            intent_scores['exploratory'] += 1
        elif identified_task in ['coding', 'writing', 'presentation', 'data_analysis']:
            # Specific work tasks indicate focused intent
            intent_scores['focused'] += 1

        # LENGTH-BASED INTENT HINTS
        word_count = len(transcription.split())
        if word_count < 10:
            # Short transcriptions often indicate quick, exploratory actions
            intent_scores['exploratory'] += 1
        elif word_count > 30:
            # Long transcriptions often indicate detailed, focused work
            intent_scores['focused'] += 1

        # DETERMINE PRIMARY INTENT
        if intent_scores:
            primary_intent = max(intent_scores.items(), key=lambda x: x[1])

            # Only return intent if score is above threshold
            if primary_intent[1] >= 2:
                logger.info(f"🔍 USER INTENT DETECTED: {primary_intent[0]} (score: {primary_intent[1]})")
                logger.info(f"   Transcription: '{transcription[:100]}...'")
                logger.info(f"   Intent scores: {intent_scores}")
                return primary_intent[0]

        # DEFAULT: Return 'focused' for unidentified intents (safer assumption)
        logger.info("🔍 USER INTENT: Defaulting to 'focused' (unidentified intent)")
        return 'focused'