"""
Enhanced Transcription Analysis Engine
Extracts maximum actionable details from transcription data for hyper-specific suggestions
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DetailedContext:
    """Comprehensive context extracted from transcription"""
    # Basic context (existing)
    current_app: str
    active_window: str
    visible_content: str
    user_actions: str
    time_context: str
    
    # Enhanced context (new)
    file_context: Dict[str, Any]
    code_context: Dict[str, Any]
    ui_context: Dict[str, Any]
    communication_context: Dict[str, Any]
    workflow_context: Dict[str, Any]
    data_context: Dict[str, Any]
    content_patterns: List[str]
    actionable_items: List[Dict[str, Any]]
    intent_signals: List[str]

class EnhancedTranscriptionAnalyzer:
    """Advanced transcription analysis for maximum detail extraction"""
    
    def __init__(self):
        self.file_patterns = self._compile_file_patterns()
        self.code_patterns = self._compile_code_patterns()
        self.ui_patterns = self._compile_ui_patterns()
        self.communication_patterns = self._compile_communication_patterns()
        self.workflow_patterns = self._compile_workflow_patterns()
        self.data_patterns = self._compile_data_patterns()
    
    def analyze_transcription(self, transcription_content: str) -> DetailedContext:
        """Extract comprehensive context from transcription"""
        
        # Start with basic context (existing functionality)
        basic_context = self._extract_basic_context(transcription_content)
        
        # Extract detailed contexts
        file_context = self._extract_file_context(transcription_content)
        code_context = self._extract_code_context(transcription_content)
        ui_context = self._extract_ui_context(transcription_content)
        communication_context = self._extract_communication_context(transcription_content)
        workflow_context = self._extract_workflow_context(transcription_content)
        data_context = self._extract_data_context(transcription_content)
        
        # Identify patterns and actionable items
        content_patterns = self._identify_content_patterns(transcription_content)
        actionable_items = self._extract_actionable_items(transcription_content, {
            'file': file_context,
            'code': code_context,
            'ui': ui_context,
            'communication': communication_context,
            'workflow': workflow_context,
            'data': data_context
        })
        intent_signals = self._detect_intent_signals(transcription_content, actionable_items)
        
        return DetailedContext(
            # Basic context
            current_app=basic_context['current_app'],
            active_window=basic_context['active_window'],
            visible_content=basic_context['visible_content'],
            user_actions=basic_context['user_actions'],
            time_context=basic_context['time_context'],
            
            # Enhanced context
            file_context=file_context,
            code_context=code_context,
            ui_context=ui_context,
            communication_context=communication_context,
            workflow_context=workflow_context,
            data_context=data_context,
            content_patterns=content_patterns,
            actionable_items=actionable_items,
            intent_signals=intent_signals
        )
    
    def _extract_basic_context(self, content: str) -> Dict[str, str]:
        """Extract basic context (existing functionality)"""
        context = {
            "current_app": "Unknown",
            "active_window": "Unknown",
            "visible_content": "No specific content detected",
            "user_actions": "General activity",
            "time_context": datetime.now().strftime("%I:%M %p")
        }
        
        # Extract application name
        app_match = re.search(r'Application[:\s]+([^\n]+)', content, re.IGNORECASE)
        if app_match:
            context["current_app"] = app_match.group(1).strip()
        
        # Extract window title/document name
        window_patterns = [
            r'Window Title[:\s]+([^\n]+)',
            r'Title[:\s]+([^\n]+)',
            r'Document[:\s]+([^\n]+)'
        ]
        for pattern in window_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                context["active_window"] = match.group(1).strip()
                break
        
        # Extract visible text content
        content_patterns = [
            r'Visible Text Content[:\s]+([^]*?)(?=\n[A-Z]|$)',
            r'Text Content[:\s]+([^]*?)(?=\n[A-Z]|$)',
            r'Content[:\s]+([^]*?)(?=\n[A-Z]|$)'
        ]
        for pattern in content_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted_content = match.group(1).strip()
                context["visible_content"] = extracted_content[:500] + "..." if len(extracted_content) > 500 else extracted_content
                break
        
        return context
    
    def _extract_file_context(self, content: str) -> Dict[str, Any]:
        """Extract file-related context"""
        file_context = {
            'files_mentioned': [],
            'file_types': [],
            'directories': [],
            'file_operations': [],
            'project_structure': []
        }
        
        # Extract file names with extensions
        file_matches = re.findall(r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,4})', content)
        file_context['files_mentioned'] = list(set(file_matches))
        
        # Extract file types
        file_context['file_types'] = list(set([f.split('.')[-1] for f in file_matches if '.' in f]))
        
        # Extract directory paths
        dir_matches = re.findall(r'([a-zA-Z0-9_/-]+/[a-zA-Z0-9_/-]*)', content)
        file_context['directories'] = list(set(dir_matches))
        
        # Extract file operations
        operation_patterns = [
            r'(open|opening|edit|editing|save|saving|create|creating|delete|deleting)\s+([a-zA-Z0-9_.-]+)',
            r'(new|modified|updated)\s+file',
            r'file\s+(created|saved|opened|closed)'
        ]
        for pattern in operation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            file_context['file_operations'].extend(matches)
        
        return file_context
    
    def _extract_code_context(self, content: str) -> Dict[str, Any]:
        """Extract code-related context"""
        code_context = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
            'errors': [],
            'line_numbers': [],
            'programming_language': None
        }
        
        # Extract function names
        function_patterns = [
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Python
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # JavaScript
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # General function calls
        ]
        for pattern in function_patterns:
            matches = re.findall(pattern, content)
            code_context['functions'].extend(matches)
        
        # Extract class names
        class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
        code_context['classes'] = list(set(class_matches))
        
        # Extract import statements
        import_patterns = [
            r'import\s+([a-zA-Z0-9_.]+)',
            r'from\s+([a-zA-Z0-9_.]+)\s+import',
            r'#include\s*<([^>]+)>',
            r'require\([\'"]([^\'"]+)[\'"]\)'
        ]
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            code_context['imports'].extend(matches)
        
        # Extract error messages
        error_patterns = [
            r'Error[:\s]+([^\n]+)',
            r'Exception[:\s]+([^\n]+)',
            r'Traceback[:\s]+([^\n]+)',
            r'SyntaxError[:\s]+([^\n]+)'
        ]
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            code_context['errors'].extend(matches)
        
        # Extract line numbers
        line_matches = re.findall(r'line\s+(\d+)', content, re.IGNORECASE)
        code_context['line_numbers'] = [int(line) for line in line_matches]
        
        # Detect programming language
        language_indicators = {
            'python': ['def ', 'import ', 'from ', '__init__', '.py'],
            'javascript': ['function ', 'const ', 'let ', 'var ', '.js'],
            'java': ['public class', 'private ', 'public ', '.java'],
            'cpp': ['#include', 'std::', '.cpp', '.h'],
            'html': ['<html>', '<div>', '<script>', '.html'],
            'css': ['{', '}', '.css', 'color:', 'margin:']
        }
        
        for lang, indicators in language_indicators.items():
            if any(indicator in content.lower() for indicator in indicators):
                code_context['programming_language'] = lang
                break
        
        return code_context
    
    def _extract_ui_context(self, content: str) -> Dict[str, Any]:
        """Extract UI-related context"""
        ui_context = {
            'buttons': [],
            'menus': [],
            'forms': [],
            'dialogs': [],
            'tabs': [],
            'panels': [],
            'interactions': []
        }
        
        # Extract button text
        button_patterns = [
            r'button[:\s]+([^\n]+)',
            r'click[:\s]+([^\n]+)',
            r'press[:\s]+([^\n]+)'
        ]
        for pattern in button_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            ui_context['buttons'].extend(matches)
        
        # Extract menu items
        menu_patterns = [
            r'menu[:\s]+([^\n]+)',
            r'File\s*>\s*([^\n]+)',
            r'Edit\s*>\s*([^\n]+)',
            r'View\s*>\s*([^\n]+)'
        ]
        for pattern in menu_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            ui_context['menus'].extend(matches)
        
        # Extract tab names
        tab_matches = re.findall(r'tab[:\s]+([^\n]+)', content, re.IGNORECASE)
        ui_context['tabs'] = list(set(tab_matches))
        
        # Extract dialog information
        dialog_patterns = [
            r'dialog[:\s]+([^\n]+)',
            r'popup[:\s]+([^\n]+)',
            r'alert[:\s]+([^\n]+)'
        ]
        for pattern in dialog_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            ui_context['dialogs'].extend(matches)
        
        return ui_context
    
    def _extract_communication_context(self, content: str) -> Dict[str, Any]:
        """Extract communication-related context"""
        comm_context = {
            'emails': [],
            'messages': [],
            'contacts': [],
            'subjects': [],
            'timestamps': [],
            'communication_type': None
        }
        
        # Extract email addresses
        email_matches = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
        comm_context['emails'] = list(set(email_matches))
        
        # Extract subjects
        subject_patterns = [
            r'Subject[:\s]+([^\n]+)',
            r'Re[:\s]+([^\n]+)',
            r'Fwd[:\s]+([^\n]+)'
        ]
        for pattern in subject_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            comm_context['subjects'].extend(matches)
        
        # Extract names (potential contacts)
        name_patterns = [
            r'From[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'To[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'@([a-zA-Z0-9_]+)'  # Social media handles
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            comm_context['contacts'].extend(matches)
        
        # Detect communication type
        if any(word in content.lower() for word in ['email', 'gmail', 'outlook', 'inbox']):
            comm_context['communication_type'] = 'email'
        elif any(word in content.lower() for word in ['slack', 'teams', 'discord', 'chat']):
            comm_context['communication_type'] = 'chat'
        elif any(word in content.lower() for word in ['zoom', 'meet', 'call', 'meeting']):
            comm_context['communication_type'] = 'meeting'
        
        return comm_context
    
    def _extract_workflow_context(self, content: str) -> Dict[str, Any]:
        """Extract workflow-related context"""
        workflow_context = {
            'current_task': None,
            'task_stage': None,
            'tools_used': [],
            'time_indicators': [],
            'productivity_signals': [],
            'context_switches': []
        }
        
        # Detect current task based on content
        task_indicators = {
            'coding': ['function', 'class', 'import', 'def', 'var', 'const'],
            'writing': ['document', 'essay', 'article', 'draft', 'paragraph'],
            'analysis': ['data', 'chart', 'graph', 'analysis', 'report'],
            'research': ['search', 'google', 'wikipedia', 'article', 'study'],
            'communication': ['email', 'message', 'reply', 'send', 'meeting'],
            'design': ['photoshop', 'figma', 'design', 'color', 'layout']
        }
        
        for task, indicators in task_indicators.items():
            if any(indicator in content.lower() for indicator in indicators):
                workflow_context['current_task'] = task
                break
        
        # Extract tools being used
        tool_patterns = [
            r'(VS Code|Visual Studio|Sublime|Atom|Notepad)',
            r'(Chrome|Firefox|Safari|Edge)',
            r'(Photoshop|Illustrator|Figma|Sketch)',
            r'(Excel|Word|PowerPoint|Google Docs)',
            r'(Slack|Teams|Discord|Zoom)'
        ]
        for pattern in tool_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            workflow_context['tools_used'].extend(matches)
        
        # Extract time indicators
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)',
            r'(morning|afternoon|evening|night)',
            r'(today|yesterday|tomorrow)',
            r'(\d+\s*(?:minutes?|hours?|days?)\s*ago)'
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            workflow_context['time_indicators'].extend(matches)
        
        return workflow_context
    
    def _extract_data_context(self, content: str) -> Dict[str, Any]:
        """Extract data-related context"""
        data_context = {
            'numbers': [],
            'dates': [],
            'percentages': [],
            'currencies': [],
            'data_types': [],
            'metrics': []
        }
        
        # Extract numbers
        number_matches = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', content)
        data_context['numbers'] = [float(n.replace(',', '')) for n in number_matches if n]
        
        # Extract dates
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
            r'\b(\d{4}-\d{2}-\d{2})\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b'
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            data_context['dates'].extend(matches)
        
        # Extract percentages
        percentage_matches = re.findall(r'(\d+(?:\.\d+)?%)', content)
        data_context['percentages'] = percentage_matches
        
        # Extract currency amounts
        currency_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP))'
        ]
        for pattern in currency_patterns:
            matches = re.findall(pattern, content)
            data_context['currencies'].extend(matches)
        
        return data_context
    
    def _identify_content_patterns(self, content: str) -> List[str]:
        """Identify patterns in the content that suggest specific types of work"""
        patterns = []
        
        # Financial/business patterns
        if any(word in content.lower() for word in ['revenue', 'profit', 'budget', 'forecast', 'quarterly']):
            patterns.append('financial_analysis')
        
        # Academic/research patterns
        if any(word in content.lower() for word in ['research', 'study', 'analysis', 'hypothesis', 'conclusion']):
            patterns.append('academic_work')
        
        # Creative patterns
        if any(word in content.lower() for word in ['design', 'creative', 'brand', 'visual', 'aesthetic']):
            patterns.append('creative_work')
        
        # Technical patterns
        if any(word in content.lower() for word in ['code', 'function', 'algorithm', 'database', 'api']):
            patterns.append('technical_work')
        
        # Communication patterns
        if any(word in content.lower() for word in ['email', 'meeting', 'presentation', 'proposal', 'pitch']):
            patterns.append('communication_work')
        
        return patterns
    
    def _extract_actionable_items(self, content: str, contexts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract specific actionable items from the content"""
        actionable_items = []
        
        # File-based actions
        if contexts['file']['files_mentioned']:
            for file in contexts['file']['files_mentioned']:
                actionable_items.append({
                    'type': 'file_action',
                    'item': file,
                    'action': 'analyze_file',
                    'context': f"File {file} is being worked on"
                })
        
        # Code-based actions
        if contexts['code']['errors']:
            for error in contexts['code']['errors']:
                actionable_items.append({
                    'type': 'code_action',
                    'item': error,
                    'action': 'debug_error',
                    'context': f"Error detected: {error}"
                })
        
        # Communication-based actions
        if contexts['communication']['emails']:
            for email in contexts['communication']['emails']:
                actionable_items.append({
                    'type': 'communication_action',
                    'item': email,
                    'action': 'draft_response',
                    'context': f"Communication with {email}"
                })
        
        # Data-based actions
        if contexts['data']['numbers'] and len(contexts['data']['numbers']) > 3:
            actionable_items.append({
                'type': 'data_action',
                'item': contexts['data']['numbers'],
                'action': 'analyze_data',
                'context': f"Multiple data points detected: {len(contexts['data']['numbers'])} numbers"
            })
        
        return actionable_items
    
    def _detect_intent_signals(self, content: str, actionable_items: List[Dict[str, Any]]) -> List[str]:
        """Detect user intent signals from content and context"""
        intent_signals = []
        
        # Intent from action words
        action_words = {
            'create': 'creation_intent',
            'build': 'creation_intent',
            'make': 'creation_intent',
            'analyze': 'analysis_intent',
            'review': 'analysis_intent',
            'study': 'analysis_intent',
            'fix': 'problem_solving_intent',
            'debug': 'problem_solving_intent',
            'solve': 'problem_solving_intent',
            'optimize': 'improvement_intent',
            'improve': 'improvement_intent',
            'enhance': 'improvement_intent'
        }
        
        for word, intent in action_words.items():
            if word in content.lower():
                intent_signals.append(intent)
        
        # Intent from actionable items
        item_types = [item['type'] for item in actionable_items]
        if 'code_action' in item_types:
            intent_signals.append('development_intent')
        if 'communication_action' in item_types:
            intent_signals.append('communication_intent')
        if 'data_action' in item_types:
            intent_signals.append('analysis_intent')
        
        return list(set(intent_signals))
    
    def _compile_file_patterns(self):
        """Compile regex patterns for file detection"""
        return [
            re.compile(r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,4})'),
            re.compile(r'([a-zA-Z0-9_/-]+/[a-zA-Z0-9_/-]*)'),
        ]
    
    def _compile_code_patterns(self):
        """Compile regex patterns for code detection"""
        return [
            re.compile(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)'),
            re.compile(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)'),
            re.compile(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'),
        ]
    
    def _compile_ui_patterns(self):
        """Compile regex patterns for UI detection"""
        return [
            re.compile(r'button[:\s]+([^\n]+)', re.IGNORECASE),
            re.compile(r'menu[:\s]+([^\n]+)', re.IGNORECASE),
        ]
    
    def _compile_communication_patterns(self):
        """Compile regex patterns for communication detection"""
        return [
            re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'),
            re.compile(r'Subject[:\s]+([^\n]+)', re.IGNORECASE),
        ]
    
    def _compile_workflow_patterns(self):
        """Compile regex patterns for workflow detection"""
        return [
            re.compile(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)'),
            re.compile(r'(morning|afternoon|evening|night)', re.IGNORECASE),
        ]
    
    def _compile_data_patterns(self):
        """Compile regex patterns for data detection"""
        return [
            re.compile(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b'),
            re.compile(r'(\d+(?:\.\d+)?%)'),
        ]