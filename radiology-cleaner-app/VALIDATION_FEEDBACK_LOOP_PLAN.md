# Validation Feedback Loop Implementation Plan

## 1. Objective

To create a robust, closed-loop system where human-in-the-loop (HITL) validation decisions are fed back into the main processing pipeline. This will ensure that the system learns from human corrections, improving accuracy and efficiency over time.

The system will handle three validation states:
1.  **Approved:** The mapping is correct. Future requests with the same input should automatically use this approved mapping.
2.  **Rejected:** The mapping is incorrect. Future requests with the same input should never be matched to the rejected SNOMED ID.
3.  **Skipped:** The mapping is uncertain. Future requests with the same input should be re-processed from scratch as if for the first time.

## 2. Current System Architecture

The validation system is already partially implemented with:
- **Validation UI**: Interactive interface for human validation decisions (`/validation/`)
- **Hash-based Keys**: SHA-256 hashes of complete request data for unique identification
- **Structured Storage**: JSON files with complete mapping metadata and validation notes
- **Pipeline Integration**: Existing hooks for validation in the main processing flow

## 3. Key Components & Files to Modify

-   **`backend/nhs_lookup_engine.py`**: The core processing engine. This will be modified to load and act upon the validation decisions.
-   **`backend/app.py`**: The main Flask application. This will be modified to provide an API endpoint for reloading the validation caches without a server restart.
-   **`validation/approved_mappings_cache.json`**: The source of truth for approved mappings (uses SHA-256 hash keys).
-   **`validation/rejected_mappings.json`**: The source of truth for rejected mappings.

## 4. Detailed Implementation Steps

### Step 4.1: Modify `backend/nhs_lookup_engine.py`

#### A. Load Validation Caches on Initialization

-   In the `__init__` method, after initializing the primary components, call a new method `_load_validation_caches()`.
-   This new method will:
    -   Construct the correct file paths to `validation/approved_mappings_cache.json` and `validation/rejected_mappings.json`, navigating up from the `backend` directory.
    -   **Load `approved_mappings_cache.json`**:
        -   Parse the JSON file.
        -   Create a dictionary `self.approved_mappings`.
        -   The **key** for the dictionary will be the SHA-256 hash used by the validation system (matches current implementation).
        -   The **value** will be the complete mapping_data section from the approved cache.
    -   **Load `rejected_mappings.json`**:
        -   Parse the JSON file.
        -   Create a dictionary `self.rejected_mappings`.
        -   The **key** will be the SHA-256 hash matching the approved mappings format.
        -   The **value** will be a `set` of rejected SNOMED CT IDs for that specific input hash. Using a set allows for efficient checking (`O(1)`) and prevents duplicate entries.
    -   **Error Handling**: Include try-catch blocks for malformed JSON files and missing files.
    -   **Logging**: Log the number of approved/rejected mappings loaded for monitoring.

#### B. Hash Generation for Request Matching

-   Create a method `_generate_request_hash()` that matches the validation system's hash generation:
    -   Takes the complete request data (exam_name, modality_code, data_source, etc.)
    -   Generates SHA-256 hash using the same algorithm as the validation UI
    -   Returns the hash string for lookup in validation caches

#### C. Integrate Validation Logic into `standardize_exam`

-   At the very beginning of the `standardize_exam` method, perform the following checks:
    1.  **Check for Approved Mapping (Cache Hit):**
        -   Generate the request hash from the input parameters.
        -   If this hash exists in `self.approved_mappings`:
            -   Retrieve the corresponding approved mapping data.
            -   Add a `validation_status` field to the result (e.g., `{'validation_status': 'approved_by_human'}`).
            -   Set the confidence score to `1.0`.
            -   Immediately `return` this result, bypassing the entire standard pipeline.
    2.  **Check for Rejected Mappings:**
        -   Generate the request hash.
        -   If the hash exists in `self.rejected_mappings`, retrieve the `set` of rejected SNOMED IDs.
        -   Pass this set down to the candidate retrieval and reranking stages.
-   **Modify Candidate Filtering:**
    -   After the initial candidate retrieval from FAISS, add a filtering step.
    -   Iterate through the candidates and remove any candidate whose `snomed_concept_id` is present in the `set` of rejected IDs for the current input.

#### D. Create a Public Method for Reloading Caches

-   Create a new public method `reload_validation_caches()`.
-   This method will simply call `_load_validation_caches()` to refresh the `self.approved_mappings` and `self.rejected_mappings` dictionaries from the JSON files.
-   Include comprehensive error handling and logging for cache reload operations.

### Step 4.2: Modify `backend/app.py`

#### A. Add a New API Endpoint

-   Create a new Flask route: `@app.route('/admin/reload-validation-cache', methods=['POST'])`.
-   This endpoint will be responsible for triggering the cache reload.
-   **Security**: Add authentication middleware to prevent unauthorized cache reloads.

#### B. Implement the Endpoint Logic

-   The function for this endpoint will:
    1.  **Authentication Check**: Verify admin credentials or API key.
    2.  Ensure the `nhs_lookup_engine` global object is initialized.
    3.  Call the `nhs_lookup_engine.reload_validation_caches()` method.
    4.  Return a JSON response indicating success or failure, including the number of approved and rejected mappings that were loaded.
    5.  **Error Handling**: Return appropriate HTTP status codes for different failure scenarios.

#### C. Automatic Cache Reload Triggers

-   **File Watching**: Consider implementing file system watchers to automatically reload caches when validation files change.
-   **Startup Reload**: Ensure validation caches are loaded during application startup.
-   **Periodic Reload**: Optionally implement periodic cache refresh (e.g., every hour) for production environments.

## 5. Data and Control Flow Diagram

```
[User Input] -> /parse_enhanced
      |
      v
[app.py] -> NHSLookupEngine.standardize_exam(input)
      |
      v
[NHSLookupEngine]
      |
      |--> 1. Generate SHA-256 hash from request data
      |      |
      |      v
      |--> 2. Check Approved Cache (hash-based lookup)?
      |      |
      |      |-- YES (Hit) -> Return cached result (Confidence: 1.0, validation_status: 'approved_by_human') --> [app.py] -> [User]
      |      |
      |      `-- NO (Miss)
      |           |
      |           v
      |--> 3. Check Rejected Mappings (hash-based lookup)?
      |      |
      |      |-- YES (Hit) -> Get rejected SNOMED IDs set
      |      |-- NO (Miss) -> Continue with empty rejected set
      |           |
      |           v
      |--> 4. Proceed with standard pipeline (FAISS, Reranking)
      |           |
      |           |--> 5. Filter candidates: Remove any with SNOMED IDs in rejected set
      |           |
      |           v
      |      Return best non-rejected candidate --> [app.py] -> [User]


[Validation UI] -> Human validation decisions -> Saves to `approved_mappings_cache.json` & `rejected_mappings.json`
      |
      v
[Admin/Automatic Trigger] -> POST /admin/reload-validation-cache (with auth)
      |
      v
[app.py] -> NHSLookupEngine.reload_validation_caches()
      |
      v
[NHSLookupEngine] -> Reloads caches from JSON files (with error handling)
```

## 6. Implementation Priorities

### Phase 1: Core Integration (High Priority)
1. Implement validation cache loading in `nhs_lookup_engine.py`
2. Add hash generation method matching validation UI
3. Integrate approved mapping cache hits (immediate return)
4. Add rejected mapping filtering in candidate selection

### Phase 2: API & Automation (Medium Priority)  
1. Add admin endpoint for cache reload with authentication
2. Implement automatic cache loading on startup
3. Add comprehensive error handling and logging

### Phase 3: Advanced Features (Low Priority)
1. File system watchers for automatic reload
2. Periodic cache refresh mechanisms
3. Monitoring and metrics for validation effectiveness
4. Performance optimization for large validation datasets

## 7. Testing Strategy

### Unit Tests
- Test hash generation matches validation UI
- Test approved mapping cache hits
- Test rejected mapping filtering
- Test cache reload functionality

### Integration Tests  
- Test end-to-end validation feedback loop
- Test API endpoint security
- Test error handling for malformed validation files

### Performance Tests
- Measure impact of validation checks on response times
- Test with large validation datasets
- Optimize cache lookup performance

## 8. Deployment Considerations

### Production Safety
- Implement graceful degradation if validation files are corrupted
- Ensure validation cache failures don't break main pipeline
- Add monitoring for cache hit rates and effectiveness

### Data Consistency
- Validate SHA-256 hash consistency between validation UI and engine
- Implement backup and recovery for validation data
- Consider versioning for validation decisions

### Security
- Secure admin endpoints with proper authentication
- Audit log for validation cache modifications
- Rate limiting for cache reload operations
