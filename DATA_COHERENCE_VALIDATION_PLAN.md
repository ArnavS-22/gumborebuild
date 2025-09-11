# Data Coherence Validation Implementation Plan

## Problem Analysis

The current suggestion system is making assumptions not supported by transcription data. For example:

**❌ CURRENT PROBLEM:**
- Transcription shows: User browsing Zavion interface + Gift Pleasanton website
- AI assumes: User is "planning a local community event"
- Suggestion: "Use Zavion's AI Assistant for Event Planning"
- **ISSUE**: No evidence in transcription supports event planning assumption

## Solution Architecture

### 1. Data Coherence Validator Module (`data_coherence_validator.py`)

**Core Components:**
- `TranscriptionAnalyzer`: Extract concrete facts from transcription data
- `EvidenceMapper`: Map suggestions back to specific data points
- `AssumptionDetector`: Identify when AI is filling gaps with assumptions
- `CoherenceScorer`: Rate how well data supports each suggestion

### 2. Validation Rules Engine

**REJECT Criteria:**
- Suggestion assumes activities not shown in transcription
- Suggestion assumes context not present in data
- Suggestion requires knowledge not available in observations
- Suggestion contradicts actual transcription content

**ACCEPT Criteria:**
- Suggestion directly references transcription content
- Suggestion follows logically from observed behavior
- Suggestion doesn't require assumptions about missing context
- Suggestion uses only concrete data points

### 3. Evidence Mapping System

**For each suggestion, validate:**
- **Transcription Support**: Which specific transcription data supports this?
- **Behavioral Pattern Match**: Does this align with observed patterns?
- **Context Coherence**: Does this create a logical narrative?
- **Assumption Detection**: What assumptions are being made?

### 4. Confidence Scoring Algorithm

**Scoring Factors:**
- **Direct Evidence Score** (0-1): How much transcription directly supports this
- **Pattern Consistency Score** (0-1): How well this matches observed patterns
- **Assumption Penalty** (-0.5 to 0): Penalty for each assumption made
- **Context Coherence Score** (0-1): How well this fits the complete picture

**Final Score = (Direct Evidence + Pattern Consistency + Context Coherence) + Assumption Penalty**

## Implementation Strategy

### Phase 1: Core Validator
1. Create `TranscriptionAnalyzer` to extract concrete facts
2. Build `EvidenceMapper` to link suggestions to data
3. Implement `AssumptionDetector` to catch hallucinations

### Phase 2: Validation Rules
1. Define strict validation criteria
2. Create rule engine for accept/reject decisions
3. Implement confidence scoring algorithm

### Phase 3: Integration
1. Integrate validator into `ProactiveEngine`
2. Integrate validator into `GumboEngine`
3. Update prompts to enforce strict data adherence

### Phase 4: Testing
1. Test with example scenarios from user
2. Validate against known problematic cases
3. Ensure no false positives/negatives

## Example Validation Flow

**Input Transcription:**
```
Application: Electron
Window Title: Zavion
Navigation: Home, Timeline, Suggestions
Current Screen: Safari browsing cityofpleasantonca.gov/Business Promotion
```

**AI Suggestion:**
"Use Zavion's AI Assistant for Event Planning"

**Validation Process:**
1. **Extract Facts**: User is in Zavion app, browsing city website
2. **Map Evidence**: No evidence of event planning in transcription
3. **Detect Assumptions**: AI assumes "event planning" from city website browsing
4. **Score Confidence**: Low (0.2) - suggestion not supported by data
5. **Decision**: REJECT - assumption not supported by transcription

**Better Suggestion:**
"You're browsing Pleasanton's business promotion page in Safari while having Zavion open. Based on the Gift Pleasanton content visible, you might want to explore the eGift card program details in the current browser tab."

## Key Validation Rules

### Rule 1: Transcription Fidelity
- Suggestions MUST reference specific content from transcription
- No assumptions about activities not explicitly shown
- Use exact app names, window titles, content from observations

### Rule 2: Evidence Mapping
- Each suggestion must map to specific transcription data points
- Clear chain of evidence from observation to suggestion
- No logical leaps without supporting data

### Rule 3: Context Boundaries
- Stay within the bounds of what transcription actually shows
- Don't assume broader context not present in data
- Acknowledge limitations when data is insufficient

### Rule 4: Assumption Detection
- Flag any inference not directly supported by transcription
- Penalize suggestions that require external knowledge
- Prefer conservative interpretations over speculative ones

## Expected Outcomes

**Before Validation:**
- AI assumes user is "planning events" from city website browsing
- Suggestions reference activities not shown in transcription
- High rate of irrelevant or speculative suggestions

**After Validation:**
- AI only suggests based on concrete transcription data
- Suggestions reference specific observed activities
- Higher relevance and accuracy of suggestions
- Clear evidence trail for each suggestion

## Integration Points

### ProactiveEngine Integration
- Add validation step after suggestion generation
- Filter out suggestions that fail coherence checks
- Provide feedback to improve future suggestions

### GumboEngine Integration
- Validate suggestions before utility scoring
- Ensure contextual retrieval supports suggestions
- Maintain evidence chain through entire pipeline

### Prompt Updates
- Add strict data adherence requirements
- Include validation examples in prompts
- Emphasize evidence-based reasoning

## Success Metrics

1. **Assumption Reduction**: Decrease in suggestions making unsupported assumptions
2. **Evidence Coverage**: Increase in suggestions with clear transcription support
3. **Relevance Improvement**: Higher user satisfaction with suggestion accuracy
4. **False Positive Reduction**: Fewer suggestions about activities not actually happening

This validation system will ensure suggestions are grounded in actual transcription data rather than AI assumptions.