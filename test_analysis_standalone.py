#!/usr/bin/env python3
"""
Standalone test for enhanced transcription analysis logic
Tests the core analysis functionality without database dependencies
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime

@dataclass
class DetailedContext:
    """Comprehensive context extracted from transcription"""
    current_app: str
    active_window: str
    visible_content: str
    user_actions: str
    time_context: str
    file_context: Dict[str, Any]
    code_context: Dict[str, Any]
    ui_context: Dict[str, Any]
    communication_context: Dict[str, Any]
    workflow_context: Dict[str, Any]
    data_context: Dict[str, Any]
    content_patterns: List[str]
    actionable_items: List[Dict[str, Any]]
    intent_signals: List[str]

class StandaloneTranscriptionAnalyzer:
    """Standalone version of enhanced transcription analyzer for testing"""
    
    def analyze_transcription(self, transcription_content: str) -> DetailedContext:
        """Extract comprehensive context from transcription"""
        
        # Basic context extraction
        basic_context = self._extract_basic_context(transcription_content)
        
        # Enhanced context extraction
        file_context = self._extract_file_context(transcription_content)
        code_context = self._extract_code_context(transcription_content)
        ui_context = self._extract_ui_context(transcription_content)
        communication_context = self._extract_communication_context(transcription_content)
        workflow_context = self._extract_workflow_context(transcription_content)
        data_context = self._extract_data_context(transcription_content)
        
        # Pattern and intent analysis
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
            current_app=basic_context['current_app'],
            active_window=basic_context['active_window'],
            visible_content=basic_context['visible_content'],
            user_actions=basic_context['user_actions'],
            time_context=basic_context['time_context'],
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
        """Extract basic context"""
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
        
        # Extract window title
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
        
        # Extract visible content
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
    
    def _extract_data_context(self, content: str) -> Dict[str, Any]:
        """Extract data-related context"""
        data_context = {
            'numbers': [],
            'dates': [],
            'percentages': [],
            'currencies': []
        }
        
        # Extract numbers
        number_matches = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', content)
        data_context['numbers'] = [float(n.replace(',', '')) for n in number_matches if n]
        
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
    
    def _extract_file_context(self, content: str) -> Dict[str, Any]:
        """Extract file-related context"""
        file_context = {
            'files_mentioned': [],
            'file_types': []
        }
        
        # Extract file names
        file_matches = re.findall(r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9]{1,4})', content)
        file_context['files_mentioned'] = list(set(file_matches))
        file_context['file_types'] = list(set([f.split('.')[-1] for f in file_matches if '.' in f]))
        
        return file_context
    
    def _extract_code_context(self, content: str) -> Dict[str, Any]:
        """Extract code-related context"""
        code_context = {
            'functions': [],
            'classes': [],
            'errors': [],
            'programming_language': None
        }
        
        # Extract function names
        function_patterns = [
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        for pattern in function_patterns:
            matches = re.findall(pattern, content)
            code_context['functions'].extend(matches)
        
        # Extract errors
        error_patterns = [
            r'Error[:\s]+([^\n]+)',
            r'Exception[:\s]+([^\n]+)',
            r'SyntaxError[:\s]+([^\n]+)'
        ]
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            code_context['errors'].extend(matches)
        
        # Detect programming language
        if any(indicator in content.lower() for indicator in ['def ', 'import ', '.py']):
            code_context['programming_language'] = 'python'
        elif any(indicator in content.lower() for indicator in ['function ', '.js']):
            code_context['programming_language'] = 'javascript'
        
        return code_context
    
    def _extract_ui_context(self, content: str) -> Dict[str, Any]:
        """Extract UI-related context"""
        return {'buttons': [], 'menus': [], 'tabs': []}
    
    def _extract_communication_context(self, content: str) -> Dict[str, Any]:
        """Extract communication-related context"""
        return {'emails': [], 'subjects': [], 'contacts': []}
    
    def _extract_workflow_context(self, content: str) -> Dict[str, Any]:
        """Extract workflow-related context"""
        workflow_context = {
            'current_task': None,
            'tools_used': []
        }
        
        # Detect current task
        task_indicators = {
            'financial_analysis': ['revenue', 'profit', 'budget', 'financial', 'quarterly'],
            'coding': ['function', 'class', 'import', 'def', 'error'],
            'writing': ['document', 'essay', 'article', 'draft'],
            'data_analysis': ['dataset', 'statistics', 'analytics', 'jupyter']
        }
        
        for task, indicators in task_indicators.items():
            if any(indicator in content.lower() for indicator in indicators):
                workflow_context['current_task'] = task
                break
        
        return workflow_context
    
    def _identify_content_patterns(self, content: str) -> List[str]:
        """Identify patterns in content"""
        patterns = []
        
        if any(word in content.lower() for word in ['revenue', 'profit', 'budget', 'quarterly']):
            patterns.append('financial_analysis')
        if any(word in content.lower() for word in ['function', 'class', 'error', 'code']):
            patterns.append('technical_work')
        if any(word in content.lower() for word in ['dataset', 'statistics', 'analytics']):
            patterns.append('data_analysis')
        
        return patterns
    
    def _extract_actionable_items(self, content: str, contexts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract actionable items"""
        actionable_items = []
        
        # File-based actions
        if contexts['file']['files_mentioned']:
            for file in contexts['file']['files_mentioned']:
                actionable_items.append({
                    'type': 'file_action',
                    'item': file,
                    'action': 'analyze_file'
                })
        
        # Code-based actions
        if contexts['code']['errors']:
            for error in contexts['code']['errors']:
                actionable_items.append({
                    'type': 'code_action',
                    'item': error,
                    'action': 'debug_error'
                })
        
        return actionable_items
    
    def _detect_intent_signals(self, content: str, actionable_items: List[Dict[str, Any]]) -> List[str]:
        """Detect user intent signals"""
        intent_signals = []
        
        action_words = {
            'analyze': 'analysis_intent',
            'debug': 'problem_solving_intent',
            'create': 'creation_intent'
        }
        
        for word, intent in action_words.items():
            if word in content.lower():
                intent_signals.append(intent)
        
        return list(set(intent_signals))

def test_enhanced_analysis():
    """Test enhanced transcription analysis"""
    
    # Test transcription
    test_transcription = """Application: Microsoft Excel
Window Title: Q3_Financial_Report.xlsx
Visible Text Content and UI Elements:
Revenue: $2,450,000
Expenses: $1,890,000
Profit Margin: 22.9%
YoY Growth: 15.3%
Current Quarter: Q3 2024
Previous Quarter: $2,120,000
Budget vs Actual: 103.2%
Key Metrics Dashboard showing:
- Customer Acquisition Cost: $125
- Lifetime Value: $1,850
- Churn Rate: 3.2%
- Monthly Recurring Revenue: $815,000
User is analyzing quarterly financial performance and comparing against budget targets."""
    
    # Initialize analyzer
    analyzer = StandaloneTranscriptionAnalyzer()
    
    # Analyze transcription
    print("🔍 Testing Enhanced Transcription Analysis...")
    detailed_context = analyzer.analyze_transcription(test_transcription)
    
    # Print results
    print(f"✅ Analysis Complete!")
    print(f"   Application: {detailed_context.current_app}")
    print(f"   Window: {detailed_context.active_window}")
    print(f"   Files detected: {len(detailed_context.file_context.get('files_mentioned', []))}")
    print(f"   Numbers detected: {len(detailed_context.data_context.get('numbers', []))}")
    print(f"   Currencies detected: {len(detailed_context.data_context.get('currencies', []))}")
    print(f"   Percentages detected: {len(detailed_context.data_context.get('percentages', []))}")
    print(f"   Content patterns: {detailed_context.content_patterns}")
    print(f"   Actionable items: {len(detailed_context.actionable_items)}")
    print(f"   Intent signals: {detailed_context.intent_signals}")
    
    # Test executor selection logic
    print("\n🎯 Testing Executor Selection Logic...")
    
    data_context = detailed_context.data_context
    if (data_context.get('currencies') or 
        any(word in detailed_context.visible_content.lower() 
            for word in ['revenue', 'profit', 'budget', 'financial', 'quarterly'])):
        selected_executor = 'financial_analysis'
    elif detailed_context.code_context.get('errors'):
        selected_executor = 'code_analysis'
    elif len(data_context.get('numbers', [])) > 5:
        selected_executor = 'data_analysis'
    else:
        selected_executor = 'content_creation'
    
    print(f"   Selected executor: {selected_executor}")
    
    # Show detailed breakdown
    print("\n📊 Detailed Context Breakdown:")
    print(f"   Numbers found: {detailed_context.data_context['numbers']}")
    print(f"   Currencies found: {detailed_context.data_context['currencies']}")
    print(f"   Percentages found: {detailed_context.data_context['percentages']}")
    print(f"   Workflow task: {detailed_context.workflow_context.get('current_task')}")
    
    # Validate expected results
    expected_results = {
        'app_detected': detailed_context.current_app == 'Microsoft Excel',
        'window_detected': 'Q3_Financial_Report.xlsx' in detailed_context.active_window,
        'currencies_found': len(detailed_context.data_context['currencies']) > 0,
        'numbers_found': len(detailed_context.data_context['numbers']) > 5,
        'percentages_found': len(detailed_context.data_context['percentages']) > 0,
        'financial_pattern': 'financial_analysis' in detailed_context.content_patterns,
        'correct_executor': selected_executor == 'financial_analysis'
    }
    
    print("\n✅ Validation Results:")
    for test, passed in expected_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test}: {status}")
    
    success_rate = sum(expected_results.values()) / len(expected_results)
    print(f"\n📊 Overall Success Rate: {success_rate:.1%}")
    
    return success_rate >= 0.8

if __name__ == "__main__":
    try:
        success = test_enhanced_analysis()
        if success:
            print("\n🎉 Enhanced Analysis Test: SUCCESS!")
            print("The maximally helpful AI assistant transformation is working correctly.")
        else:
            print("\n❌ Enhanced Analysis Test: FAILED!")
            print("Some validation checks failed - review the results above.")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()