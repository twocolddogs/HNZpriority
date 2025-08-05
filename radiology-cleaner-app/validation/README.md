# Human-in-the-Loop (HITL) Validation Pipeline

This directory contains the complete Human-in-the-Loop validation system for the radiology exam standardization application. The system allows human validators to review, correct, and approve automated mapping results using a "validation by exception" approach.

## Core Principles

- **Validation by Exception**: Items are automatically approved unless explicitly flagged
- **Stateful & Iterative**: Validation status is tracked persistently across multiple cycles
- **Singleton Suspicion**: Single-item mappings are automatically flagged for review
- **Decision Deferral**: Validators can skip decisions on ambiguous items
- **Targeted Reprocessing**: Items can be flagged for reprocessing with specific hints

## System Architecture

### Data Files

| File | Purpose | When Created |
|------|---------|--------------|
| `validation_state.json` | Master state tracking for all inputs | Step 1: Initialize |
| `gold_standard_cache.json` | Cache of approved mappings | Step 5: Update state |
| `failed_mappings.json` | Cache of rejected mappings | Step 5: Update state |
| `_current_batch.json` | Current batch for processing | Step 2: Prepare batch |
| `view_data.json` | UI-ready validation data | Step 4: Generate view |

### Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `initialize_state.py` | Create initial validation state | Source data (e.g., hnz_hdp.json) | validation_state.json |
| `prepare_batch.py` | Select items for processing | validation_state.json | _current_batch.json |
| `generate_view.py` | Prepare data for UI | consolidated_results.json | view_data.json |
| `update_state.py` | Apply human decisions | decisions.json | Updated state + caches |

### UI Components

| Component | Purpose |
|-----------|---------|
| `validation_ui/index.html` | Web interface for human review |
| `validation_ui/app.js` | JavaScript application logic |

## Complete Workflow

### Step 1: Initialize Validation State

Create the master validation state from your source data:

```bash
# Initialize from HNZ hospital data
python3 validation/initialize_state.py backend/core/hnz_hdp.json

# Or from sanity test data
python3 validation/initialize_state.py backend/core/sanity_test.json

# Custom output location
python3 validation/initialize_state.py backend/core/hnz_hdp.json --output custom_state.json
```

**What this does:**
- Reads source input data (exam names, codes, etc.)
- Generates unique SHA256 IDs for each input
- Creates validation state entries with status "unprocessed"
- Saves to `validation/validation_state.json`

### Step 2: Prepare Processing Batch

Select items that need processing:

```bash
# Default: select unprocessed, pending_review, needs_reprocessing
python3 validation/prepare_batch.py

# Custom state file
python3 validation/prepare_batch.py --state custom_state.json

# Custom status selection
python3 validation/prepare_batch.py --include unprocessed needs_reprocessing
```

**What this does:**
- Loads validation state
- Filters items by status (excludes approved/failed)
- Formats items for `/parse_batch` endpoint
- Includes reprocessing hints if specified
- Saves to `validation/_current_batch.json`

### Step 3: Run Batch Processing

Process the batch through your application:

```bash
# Start your backend server
python3 backend/app.py

# In another terminal, process the batch
curl -X POST http://localhost:10000/parse_batch \
     -H "Content-Type: application/json" \
     -d @validation/_current_batch.json

# This creates consolidated_results.json
```

**What this does:**
- Processes each exam through the standardization pipeline
- Applies reprocessing hints if specified
- Generates consolidated_results.json with all results

### Step 4: Generate UI View Data

Prepare results for human review:

```bash
# Default input/output
python3 validation/generate_view.py

# Custom files
python3 validation/generate_view.py --input batch_output.json --output custom_view.json
```

**What this does:**
- Groups results by SNOMED ID
- Flags singleton mappings for review
- Applies smart highlighting (low confidence, ambiguous, errors)
- Creates UI-ready data structure
- Saves to `validation/view_data.json`

### Step 5: Human Validation

1. **Open the validation UI:**
   ```bash
   # Serve the UI (choose one method)
   python3 -m http.server 8000  # Then visit http://localhost:8000/validation_ui/
   # OR open validation_ui/index.html directly in browser
   ```

2. **Load validation data:**
   - Click "Load validation data" in the UI
   - Select `validation/view_data.json`

3. **Review and make decisions:**
   - **Red items**: Need attention (low confidence, singletons, errors)
   - **Green items**: High confidence, likely correct
   - **Actions available:**
     - **Approve**: Explicitly approve this mapping
     - **Fail**: Mark as incorrect, exclude from future processing
     - **Review**: Flag for reprocessing with hints
     - **Defer**: Skip decision, review in future cycle

4. **Save decisions:**
   - Click "Save Decisions" to download `decisions.json`

### Step 6: Apply Decisions and Update State

Apply human decisions to the validation state:

```bash
# Apply decisions from UI
python3 validation/update_state.py decisions.json

# Custom state file
python3 validation/update_state.py decisions.json --state custom_state.json

# Custom results file
python3 validation/update_state.py decisions.json --results batch_output.json
```

**What this does:**
- Loads human decisions from JSON file
- Applies explicit decisions (fail, review, defer, approve)
- **Auto-approves items without explicit decisions** (key principle!)
- Updates validation state with new statuses
- Regenerates cache files:
  - `gold_standard_cache.json`: Approved mappings
  - `failed_mappings.json`: Rejected mappings

### Step 7: Repeat Cycle

For iterative improvement, repeat from Step 2:

```bash
# Prepare next batch (will process remaining unprocessed items)
python3 validation/prepare_batch.py

# Continue with steps 3-6...
```

## Backend Integration

### Cache Integration (TODO)

The backend needs to be modified to use the validation caches:

**In `nhs_lookup_engine.py`:**
- Check `gold_standard_cache.json` before processing
- Check `failed_mappings.json` to exclude rejected items
- Return cached results immediately if found

**In `app.py`:**
- Support reprocessing hints in batch payload
- Pass hints to processing pipeline
- Override default behavior based on hints

### Required Modifications

1. **Cache Loading:**
   ```python
   def load_validation_caches(self):
       try:
           with open('validation/gold_standard_cache.json', 'r') as f:
               self.gold_cache = json.load(f)
           with open('validation/failed_mappings.json', 'r') as f:
               self.failed_cache = json.load(f)
       except Exception as e:
           logger.warning(f"Could not load validation caches: {e}")
           self.gold_cache, self.failed_cache = {}, {}
   ```

2. **Cache Checking:**
   ```python
   def standardize_exam(self, input_exam, ..., unique_input_id=None):
       if unique_input_id:
           if unique_input_id in self.gold_cache:
               return self.gold_cache[unique_input_id]
           if unique_input_id in self.failed_cache:
               return {'error': 'EXCLUDED_FAILED_VALIDATION'}
       # Continue with normal processing...
   ```

## File Format Specifications

### validation_state.json

```json
{
  "_metadata": {
    "created_at": "2023-10-27T10:00:00Z",
    "source_file": "backend/core/hnz_hdp.json",
    "total_items": 1000,
    "version": "1.0"
  },
  "sha256_hash_1": {
    "unique_input_id": "sha256_hash_1",
    "source_input": {
      "exam_name": "CT HEAD",
      "exam_code": "CTHD",
      "data_source": "HNZ"
    },
    "status": "approved",
    "approved_mapping": {
      "snomed_id": "12345",
      "clean_name": "CT of Head",
      "confidence": 0.98
    },
    "reprocessing_hint": null,
    "history": [...],
    "notes": "Auto-approved by validation pipeline"
  }
}
```

### decisions.json (from UI)

```json
{
  "sha256_hash_1": {
    "action": "fail",
    "note": "Maps to wrong body part"
  },
  "sha256_hash_2": {
    "action": "review",
    "note": "Needs secondary pipeline",
    "hint": {
      "force_secondary_pipeline": true,
      "use_reranker": "claude-3-haiku"
    }
  },
  "sha256_hash_3": {
    "action": "defer",
    "note": "Ambiguous, need more examples"
  }
}
```

## Status Values

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `unprocessed` | Never processed | Include in batch |
| `pending_review` | Deferred by validator | Include in batch |
| `needs_reprocessing` | Flagged for reprocessing | Include in batch with hints |
| `approved` | Validated as correct | Cache and exclude from processing |
| `failed` | Marked as incorrect | Cache and exclude from processing |

## Troubleshooting

### Common Issues

1. **"Validation state file not found"**
   - Run `initialize_state.py` first to create the state file

2. **"Results file not found"**
   - Ensure batch processing completed successfully
   - Check that `consolidated_results.json` was created

3. **"No decisions to save"**
   - Make at least one validation decision in the UI before saving

4. **Backend not using caches**
   - The cache integration is not yet implemented
   - This is a TODO item for backend modifications

### Debug Tips

1. **Check state file status distribution:**
   ```bash
   python3 -c "
   import json
   with open('validation/validation_state.json', 'r') as f:
       state = json.load(f)
   status_count = {}
   for k, v in state.items():
       if k.startswith('_'): continue
       status = v.get('status', 'unknown')
       status_count[status] = status_count.get(status, 0) + 1
   print(status_count)
   "
   ```

2. **Validate batch file format:**
   ```bash
   python3 validation/prepare_batch.py --help
   ```

3. **Check view data summary:**
   ```bash
   python3 -c "
   import json
   with open('validation/view_data.json', 'r') as f:
       data = json.load(f)
   print(data['_metadata']['summary'])
   "
   ```

## Performance Considerations

- **Large datasets**: The system handles thousands of items efficiently
- **Memory usage**: View data is loaded entirely in browser, consider chunking for very large datasets
- **Processing time**: Batch processing time depends on pipeline complexity
- **Cache benefits**: Approved/failed items are processed instantly on subsequent runs

## Security Notes

- All validation data is stored locally
- No sensitive medical data is transmitted over networks
- Human decisions are stored in JSON format for auditability
- SHA256 hashes provide anonymization while maintaining uniqueness