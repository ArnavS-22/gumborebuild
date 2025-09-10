#!/usr/bin/env python3
"""
Test script for the Maximally Helpful AI Assistant transformation
Tests the enhanced transcription analysis, intelligent executors, and completed work generation
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import the enhanced components
from gum.services.enhanced_analysis import EnhancedTranscriptionAnalyzer, DetailedContext
from gum.services.intelligent_executors import (
    get_intelligent_executor, 
    determine_best_executor,
    FinancialAnalysisExecutor,
    CodeAnalysisExecutor,
    ContentCreatorExecutor,
    DataAnalysisExecutor
)
from gum.services.proactive_engine import ProactiveEngine
from gum.models import init_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test transcription samples
TEST_TRANSCRIPTIONS = {
    "financial_analysis": """Application: Microsoft Excel
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
User is analyzing quarterly financial performance and comparing against budget targets.""",
    
    "code_analysis": """Application: Visual Studio Code
Window Title: proactive_engine.py - zavionapp
Visible Text Content and UI Elements:
Line 456: async def _analyze_transcription(self, transcription_content: str) -> List[Dict[str, Any]]:
Line 457: Enhanced transcription analysis with maximum detail extraction.
Line 458: max_retries = self.config.max_retries if self.config.enable_retry_logic else 0
Error: SyntaxError: invalid syntax at line 462
Traceback (most recent call last):
  File proactive_engine.py, line 462, in _analyze_transcription
    detailed_context = self.enhanced_analyzer.analyze_transcription(transcription_content
SyntaxError: ( was never closed
Functions detected: _analyze_transcription, _create_context_summary, _save_suggestions_to_database
Classes detected: ProactiveEngine, EnhancedTranscriptionAnalyzer
User is debugging a Python syntax error in the proactive engine code.""",
    
    "content_creation": """Application: Google Docs
Window Title: Blog Post Draft - Marketing Strategy
Visible Text Content and UI Elements:
Title: 5 Ways to Improve Customer Engagement in 2024
Current content:
1. Personalization at Scale
   - Use AI-driven recommendations
   - Segment customers by behavior
2. Omnichannel Experience
   - Consistent messaging across platforms
   - Seamless handoffs between channels
3. [INCOMPLETE]
4. [INCOMPLETE]
5. [INCOMPLETE]

Word count: 127 words
Target: 1,500 words
Deadline: Tomorrow 9 AM
User is writing a marketing blog post and needs to complete the remaining sections.""",
    
    "data_analysis": """Application: Jupyter Notebook
Window Title: Customer_Analytics.ipynb
Visible Text Content and UI Elements:
Dataset loaded: customer_data.csv (15,847 rows, 23 columns)
Key statistics:
- Average order value: $89.34
- Customer lifetime value: $1,247.89
- Conversion rate: 3.7%
- Return customer rate: 68.2%
- Top product categories: Electronics (34%), Clothing (28%), Home (19%)
- Geographic distribution: US (45%), EU (32%), APAC (23%)
- Age demographics: 25-34 (31%), 35-44 (27%), 45-54 (22%)
- Seasonal trends: Q4 sales 40% higher than Q1
Current cell: df.groupby customer_segment agg revenue sum orders count
User is performing customer segmentation analysis to identify high-value customer groups."""
}

class MaximalHelpfulnessTest:
    """Test suite for the maximally helpful AI assistant"""
    
    def __init__(self):
        self.analyzer = EnhancedTranscriptionAnalyzer()
        self.test_results = {}
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        logger.info("🚀 Starting Maximally Helpful AI Assistant Test Suite")
        
        # Test 1: Enhanced Transcription Analysis
        await self.test_enhanced_analysis()
        
        # Test 2: Intelligent Executor Selection
        await self.test_executor_selection()
        
        # Test 3: Content Generation
        await self.test_content_generation()
        
        # Test 4: End-to-End Integration
        await self.test_end_to_end_integration()
        
        # Generate test report
        self.generate_test_report()
    
    async def test_enhanced_analysis(self):
        """Test the enhanced transcription analysis engine"""
        logger.info("📊 Testing Enhanced Transcription Analysis...")
        
        analysis_results = {}
        
        for test_name, transcription in TEST_TRANSCRIPTIONS.items():
            logger.info(f"  Analyzing {test_name} transcription...")
            
            try:
                detailed_context = self.analyzer.analyze_transcription(transcription)
                
                analysis_results[test_name] = {
                    "success": True,
                    "current_app": detailed_context.current_app,
                    "files_detected": len(detailed_context.file_context.get('files_mentioned', [])),
                    "code_elements": {
                        "functions": len(detailed_context.code_context.get('functions', [])),
                        "classes": len(detailed_context.code_context.get('classes', [])),
                        "errors": len(detailed_context.code_context.get('errors', [])),
                        "language": detailed_context.code_context.get('programming_language')
                    },
                    "data_elements": {
                        "numbers": len(detailed_context.data_context.get('numbers', [])),
                        "percentages": len(detailed_context.data_context.get('percentages', [])),
                        "currencies": len(detailed_context.data_context.get('currencies', []))
                    },
                    "patterns": detailed_context.content_patterns,
                    "actionable_items": len(detailed_context.actionable_items),
                    "intent_signals": detailed_context.intent_signals
                }
                
                logger.info(f"    ✅ {test_name}: {len(detailed_context.actionable_items)} actionable items, {len(detailed_context.intent_signals)} intent signals")
                
            except Exception as e:
                logger.error(f"    ❌ {test_name} failed: {e}")
                analysis_results[test_name] = {"success": False, "error": str(e)}
        
        self.test_results["enhanced_analysis"] = analysis_results
    
    async def test_executor_selection(self):
        """Test intelligent executor selection logic"""
        logger.info("🎯 Testing Intelligent Executor Selection...")
        
        selection_results = {}
        
        for test_name, transcription in TEST_TRANSCRIPTIONS.items():
            logger.info(f"  Testing executor selection for {test_name}...")
            
            try:
                # Analyze transcription
                detailed_context = self.analyzer.analyze_transcription(transcription)
                
                # Determine best executor
                executor_type = await determine_best_executor({
                    'visible_content': detailed_context.visible_content,
                    'file_context': detailed_context.file_context,
                    'code_context': detailed_context.code_context,
                    'ui_context': detailed_context.ui_context,
                    'communication_context': detailed_context.communication_context,
                    'workflow_context': detailed_context.workflow_context,
                    'data_context': detailed_context.data_context,
                    'content_patterns': detailed_context.content_patterns,
                    'actionable_items': detailed_context.actionable_items,
                    'intent_signals': detailed_context.intent_signals
                })
                
                selection_results[test_name] = {
                    "success": True,
                    "selected_executor": executor_type,
                    "context_factors": {
                        "patterns": detailed_context.content_patterns,
                        "data_points": len(detailed_context.data_context.get('numbers', [])),
                        "code_elements": bool(detailed_context.code_context.get('functions') or detailed_context.code_context.get('classes')),
                        "financial_indicators": bool(detailed_context.data_context.get('currencies'))
                    }
                }
                
                logger.info(f"    ✅ {test_name}: Selected {executor_type}")
                
            except Exception as e:
                logger.error(f"    ❌ {test_name} selection failed: {e}")
                selection_results[test_name] = {"success": False, "error": str(e)}
        
        self.test_results["executor_selection"] = selection_results
    
    async def test_content_generation(self):
        """Test content generation by intelligent executors"""
        logger.info("🎨 Testing Content Generation...")
        
        generation_results = {}
        
        # Test specific executors with appropriate contexts
        test_cases = [
            ("financial_analysis", FinancialAnalysisExecutor()),
            ("code_analysis", CodeAnalysisExecutor()),
            ("content_creation", ContentCreatorExecutor()),
            ("data_analysis", DataAnalysisExecutor())
        ]
        
        for test_name, executor in test_cases:
            if test_name not in TEST_TRANSCRIPTIONS:
                continue
                
            logger.info(f"  Testing {executor.__class__.__name__} with {test_name}...")
            
            try:
                # Analyze transcription
                transcription = TEST_TRANSCRIPTIONS[test_name]
                detailed_context = self.analyzer.analyze_transcription(transcription)
                
                # Generate content
                completed_work = await executor.execute({
                    'visible_content': detailed_context.visible_content,
                    'file_context': detailed_context.file_context,
                    'code_context': detailed_context.code_context,
                    'ui_context': detailed_context.ui_context,
                    'communication_context': detailed_context.communication_context,
                    'workflow_context': detailed_context.workflow_context,
                    'data_context': detailed_context.data_context,
                    'content_patterns': detailed_context.content_patterns,
                    'actionable_items': detailed_context.actionable_items,
                    'intent_signals': detailed_context.intent_signals
                })
                
                if completed_work:
                    generation_results[test_name] = {
                        "success": True,
                        "executor": executor.__class__.__name__,
                        "title": completed_work.title,
                        "content_type": completed_work.content_type,
                        "content_length": len(completed_work.content),
                        "preview": completed_work.preview[:100] + "..." if len(completed_work.preview) > 100 else completed_work.preview,
                        "action_label": completed_work.action_label,
                        "metadata": completed_work.metadata
                    }
                    
                    logger.info(f"    ✅ {test_name}: Generated '{completed_work.title}' ({completed_work.content_type}, {len(completed_work.content)} chars)")
                else:
                    generation_results[test_name] = {"success": False, "error": "No content generated"}
                    logger.warning(f"    ⚠️ {test_name}: No content generated")
                
            except Exception as e:
                logger.error(f"    ❌ {test_name} generation failed: {e}")
                generation_results[test_name] = {"success": False, "error": str(e)}
        
        self.test_results["content_generation"] = generation_results
    
    async def test_end_to_end_integration(self):
        """Test end-to-end integration with the proactive engine"""
        logger.info("🔄 Testing End-to-End Integration...")
        
        integration_results = {}
        
        try:
            # Initialize database (in-memory for testing)
            engine, Session = await init_db(":memory:")
            
            # Initialize proactive engine
            proactive_engine = ProactiveEngine()
            await proactive_engine.start()
            
            # Test with one sample transcription
            test_transcription = TEST_TRANSCRIPTIONS["financial_analysis"]
            
            logger.info("  Running end-to-end analysis...")
            
            # This would normally be called by the main system
            suggestions = await proactive_engine._analyze_transcription(test_transcription)
            
            integration_results = {
                "success": True,
                "suggestions_generated": len(suggestions),
                "completed_work_count": sum(1 for s in suggestions if s.get("has_completed_work")),
                "suggestion_types": [s.get("category", "unknown") for s in suggestions],
                "executor_types": [s.get("executor_type", "unknown") for s in suggestions if s.get("executor_type")]
            }
            
            logger.info(f"    ✅ Generated {len(suggestions)} suggestions ({integration_results['completed_work_count']} with completed work)")
            
            # Clean up
            await proactive_engine.stop()
            
        except Exception as e:
            logger.error(f"    ❌ End-to-end integration failed: {e}")
            integration_results = {"success": False, "error": str(e)}
        
        self.test_results["end_to_end_integration"] = integration_results
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📋 Generating Test Report...")
        
        report = {
            "test_suite": "Maximally Helpful AI Assistant",
            "timestamp": datetime.now().isoformat(),
            "results": self.test_results,
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0
            }
        }
        
        # Calculate summary statistics
        for test_category, results in self.test_results.items():
            if isinstance(results, dict):
                if "success" in results:
                    # Single test result
                    report["summary"]["total_tests"] += 1
                    if results["success"]:
                        report["summary"]["passed_tests"] += 1
                    else:
                        report["summary"]["failed_tests"] += 1
                else:
                    # Multiple test results
                    for test_name, result in results.items():
                        if isinstance(result, dict) and "success" in result:
                            report["summary"]["total_tests"] += 1
                            if result["success"]:
                                report["summary"]["passed_tests"] += 1
                            else:
                                report["summary"]["failed_tests"] += 1
        
        if report["summary"]["total_tests"] > 0:
            report["summary"]["success_rate"] = report["summary"]["passed_tests"] / report["summary"]["total_tests"]
        
        # Save report
        with open("test_maximal_helpfulness_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed_tests']}")
        logger.info(f"Failed: {report['summary']['failed_tests']}")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1%}")
        logger.info("=" * 60)
        
        if report["summary"]["success_rate"] >= 0.8:
            logger.info("🎉 MAXIMALLY HELPFUL AI ASSISTANT TRANSFORMATION: SUCCESS!")
        else:
            logger.warning("⚠️ Some tests failed - review the detailed report")
        
        logger.info(f"📄 Detailed report saved to: test_maximal_helpfulness_report.json")

async def main():
    """Run the test suite"""
    test_suite = MaximalHelpfulnessTest()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())