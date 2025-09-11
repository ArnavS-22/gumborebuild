# System Prompt Fixes for Data Coherence

## Problem Analysis

**Current Issue:** The AI is making assumptions not supported by transcription data.

**Example Problem:**
- **Transcription shows:** User browsing Zavion interface + Gift Pleasanton website
- **AI assumes:** User is "planning a local community event" 
- **AI suggests:** "Use Zavion's AI Assistant for Event Planning"
- **ISSUE:** No evidence in transcription supports event planning assumption

## Root Cause: Prompts Allow Assumptions

The current prompts have these problems:

1. **Assumption-Encouraging Language:**
   - "Based on your pattern of..." (assumes patterns apply to current situation)
   - "You'll need..." (assumes future needs without evidence)
   - "Your project..." (assumes user has a project)
   - "Your team..." (assumes user has a team)

2. **Gap-Filling Instructions:**
   - Prompts tell AI to "predict" and "anticipate" 
   - This encourages filling gaps with assumptions
   - No strict boundaries on what data can be used

3. **Context Mixing:**
   - Behavioral patterns mixed with current transcription
   - AI treats patterns as current facts
   - No clear separation between "observed" vs "inferred"

## Solution: Strict Data-Only Prompts

### Core Principles for New Prompts:

1. **ONLY USE CONCRETE TRANSCRIPTION DATA**
   - Reference only what is explicitly shown in current transcription
   - No assumptions about activities not directly observed
   - No gap-filling or speculation

2. **EXPLICIT EVIDENCE REQUIREMENTS**
   - Every suggestion must cite specific transcription content
   - Use exact app names, window titles, visible text from transcription
   - No suggestions without direct supporting evidence

3. **ASSUMPTION PROHIBITION**
   - Explicitly forbid assumption-making language
   - Reject suggestions that require context not in transcription
   - Force AI to acknowledge when data is insufficient

4. **STRICT VALIDATION RULES IN PROMPTS**
   - Built-in validation criteria
   - Self-checking mechanisms
   - Clear accept/reject criteria

## Prompt Rewrite Strategy

### Current Problematic Prompt Patterns:
```
❌ "Based on your pattern of creating multiple copies for iterations..."
❌ "You'll need a counter-deck in the next 2-3 games..."
❌ "Your team can access the project directly..."
❌ "Based on your pattern of losing to air units..."
```

### New Strict Data-Only Patterns:
```
✅ "The transcription shows you are currently in [specific app] viewing [specific content]..."
✅ "Based on the visible text '[exact quote from transcription]'..."
✅ "The current screen shows [specific UI elements from transcription]..."
✅ "Since the transcription indicates [specific observed action]..."
```

## Specific Prompt Fixes Needed

### 1. ProactiveEngine Prompt (`ENHANCED_PROACTIVE_UNIVERSAL_EXPERT_PROMPT`)

**Current Problems:**
- Mixes behavioral patterns with current activity
- Encourages "prediction" and "anticipation"
- Allows assumptions about user goals

**Fix Strategy:**
- Separate current transcription analysis from behavioral patterns
- Only suggest based on what's currently visible
- Require explicit transcription quotes for each suggestion

### 2. GumboEngine Prompt (`MULTI_CANDIDATE_GENERATION_PROMPT`)

**Current Problems:**
- "MUST predict next 5-30 minute needs" encourages speculation
- Allows connecting patterns to current activity without evidence
- Examples show assumption-making

**Fix Strategy:**
- Change from "predict" to "observe and respond"
- Require current transcription evidence for all suggestions
- Update examples to show strict data adherence

### 3. New Validation Rules in Prompts

**Add These Explicit Rules:**

```
STRICT DATA ADHERENCE RULES:
1. ONLY reference content explicitly shown in current transcription
2. QUOTE exact text from transcription to support each suggestion
3. NO assumptions about activities not directly observed
4. NO speculation about user goals, projects, or teams
5. If transcription data is insufficient, acknowledge limitations
6. REJECT any suggestion requiring external context

VALIDATION CHECKLIST (AI must check each suggestion):
□ Does this reference specific content from current transcription?
□ Can I quote exact text that supports this suggestion?
□ Am I making any assumptions about context not shown?
□ Does this require knowledge not in the transcription?
□ Would this suggestion make sense to someone who only saw the transcription?
```

## Implementation Plan

### Phase 1: Fix ProactiveEngine Prompts
1. Rewrite `ENHANCED_PROACTIVE_UNIVERSAL_EXPERT_PROMPT`
2. Add strict validation rules
3. Remove assumption-encouraging language
4. Test with the problematic example

### Phase 2: Fix GumboEngine Prompts  
1. Rewrite `MULTI_CANDIDATE_GENERATION_PROMPT`
2. Update examples to show strict data adherence
3. Remove "prediction" language
4. Add transcription-only requirements

### Phase 3: Add Validation Instructions
1. Add self-validation checklist to prompts
2. Require evidence citations
3. Add assumption detection instructions
4. Test with edge cases

## Expected Results

**Before Fix:**
```json
{
  "title": "Use Zavion's AI Assistant for Event Planning",
  "description": "Generate a list of potential venues in Downtown Pleasanton for your community event",
  "rationale": "You're researching local events, and Zavion's AI can quickly provide venue options"
}
```

**After Fix:**
```json
{
  "title": "Explore Gift Pleasanton details in current Safari tab",
  "description": "The transcription shows you're viewing 'Business Promotion - City of Pleasanton' with 'Gift Pleasanton' content visible. You could explore the eGift card program details currently displayed.",
  "rationale": "Based on visible content 'Gift Pleasanton' in current Safari tab showing city business promotion page"
}
```

## Key Differences:

1. **Evidence-Based:** References specific transcription content
2. **No Assumptions:** Doesn't assume "event planning" from city website
3. **Current Focus:** Suggests action on currently visible content
4. **Explicit Quotes:** Uses exact text from transcription
5. **Realistic Scope:** Stays within bounds of observed data

This approach will eliminate assumption-making while maintaining helpful suggestions based on actual user activity.