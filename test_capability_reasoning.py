#!/usr/bin/env python3
"""
Test script for capability reasoning system
Tests the new prompt against various transcription scenarios to ensure
we preserve good suggestions while adding autonomous execution.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the unified AI client
from unified_ai_client import get_unified_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# New capability reasoning prompt
CAPABILITY_REASONING_PROMPT = """
You are an AI assistant that can perform some tasks autonomously and suggest others to the user.

YOUR CAPABILITIES:
- Text generation: drafts, summaries, outlines, rewrites, responses, emails
- Data synthesis: research compilation, comparisons, analysis, web search results
- Structured output: lists, tables, organized information, plans
- Content creation: documents, notes, agendas, recommendations

YOU CANNOT:
- Click, send, or confirm actions in external apps (games, email clients, browsers)
- Access or modify user's private environment (folders, files, configs, game interfaces)
- Make irreversible changes on behalf of the user
- Control user interfaces or navigate apps

REASONING FRAMEWORK:
For every opportunity you identify, ask yourself:
1. Can I fully complete this task end-to-end with my current abilities?
2. If YES → Execute it autonomously 
3. If NO → Suggest the best next step and state what the human must do

TRANSCRIPTION DATA: {transcription_content}

TASK CLASSIFICATION:
For each task, provide:
- Category: [Text/Research/Action] 
- Capability: [Can execute/Needs human]
- Plan: [What I'll do / What human must do]

OUTPUT FORMAT:
{{
  "tasks": [
    {{
      "description": "Clear description of the task or suggestion",
      "category": "Text|Research|Action",
      "capability": "Can execute|Needs human", 
      "plan": "Detailed explanation of execution or what human must do",
      "execute": true|false,
      "execution_type": "text_generation|research|data_synthesis",
      "rationale": "Why this can/cannot be executed autonomously"
    }}
  ]
}}

Always ask yourself: Can I fully complete this task end-to-end with my current abilities?
Never attempt actions outside your abilities.
Preserve the quality and specificity of suggestions - be detailed and actionable.
"""

# Test transcription scenarios
TEST_SCENARIOS = [
    {
        "name": "Clash Royale Gaming",
        "transcription": """
        User is playing Clash Royale mobile game. Screen shows current deck: Giant, Wizard, Arrows, Skeleton Army, Barbarians, Knight, Fireball, Zap. 
        User just lost to opponent using Balloon, Minion Horde, and Baby Dragon (heavy air troops). 
        User looking frustrated at defeat screen showing "DEFEAT". Battle log shows 3 recent losses to air-heavy decks.
        """,
        "expected": "Should suggest deck changes but NOT execute (can't access game interface)"
    },
    
    {
        "name": "Email Management", 
        "transcription": """
        User has Gmail inbox open with 5 unread emails. One email from Sarah Johnson with subject "Project Deadline - Need Update ASAP" 
        received 2 hours ago marked as high priority. Email content visible: "Hi, can you send me the current status of the 
        marketing campaign project? We need to present to stakeholders tomorrow. Thanks, Sarah"
        """,
        "expected": "Should execute email draft AND suggest sending it"
    },
    
    {
        "name": "Debugging Session",
        "transcription": """
        User debugging Python code in VS Code. Terminal shows JSON parsing error: "JSONDecodeError: Expecting ',' delimiter: line 47 column 12". 
        User has been staring at proactive_engine.py file for 45 minutes. Code shows _parse_json_response method with nested try-catch blocks.
        Environment variables file .env is visible in file explorer but not opened.
        """,
        "expected": "Should suggest checking code/files but NOT execute (can't access user's files)"
    },
    
    {
        "name": "House Hunting Research",
        "transcription": """
        User browsing Zillow website looking at Seattle houses. Search filters show: $600k-$800k, 2+ bedrooms, Ballard neighborhood.
        Currently viewing house listing at "1234 Market St, Seattle WA" - 3 bed, 2 bath, $750k, built 1985. 
        User has been scrolling through 15+ listings for past 30 minutes, bookmarked 3 houses.
        """,
        "expected": "Should execute research compilation AND suggest next steps like contacting agents"
    },
    
    {
        "name": "Document Editing",
        "transcription": """
        User editing Google Doc titled "Q4 Marketing Strategy". Document contains outline with sections: Budget Analysis, 
        Target Demographics, Campaign Ideas. User cursor is in "Campaign Ideas" section which only has bullet point "- Social Media Push". 
        User has been typing and deleting text for 10 minutes, seems stuck on content creation.
        """,
        "expected": "Should execute content generation for campaign ideas AND suggest review/editing"
    },
    
    {
        "name": "Calendar Scheduling",
        "transcription": """
        User has Google Calendar open showing next week. Trying to schedule team meeting with 4 people. 
        Email thread visible discussing meeting agenda: "Discuss Q4 goals, review budget, plan holiday campaign". 
        User checking availability across multiple calendars, looking frustrated at scheduling conflicts.
        """,
        "expected": "Should execute meeting agenda creation but NOT schedule meeting (can't access calendars)"
    }
]

class CapabilityReasoningTester:
    def __init__(self):
        self.ai_client = None
    
    async def start(self):
        """Initialize the AI client"""
        self.ai_client = await get_unified_client()
        logger.info("Capability reasoning tester initialized")
    
    async def test_scenario(self, scenario: Dict[str, str]) -> Dict[str, Any]:
        """Test a single transcription scenario"""
        logger.info(f"\n🧪 Testing: {scenario['name']}")
        logger.info(f"Expected: {scenario['expected']}")
        
        # Format the prompt with transcription
        prompt = CAPABILITY_REASONING_PROMPT.format(
            transcription_content=scenario['transcription']
        )
        
        try:
            # Get AI response
            response = await self.ai_client.text_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.1
            )
            
            # Parse JSON response
            result = self._parse_json_response(response)
            
            # Analyze results
            analysis = self._analyze_result(result, scenario)
            
            return {
                "scenario": scenario['name'],
                "raw_response": response,
                "parsed_result": result,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error testing scenario {scenario['name']}: {e}")
            return {
                "scenario": scenario['name'],
                "error": str(e),
                "analysis": {"status": "failed", "reason": str(e)}
            }
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with error handling"""
        try:
            # Clean up response
            response = response.strip()
            
            # Try direct JSON parsing
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Try extracting from markdown code blocks
            if "```json" in response or "```" in response:
                start_markers = ["```json", "```"]
                for start_marker in start_markers:
                    start_idx = response.find(start_marker)
                    if start_idx >= 0:
                        json_start = response.find('{', start_idx)
                        if json_start >= 0:
                            end_idx = response.find("```", json_start)
                            if end_idx >= 0:
                                json_str = response[json_start:end_idx].strip()
                                return json.loads(json_str)
            
            # Try finding JSON by braces
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                return json.loads(json_str)
            
            raise ValueError("No valid JSON found in response")
            
        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response: {response[:500]}...")
            return {"tasks": [], "parse_error": str(e)}
    
    def _analyze_result(self, result: Dict[str, Any], scenario: Dict[str, str]) -> Dict[str, Any]:
        """Analyze the AI's capability reasoning"""
        if "parse_error" in result:
            return {"status": "parse_failed", "reason": result["parse_error"]}
        
        tasks = result.get("tasks", [])
        if not tasks:
            return {"status": "no_tasks", "reason": "No tasks generated"}
        
        executable_tasks = [t for t in tasks if t.get("execute", False)]
        suggestion_tasks = [t for t in tasks if not t.get("execute", False)]
        
        analysis = {
            "status": "success",
            "total_tasks": len(tasks),
            "executable_count": len(executable_tasks),
            "suggestion_count": len(suggestion_tasks),
            "executable_tasks": [
                {
                    "description": t.get("description", ""),
                    "execution_type": t.get("execution_type", ""),
                    "rationale": t.get("rationale", "")
                } for t in executable_tasks
            ],
            "suggestion_tasks": [
                {
                    "description": t.get("description", ""),
                    "rationale": t.get("rationale", "")
                } for t in suggestion_tasks
            ]
        }
        
        # Validate reasoning quality
        reasoning_quality = self._validate_reasoning(tasks, scenario['name'])
        analysis["reasoning_quality"] = reasoning_quality
        
        return analysis
    
    def _validate_reasoning(self, tasks: List[Dict], scenario_name: str) -> Dict[str, Any]:
        """Validate the quality of AI's capability reasoning"""
        quality = {"score": 0, "issues": [], "strengths": []}
        
        for task in tasks:
            capability = task.get("capability", "")
            execute = task.get("execute", False)
            execution_type = task.get("execution_type", "")
            description = task.get("description", "").lower()
            
            # Check consistency between capability and execute flag
            if capability == "Can execute" and not execute:
                quality["issues"].append(f"Inconsistent: says 'Can execute' but execute=false")
            elif capability == "Needs human" and execute:
                quality["issues"].append(f"Inconsistent: says 'Needs human' but execute=true")
            
            # Check appropriate execution types
            if execute and execution_type in ["text_generation", "research", "data_synthesis"]:
                quality["strengths"].append(f"Correctly identified executable task: {execution_type}")
            
            # Check for inappropriate execution attempts
            if execute and any(word in description for word in ["click", "send", "navigate", "access", "open"]):
                quality["issues"].append(f"Inappropriately trying to execute UI action: {description[:50]}")
            
            # Check for good suggestions preserved
            if not execute and any(word in description for word in ["check", "rearrange", "consider", "try"]):
                quality["strengths"].append(f"Good suggestion preserved: {description[:50]}")
        
        # Calculate score
        total_points = len(quality["strengths"]) - len(quality["issues"])
        quality["score"] = max(0, min(10, total_points + 5))  # Scale to 0-10
        
        return quality
    
    async def run_all_tests(self):
        """Run all test scenarios and generate report"""
        logger.info("🚀 Starting capability reasoning tests...")
        
        results = []
        for scenario in TEST_SCENARIOS:
            result = await test_scenario(scenario)
            results.append(result)
            
            # Print immediate results
            if result.get("analysis", {}).get("status") == "success":
                analysis = result["analysis"]
                logger.info(f"✅ {scenario['name']}")
                logger.info(f"   Executable: {analysis['executable_count']}, Suggestions: {analysis['suggestion_count']}")
                logger.info(f"   Quality Score: {analysis['reasoning_quality']['score']}/10")
            else:
                logger.error(f"❌ {scenario['name']}: {result.get('analysis', {}).get('reason', 'Unknown error')}")
        
        # Generate summary report
        self._generate_report(results)
        return results
    
    def _generate_report(self, results: List[Dict[str, Any]]):
        """Generate a comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("CAPABILITY REASONING TEST REPORT")
        logger.info("="*60)
        
        successful_tests = [r for r in results if r.get("analysis", {}).get("status") == "success"]
        failed_tests = [r for r in results if r.get("analysis", {}).get("status") != "success"]
        
        logger.info(f"Total Tests: {len(results)}")
        logger.info(f"Successful: {len(successful_tests)}")
        logger.info(f"Failed: {len(failed_tests)}")
        
        if successful_tests:
            avg_quality = sum(r["analysis"]["reasoning_quality"]["score"] for r in successful_tests) / len(successful_tests)
            logger.info(f"Average Quality Score: {avg_quality:.1f}/10")
            
            total_executable = sum(r["analysis"]["executable_count"] for r in successful_tests)
            total_suggestions = sum(r["analysis"]["suggestion_count"] for r in successful_tests)
            logger.info(f"Total Executable Tasks: {total_executable}")
            logger.info(f"Total Suggestions: {total_suggestions}")
        
        # Detailed results
        logger.info("\nDETAILED RESULTS:")
        for result in results:
            scenario_name = result["scenario"]
            analysis = result.get("analysis", {})
            
            if analysis.get("status") == "success":
                logger.info(f"\n📋 {scenario_name}")
                logger.info(f"   Quality: {analysis['reasoning_quality']['score']}/10")
                
                if analysis["executable_tasks"]:
                    logger.info("   🤖 EXECUTABLE:")
                    for task in analysis["executable_tasks"]:
                        logger.info(f"      • {task['description'][:60]}...")
                
                if analysis["suggestion_tasks"]:
                    logger.info("   💡 SUGGESTIONS:")
                    for task in analysis["suggestion_tasks"]:
                        logger.info(f"      • {task['description'][:60]}...")
                
                if analysis["reasoning_quality"]["issues"]:
                    logger.info("   ⚠️  ISSUES:")
                    for issue in analysis["reasoning_quality"]["issues"]:
                        logger.info(f"      • {issue}")
            else:
                logger.error(f"\n❌ {scenario_name}: {analysis.get('reason', 'Unknown error')}")


async def test_scenario(scenario: Dict[str, str]) -> Dict[str, Any]:
    """Standalone function to test a single scenario"""
    tester = CapabilityReasoningTester()
    await tester.start()
    return await tester.test_scenario(scenario)


async def main():
    """Main test function"""
    tester = CapabilityReasoningTester()
    await tester.start()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
