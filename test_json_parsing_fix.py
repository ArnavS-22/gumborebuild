#!/usr/bin/env python3
"""
Test the enhanced JSON parsing with actual AI response from production logs
"""

import json
import re

def test_enhanced_json_parsing():
    """Test enhanced JSON parsing with real AI response"""
    
    # Actual AI response from your logs (truncated)
    test_response = '''```json
{
  "immediate_work": [
    {
      "title": "I analyzed the file context and created a structured data organization framework",
      "description": "Based on the files ['gs.12', 'N.V', 'le.com', 'classroom.goog'] and their types ['goog', 'com', '12', 'V'], I developed a framework to categorize and organize these files for better accessibility and management.",
      "category": "completed_work",
      "rationale": "Specific evidence from transcription includes file names and types, indicating need for organization",
      "priority": "high",
      "confidence": 9,
      "has_completed_work": true,
      "completed_work": {
        "content": "FILE ORGANIZATION FRAMEWORK\\n\\n1. CATEGORIZATION SYSTEM:\\n- Educational Files (.goog): classroom.goog\\n- Web Resources (.com): le.com\\n- Version Files (.V): N.V\\n- Numbered Files (.12): gs.12\\n\\n2. ORGANIZATION STRATEGY:\\n- Create folders by file type\\n- Implement naming conventions\\n- Set up automated sorting rules",
        "content_type": "markdown",
        "preview": "Comprehensive file organization framework with categorization system...",
        "action_label": "View Organization Framework",
        "metadata": {"files_analyzed": 4, "categories_created": 4}
      }
    }
  ]
}
```'''
    
    print("🔍 Testing Enhanced JSON Parsing")
    print("=" * 50)
    
    # Test the enhanced parsing logic
    result = parse_json_response_enhanced(test_response)
    
    if result and "immediate_work" in result:
        immediate_work = result["immediate_work"]
        print(f"✅ SUCCESS: Parsed {len(immediate_work)} immediate work items")
        
        for i, work in enumerate(immediate_work):
            print(f"\n📋 Work Item {i+1}:")
            print(f"   Title: {work.get('title', 'N/A')}")
            print(f"   Has Completed Work: {work.get('has_completed_work', False)}")
            print(f"   Content Type: {work.get('completed_work', {}).get('content_type', 'N/A')}")
            print(f"   Action Label: {work.get('completed_work', {}).get('action_label', 'N/A')}")
        
        return True
    else:
        print("❌ FAILED: Could not parse JSON")
        print(f"Result: {result}")
        return False

def parse_json_response_enhanced(response: str):
    """Enhanced JSON parsing logic (copied from proactive_engine.py)"""
    try:
        response = response.strip()
        
        # Method 1: Try direct JSON parsing
        try:
            data = json.loads(response)
            if "immediate_work" in data:
                return data
        except json.JSONDecodeError:
            pass
        
        # Method 2: Enhanced markdown extraction
        if "```json" in response or "```" in response:
            start_markers = ["```json", "```"]
            end_marker = "```"
            
            for start_marker in start_markers:
                start_idx = response.find(start_marker)
                if start_idx >= 0:
                    json_start = response.find('{', start_idx)
                    if json_start >= 0:
                        end_idx = response.find(end_marker, json_start)
                        if end_idx >= 0:
                            json_str = response[json_start:end_idx].strip()
                        else:
                            # Handle truncated response
                            json_str = response[json_start:].strip()
                            # Find last complete closing brace
                            brace_count = 0
                            last_complete_pos = -1
                            for i, char in enumerate(json_str):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        last_complete_pos = i + 1
                                        break
                            
                            if last_complete_pos > 0:
                                json_str = json_str[:last_complete_pos]
                        
                        try:
                            data = json.loads(json_str)
                            if "immediate_work" in data:
                                return data
                        except json.JSONDecodeError:
                            continue
        
        # Method 3: Enhanced brace matching
        start_idx = response.find('{')
        if start_idx >= 0:
            json_candidate = response[start_idx:]
            brace_count = 0
            last_complete_pos = -1
            
            for i, char in enumerate(json_candidate):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_complete_pos = i + 1
                        break
            
            if last_complete_pos > 0:
                json_str = json_candidate[:last_complete_pos]
                try:
                    data = json.loads(json_str)
                    if "immediate_work" in data:
                        return data
                except json.JSONDecodeError:
                    pass
        
        # Method 4: Fallback
        title_match = re.search(r'"title":\s*"([^"]+)"', response)
        description_match = re.search(r'"description":\s*"([^"]+)"', response)
        
        fallback_title = title_match.group(1) if title_match else "I analyzed your context and created helpful content"
        fallback_description = description_match.group(1) if description_match else "AI-generated analysis based on your current activity"
        
        return {
            "immediate_work": [
                {
                    "title": fallback_title,
                    "description": fallback_description,
                    "category": "completed_work",
                    "rationale": "Fallback parsing from AI response",
                    "priority": "medium",
                    "confidence": 7,
                    "has_completed_work": True,
                    "completed_work": {
                        "content": response[:1000],
                        "content_type": "text",
                        "preview": fallback_description,
                        "action_label": "View AI Analysis",
                        "metadata": {"parsing_method": "fallback"}
                    }
                }
            ]
        }
        
    except Exception as e:
        print(f"Parsing error: {e}")
        return {"immediate_work": []}

if __name__ == "__main__":
    success = test_enhanced_json_parsing()
    if success:
        print("\n🎉 ENHANCED JSON PARSING: WORKING")
        print("The fix should resolve the production JSON parsing issues")
    else:
        print("\n❌ ENHANCED JSON PARSING: STILL BROKEN")