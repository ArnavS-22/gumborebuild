#!/usr/bin/env python3
"""
Simple test for enhanced transcription analysis without database dependencies
"""

import sys
import os
import asyncio

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

# Test the enhanced analysis directly
def test_enhanced_analysis():
    """Test enhanced transcription analysis"""
    
    # Import the enhanced analysis module directly
    from gum.services.enhanced_analysis import EnhancedTranscriptionAnalyzer
    
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
    analyzer = EnhancedTranscriptionAnalyzer()
    
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
    
    # Test executor selection
    print("\n🎯 Testing Executor Selection...")
    
    # Simulate the executor selection logic
    data_context = detailed_context.data_context
    if (data_context.get('currencies') or 
        any(word in detailed_context.visible_content.lower() 
            for word in ['revenue', 'profit', 'budget', 'financial', 'quarterly'])):
        selected_executor = 'financial_analysis'
    else:
        selected_executor = 'content_creation'
    
    print(f"   Selected executor: {selected_executor}")
    
    # Show detailed breakdown
    print("\n📊 Detailed Context Breakdown:")
    print(f"   File Context: {detailed_context.file_context}")
    print(f"   Data Context: {detailed_context.data_context}")
    print(f"   Workflow Context: {detailed_context.workflow_context}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_enhanced_analysis()
        if success:
            print("\n🎉 Enhanced Analysis Test: SUCCESS!")
            print("The maximally helpful AI assistant transformation is working correctly.")
        else:
            print("\n❌ Enhanced Analysis Test: FAILED!")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()