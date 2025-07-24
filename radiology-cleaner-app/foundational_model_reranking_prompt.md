# Foundational Model Re-ranking Prompt

This prompt is designed for Claude/GPT to re-rank NHS exam candidates in the radiology cleaner application.

## Prompt Template

```
You are a medical imaging specialist helping standardize radiology exam names to NHS codes. 

TASK: Rank these candidate NHS exams from most to least appropriate for the input exam.

INPUT EXAM: "{input_exam}"

CANDIDATES:
{numbered_list_of_candidates_with_codes_and_descriptions}

RANKING CRITERIA:
1. **Anatomical match** - exact anatomy > broader anatomy > related anatomy
2. **Modality match** - CT/MRI/US/X-ray must match exactly 
3. **Contrast match** - with/without contrast must align
4. **Laterality match** - left/right/bilateral specificity
5. **Clinical appropriateness** - diagnostic vs interventional context
6. **Complexity match** - simple exams should map to simple codes

RESPONSE FORMAT:
Return ONLY a JSON array of the candidate numbers in ranked order (best first):
[candidate_number, candidate_number, ...]

EXAMPLES:
Input: "CT chest with contrast"
Candidates: 
1. CT Chest with IV Contrast
2. CT Thorax without Contrast  
3. MRI Chest with Contrast
Response: [1, 3, 2]

Input: "Left knee MRI" 
Candidates:
1. MRI Knee Bilateral
2. MRI Left Knee
3. MRI Right Knee
Response: [2, 1, 3]
```

## Implementation Notes

- This prompt replaces or supplements the MedCPT re-ranking stage
- The JSON response format allows easy integration with existing scoring pipeline
- Focuses on clinical reasoning while maintaining structured output
- Can be used with Claude, GPT-4, or other foundational models