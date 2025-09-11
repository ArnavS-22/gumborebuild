"""
Suggestion Quality Issues Test - Find what causes bad, useless, or irrelevant suggestions
This test identifies specific failure modes in suggestion generation and validation
"""

import re
from datetime import datetime

def analyze_prompt_quality_issues():
    """Analyze the SCREEN_FIRST_PROACTIVE_PROMPT for suggestion quality problems"""
    print("🔍 Analyzing Prompt Logic for Suggestion Quality Issues...")
    
    from gum.services.proactive_engine import SCREEN_FIRST_PROACTIVE_PROMPT
    
    # Issue 1: Prompt is too long and complex
    prompt_length = len(SCREEN_FIRST_PROACTIVE_PROMPT)
    print(f"   📏 Prompt length: {prompt_length:,} characters")
    if prompt_length > 4000:
        print("   🚨 ISSUE: Prompt too long - AI may lose focus or hit token limits")
    
    # Issue 2: Critical rules come early but enforcement comes late
    rules_position = SCREEN_FIRST_PROACTIVE_PROMPT.find("CRITICAL SCREEN-FIRST RULES")
    grounding_position = SCREEN_FIRST_PROACTIVE_PROMPT.find("MANDATORY SCREEN-FIRST GROUNDING")
    
    print(f"   📍 Rules position: {rules_position}, Grounding position: {grounding_position}")
    if grounding_position - rules_position > 2000:
        print("   🚨 ISSUE: Key enforcement rules separated by too much text - AI may ignore")
    
    # Issue 3: Examples are too perfect
    examples_section = SCREEN_FIRST_PROACTIVE_PROMPT[SCREEN_FIRST_PROACTIVE_PROMPT.find("SCREEN-FIRST EXAMPLES"):SCREEN_FIRST_PROACTIVE_PROMPT.find("IMMEDIATE PREDICTION CATEGORIES")]
    
    if "ambiguous" not in examples_section.lower() and "unclear" not in examples_section.lower():
        print("   🚨 ISSUE: No examples of ambiguous cases - AI won't know when NOT to suggest")
    
    # Issue 4: Confidence hardcoded to high values
    if '"confidence": 9' in SCREEN_FIRST_PROACTIVE_PROMPT:
        print("   🚨 ISSUE: Confidence hardcoded to 9 - unrealistic, should vary based on certainty")
    
    return True

def analyze_validation_false_positives():
    """Find validation issues that allow bad suggestions through"""
    print("\n🔍 Analyzing Validation for False Positives...")
    
    # Test cases that should FAIL but might pass validation
    bad_suggestions = [
        {
            "name": "Word Overlap Gaming",
            "suggestion": {
                "title": "VS Code debugging error line main.py",  # Just keywords
                "description": "Based on VS Code main.py error line debugging, here's generic help.",
                "category": "screen_first_proactive",
                "rationale": "VS Code error debugging",
                "has_completed_work": True,
                "completed_work": {
                    "content": "Here are debugging tips...",  # Generic content
                    "content_type": "text",
                    "preview": "Generic debugging advice",
                    "action_label": "View",
                    "metadata": {
                        "current_screen_elements": ["VS Code", "error", "main.py"],
                        "predicted_next_steps": ["debug"],
                        "screen_context_used": "VS Code error context"
                    }
                }
            },
            "context": {
                "current_transcription": "Application: VS Code Window: main.py Error: TypeError line 45 debugging",
                "current_app": "VS Code",
                "visible_content": "def calculate_total error TypeError main.py line debugging"
            }
        },
        {
            "name": "Irrelevant Completed Work",
            "suggestion": {
                "title": "I created email templates for your Gmail",  # Wrong prediction
                "description": "Based on Gmail activity, I created email templates.",
                "category": "screen_first_proactive", 
                "rationale": "Gmail email templates",
                "has_completed_work": True,
                "completed_work": {
                    "content": "Template 1: Hello...\nTemplate 2: Thanks...",
                    "content_type": "text",
                    "preview": "Email templates",
                    "action_label": "Use Templates",
                    "metadata": {
                        "current_screen_elements": ["Gmail"],
                        "predicted_next_steps": ["use_templates"],
                        "screen_context_used": "Gmail context"
                    }
                }
            },
            "context": {
                "current_transcription": "Application: Gmail Window: Inbox User reading important email from boss",
                "current_app": "Gmail", 
                "visible_content": "Important: Please review quarterly budget by end of day"
            }
        }
    ]
    
    issues_found = []
    
    for test_case in bad_suggestions:
        print(f"\n   Testing: {test_case['name']}")
        
        # Simulate validation logic
        suggestion = test_case['suggestion']
        context = test_case['context']
        
        # Use new semantic validation instead of simple word overlap
        try:
            from gum.services.proactive_engine import ProactiveEngine
            engine = ProactiveEngine()

            # Create work item for semantic validation
            work_item = {
                'title': suggestion['title'],
                'description': suggestion['description']
            }

            # Calculate semantic grounding score
            semantic_score = engine._calculate_semantic_grounding_score(work_item, context)

            print(f"   📊 Semantic grounding score: {semantic_score:.2f}")

            if semantic_score < 0.3:  # Low semantic relevance
                print(f"   ❌ SEMANTIC ISSUE: Low semantic relevance ({semantic_score:.2f}) for {test_case['name']}")
                issues_found.append(test_case['name'])
            else:
                print(f"   ✅ SEMANTIC VALIDATION: Good semantic relevance ({semantic_score:.2f})")

        except Exception as e:
            print(f"   ⚠️  SEMANTIC VALIDATION FAILED: {e}")
            # Fall back to basic word overlap check
            suggestion_text = f"{suggestion['title']} {suggestion['description']}"
            transcription = context['current_transcription']

            suggestion_words = set(suggestion_text.lower().split())
            transcription_words = set(transcription.lower().split())
            overlap = len(suggestion_words.intersection(transcription_words))
            overlap_ratio = overlap / len(transcription_words) if transcription_words else 0

            print(f"   📊 Word overlap (fallback): {overlap}/{len(transcription_words)} = {overlap_ratio:.2%}")

            if overlap_ratio > 0.3:  # High overlap
                print(f"   ❌ FALSE POSITIVE: High word overlap but suggestion is {test_case['name']}")
                issues_found.append(test_case['name'])
    
    if issues_found:
        print(f"\n   🚨 VALIDATION ISSUES: {len(issues_found)} false positives found")
        for issue in issues_found:
            print(f"   - {issue}")
    
    return len(issues_found) == 0

def analyze_prediction_algorithm_flaws():
    """Find flaws in the prediction algorithms that lead to bad suggestions"""
    print("\n🔍 Analyzing Prediction Algorithm Flaws...")
    
    # Test the actual prediction logic
    try:
        from gum.services.screen_first_analyzer import ScreenFirstAnalyzer
        analyzer = ScreenFirstAnalyzer()
        
        # Test case 1: Misclassified task
        print("   Test 1: Task Misclassification")
        transcription = "Application: Visual Studio Code 2024 Enterprise Edition"
        context = {"current_app": "Visual Studio Code 2024 Enterprise Edition"}
        
        task = analyzer._identify_current_task(transcription, context['current_app'])
        print(f"   Task identified: {task}")
        
        if task != 'coding':
            print("   🚨 PREDICTION ISSUE: Doesn't recognize 'Visual Studio Code 2024 Enterprise Edition' as coding")
        
        # Test case 2: Inappropriate next actions
        print("\n   Test 2: Inappropriate Next Action Predictions")
        transcription = "Application: Gmail User reading email from grandmother about family reunion"
        
        screen_state = analyzer.analyze_screen_state(transcription, {"current_app": "Gmail"})
        print(f"   Next actions predicted: {screen_state.next_likely_actions}")
        
        if 'send_email' in screen_state.next_likely_actions:
            print("   🚨 PREDICTION ISSUE: Predicts 'send_email' when user is just reading email")
        
        # Test case 3: Wrong completion estimation
        print("\n   Test 3: Wrong Completion Estimation")
        transcription = "Application: Canva User just opened new presentation template"
        
        screen_state = analyzer.analyze_screen_state(transcription, {"current_app": "Canva"})
        print(f"   Completion estimated: {screen_state.completion_percentage:.1%}")
        
        if screen_state.completion_percentage > 0.2:
            print("   🚨 PREDICTION ISSUE: High completion % for newly opened template")
        
        # Test case 4: Wrong urgency calculation
        print("\n   Test 4: Wrong Urgency Calculation")
        transcription = "Application: Word User leisurely writing journal entry"
        
        screen_state = analyzer.analyze_screen_state(transcription, {"current_app": "Word"})
        print(f"   Urgency level: {screen_state.urgency_level}")
        
        if screen_state.urgency_level == 'immediate':
            print("   🚨 PREDICTION ISSUE: High urgency for leisurely journal writing")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Can't test prediction algorithms: {e}")
        return False

def analyze_prompt_bias_issues():
    """Find biases in the prompt that lead to poor suggestions"""
    print("\n🔍 Analyzing Prompt Bias Issues...")
    
    from gum.services.proactive_engine import SCREEN_FIRST_PROACTIVE_PROMPT
    
    bias_issues = []
    
    # Issue 1: Over-confidence bias
    if '"confidence": 9' in SCREEN_FIRST_PROACTIVE_PROMPT:
        bias_issues.append("Over-confidence: Hardcoded high confidence values")
    
    # Issue 2: Completion bias
    completion_count = SCREEN_FIRST_PROACTIVE_PROMPT.lower().count("completed")
    if completion_count > 10:
        bias_issues.append(f"Completion bias: 'Completed' mentioned {completion_count} times - may always claim to complete work")
    
    # Issue 3: Specificity bias
    specific_count = SCREEN_FIRST_PROACTIVE_PROMPT.lower().count("specific")
    if specific_count > 15:
        bias_issues.append(f"Specificity bias: 'Specific' mentioned {specific_count} times - may force specificity where none exists")
    
    # Issue 4: Time pressure bias
    immediate_count = SCREEN_FIRST_PROACTIVE_PROMPT.lower().count("immediate")
    if immediate_count > 5:
        bias_issues.append(f"Time pressure bias: 'Immediate' mentioned {immediate_count} times - may create false urgency")
    
    # Issue 5: Perfect scenario bias
    if "unclear" not in SCREEN_FIRST_PROACTIVE_PROMPT.lower():
        bias_issues.append("Perfect scenario bias: No examples of unclear or ambiguous situations")
    
    if bias_issues:
        print(f"   🚨 PROMPT BIAS ISSUES: {len(bias_issues)} found")
        for issue in bias_issues:
            print(f"   - {issue}")
    else:
        print("   ✅ No significant prompt bias issues found")
    
    return len(bias_issues) == 0

def test_realistic_bad_suggestions():
    """Test with realistic scenarios that would generate bad suggestions"""
    print("\n🔍 Testing Realistic Bad Suggestion Scenarios...")
    
    # Scenario 1: Ambiguous screen state
    print("   Scenario 1: Ambiguous Screen Activity")
    ambiguous_transcription = """
    Application: Chrome
    Window: New Tab
    Visible Text Content: Google
    User opened browser
    """
    
    print("   Input: User just opened Chrome to Google homepage")
    print("   🚨 LIKELY BAD SUGGESTION: 'I researched your topic and created a summary'")
    print("   💡 BETTER: Wait for more specific activity before suggesting")
    
    # Scenario 2: Personal/private content
    print("\n   Scenario 2: Personal Content")
    personal_transcription = """
    Application: Messages
    Window: Chat with Mom
    Visible Text Content: Happy birthday! Love you
    User typing response
    """
    
    print("   Input: User typing personal message to Mom")
    print("   🚨 LIKELY BAD SUGGESTION: 'I drafted your professional message'")
    print("   💡 BETTER: Don't suggest for personal communications")
    
    # Scenario 3: User just browsing/exploring
    print("\n   Scenario 3: Exploratory Browsing")
    browsing_transcription = """
    Application: Safari
    Window: Reddit - r/programming
    Visible Text Content: Various programming posts
    User scrolling through posts
    """
    
    print("   Input: User casually browsing programming subreddit")
    print("   🚨 LIKELY BAD SUGGESTION: 'I created a programming study plan based on these posts'")
    print("   💡 BETTER: Wait for focused engagement before suggesting")
    
    # Scenario 4: Context switching rapidly
    print("\n   Scenario 4: Rapid Context Switching")
    switching_transcription = """
    Application: Slack
    Window: #general channel
    Visible Text Content: Quick team standup message
    User switching between multiple apps rapidly
    """
    
    print("   Input: User rapidly switching between apps")
    print("   🚨 LIKELY BAD SUGGESTION: 'I drafted your detailed project update'")
    print("   💡 BETTER: Don't suggest during rapid task switching")
    
    print("\n   🎯 ROOT CAUSE: System lacks context awareness for:")
    print("   - User intent (browsing vs working)")
    print("   - Content sensitivity (personal vs professional)")  
    print("   - Task certainty (clear vs ambiguous)")
    print("   - Timing appropriateness (focused vs transitioning)")
    
    return True

def analyze_grounding_evidence_quality():
    """Analyze the quality of grounding evidence extraction"""
    print("\n🔍 Analyzing Grounding Evidence Quality...")
    
    # Test the actual evidence extraction
    from gum.services.proactive_engine import ProactiveEngine
    engine = ProactiveEngine()
    
    # Test case 1: Poor evidence extraction
    test_transcription = """
    Application: Canva Pro Desktop Client
    Window: Untitled Design #47
    Visible Text Content: [Image placeholder] [Text box] [Color palette]
    User clicked on text tool
    """
    
    evidence = engine._extract_grounding_evidence(test_transcription, [], [])
    
    print(f"   📊 Evidence extracted:")
    for category, items in evidence.items():
        print(f"   - {category}: {items}")
    
    # Check for issues
    issues = []
    
    # Issue 1: Doesn't recognize "Canva Pro Desktop Client" as "Canva"
    if 'Canva' not in evidence.get('specific_apps', []):
        issues.append("Doesn't recognize app name variations (Canva Pro Desktop Client)")
    
    # Issue 2: Extracts useless generic content
    specific_content = evidence.get('specific_content', [])
    generic_content = ['Image placeholder', 'Text box', 'Color palette']
    if any(generic in str(specific_content) for generic in generic_content):
        issues.append("Extracts generic UI elements as 'specific content'")
    
    # Issue 3: No semantic understanding
    if evidence.get('specific_actions', []) == ['clicked']:
        issues.append("Only captures literal actions, not semantic meaning (design intent)")
    
    if issues:
        print(f"   🚨 EVIDENCE ISSUES: {len(issues)} problems found")
        for issue in issues:
            print(f"   - {issue}")
    
    return len(issues) == 0

def test_specificity_requirement_gaming():
    """Test how the specificity requirements can be gamed"""
    print("\n🔍 Testing Specificity Requirement Gaming...")
    
    # Create a suggestion that games the specificity scoring
    gamed_suggestion = {
        "title": "VS Code main.py line 45 calculate_total TypeError debug",  # Keyword stuffing
        "description": "Based on VS Code main.py line 45 calculate_total TypeError, I'll debug the VS Code main.py line 45 error.",
        "category": "screen_first_proactive",
        "rationale": "VS Code main.py line 45",
        "priority": "high",
        "confidence": 9,
        "has_completed_work": True,
        "prediction_timeframe": "30_seconds",  # Gaming timeframe scoring
        "completed_work": {
            "content": "Generic debugging advice that doesn't actually fix anything specific",
            "content_type": "text",
            "preview": "Debug tips",
            "action_label": "View Tips",
            "metadata": {
                "current_screen_elements": ["VS Code", "main.py", "line 45", "TypeError"],  # Keyword repetition
                "predicted_next_steps": ["debug", "fix", "error"],  # Vague actions
                "screen_context_used": "VS Code main.py line 45 TypeError debug context"  # More keywords
            }
        }
    }
    
    context = {
        "current_transcription": "Application: VS Code Window: main.py Error: TypeError line 45 calculate_total debugging",
        "current_app": "VS Code",
        "visible_content": "def calculate_total(items): return sum(item['price'] for item in items)"
    }
    
    # Calculate semantic grounding score for gamed suggestion
    try:
        from gum.services.proactive_engine import ProactiveEngine
        engine = ProactiveEngine()

        work_item = {
            'title': gamed_suggestion['title'],
            'description': gamed_suggestion['description']
        }

        semantic_score = engine._calculate_semantic_grounding_score(work_item, context)

        print(f"   📊 Semantic grounding score: {semantic_score:.2f}")

        if semantic_score < 0.3:
            print("   ✅ SEMANTIC PROTECTION: Low semantic score for keyword-stuffed suggestion")
            print("   💡 SOLUTION: Semantic validation prevents gaming!")
        else:
            print("   🚨 SEMANTIC VULNERABILITY: High semantic score despite keyword stuffing")
            print("   💡 ISSUE: Semantic validation not robust enough")

    except Exception as e:
        print(f"   ⚠️  SEMANTIC TEST FAILED: {e}")
        # Fall back to word overlap
        suggestion_text = f"{gamed_suggestion['title']} {gamed_suggestion['description']}"
        transcription = context['current_transcription']

        suggestion_words = set(suggestion_text.lower().split())
        transcription_words = set(transcription.lower().split())
        overlap = len(suggestion_words.intersection(transcription_words))
        overlap_ratio = overlap / len(transcription_words) if transcription_words else 0

        print(f"   📊 Gamed suggestion overlap (fallback): {overlap}/{len(transcription_words)} = {overlap_ratio:.2%}")

        if overlap_ratio > 0.5:
            print("   🚨 GAMING ISSUE: High overlap score for keyword-stuffed, low-value suggestion")
            print("   💡 SOLUTION: Need semantic quality checks, not just word overlap")
    
    return True

def analyze_usefulness_criteria_gaps():
    """Analyze gaps in usefulness criteria that allow useless suggestions"""
    print("\n🔍 Analyzing Usefulness Criteria Gaps...")
    
    usefulness_gaps = []
    
    # Gap 1: No validation of suggestion accuracy
    usefulness_gaps.append("No validation that predictions are actually likely to occur")
    
    # Gap 2: No user skill level consideration
    usefulness_gaps.append("No consideration of user skill level (novice vs expert)")
    
    # Gap 3: No timing appropriateness validation
    usefulness_gaps.append("No validation that timing is actually appropriate for suggestion")
    
    # Gap 4: No duplicate detection
    usefulness_gaps.append("No detection of repetitive or duplicate suggestions")
    
    # Gap 5: No context sensitivity
    usefulness_gaps.append("No sensitivity to personal vs professional content")
    
    # Gap 6: No complexity matching
    usefulness_gaps.append("No matching of suggestion complexity to task complexity")
    
    print(f"   🚨 USEFULNESS GAPS: {len(usefulness_gaps)} critical gaps found")
    for gap in usefulness_gaps:
        print(f"   - {gap}")
    
    # Test specific gap: No accuracy validation
    print("\n   Example Gap: Prediction Accuracy")
    print("   Input: 'User in PowerPoint slide 1 of 50'")
    print("   Bad Prediction: 'I created slides 2-50 for your presentation'")
    print("   Reality: User might just be reviewing, not creating content")
    print("   💡 Missing: Intent detection (creating vs reviewing)")
    
    return len(usefulness_gaps) == 0

def main():
    """Run suggestion quality analysis"""
    print("🔍 SUGGESTION QUALITY ISSUES ANALYSIS")
    print("=" * 60)
    
    tests = [
        ("Prompt Logic Issues", analyze_prompt_quality_issues),
        ("Validation False Positives", analyze_validation_false_positives),
        ("Prediction Algorithm Flaws", analyze_prediction_algorithm_flaws),
        ("Specificity Requirement Gaming", test_specificity_requirement_gaming),
        ("Grounding Evidence Quality", analyze_grounding_evidence_quality),
        ("Prompt Bias Issues", analyze_prompt_bias_issues),
        ("Usefulness Criteria Gaps", analyze_usefulness_criteria_gaps)
    ]
    
    issues_found = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():  # Returns False if issues found
                issues_found.append(test_name)
        except Exception as e:
            print(f"   💥 {test_name} - CRASHED: {e}")
            issues_found.append(test_name)
    
    # Test realistic bad suggestions
    test_realistic_bad_suggestions()
    
    print("\n" + "=" * 60)
    
    if issues_found:
        print(f"🚨 SUGGESTION QUALITY ISSUES: {len(issues_found)} areas with problems")
        for issue in issues_found:
            print(f"   ❌ {issue}")
        
        print("\n💡 ROOT CAUSES OF BAD SUGGESTIONS:")
        print("   1. Word overlap scoring can be gamed with keyword stuffing")
        print("   2. Prediction algorithms use naive string matching, not semantic understanding")
        print("   3. No validation of suggestion accuracy or usefulness")
        print("   4. No context awareness for appropriateness")
        print("   5. Prompt bias toward over-confidence and forced specificity")
        print("   6. No consideration of user intent or skill level")
        
        return False
    else:
        print("🎉 NO MAJOR SUGGESTION QUALITY ISSUES FOUND")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)