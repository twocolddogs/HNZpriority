# Implementation Plan: Human-in-the-Loop (HITL) Validation Pipeline

This document outlines the tasks required to build a robust, scalable Human-in-the-Loop (HITL) validation system for the radiology exam standardization application.

## 1. Core Principles

The system will be built on the following principles:
- **Validation by Exception:** The human validator's default action is to do nothing. Mappings are considered "approved" unless explicitly flagged for failure or review.
- **Stateful & Iterative:** The validation status of each input is tracked persistently, allowing for multiple validation cycles.
- **Singleton Suspicion:** Mappings with only one corresponding input are automatically flagged for human review.
- **Decision Deferral:** Validators can skip a decision on an ambiguous item, allowing it to be re-evaluated in future runs with more data.
- **Targeted Reprocessing:** Validators can flag items for reprocessing with specific hints (e.g., "force secondary pipeline").

---

## 2. Task Breakdown

### Task 1: Data Models & State Management

The foundation of the system is a set of JSON files to manage state. These should be created in a new `validation/` directory.

#### 1.1. Create `validation_state.json` - DONE

This file is the master record of the validation status for every input.

- **Action:** Create a script `validation/initialize_state.py`.
- **Logic:**
    1.  Read the source input file (e.g., `hnz_hdp.json`).
    2.  For each input item, generate a `unique_input_id`. A good method is a SHA256 hash of a unique combination of fields (e.g., `exam_name` + `exam_code` + `data_source`).
    3.  Create a JSON object where keys are the `unique_input_id`.
    4.  The value for each key should be an object with the following schema:
        ```json
        {
          "unique_input_id": "sha256_hash_of_input_fields",
          "source_input": {
            "exam_name": "...",
            "exam_code": "...",
            "data_source": "..."
          },
          "status": "unprocessed",
          "approved_mapping": null,
          "reprocessing_hint": null,
          "history": [],
          "notes": null
        }
        ```
    5.  The `status` field can have one of the following values: `unprocessed`, `pending_review`, `approved`, `failed`, `needs_reprocessing`.

#### 1.2. Define `gold_standard_cache.json` - DONE

This file acts as a high-speed cache for permanently approved mappings. It will be generated automatically.

- **Schema:** A simple key-value JSON object.
  ```json
  {
    "unique_input_id_1": {
      "snomed_id": "12345",
      "clean_name": "CT of Head",
      "snomed_fsn": "Computed tomography of head (procedure)",
      "components": { "anatomy": ["head"], "modality": ["CT"], "confidence": 0.98 }
    },
    "unique_input_id_2": { }
  }```


#### 1.3. Define `failed_mappings.json` - DONE
This file is a cache for inputs that should never be processed again.

**Schema:** A key-value JSON object.
```json
{
  "unique_input_id_1": {
    "reason": "Validator marked as incorrect mapping.",
    "timestamp": "2023-10-27T10:00:00Z"
  }
}```

### Task 2: Backend Modifications
Update the core application to use the new caching and state management.

#### 2.1. Modify nhs_lookup_engine.py - DONE
Action: Add logic to the standardize_exam method to check caches first.
Logic:
At the very beginning of the method, before any processing, accept the unique_input_id as an argument.
Load gold_standard_cache.json and failed_mappings.json into memory (or a simple class-level cache).
Check if unique_input_id exists in the gold standard cache. If yes, return the cached result immediately.
Check if unique_input_id exists in the failed mappings cache. If yes, return an EXCLUDED_FAILED_VALIDATION error immediately.
If not found in either cache, proceed with the normal processing pipeline.

#### 2.2. Modify app.py (/parse_batch endpoint) - DONE
Action: Enhance the batch processing endpoint to accept and act on reprocessing hints.
Logic:
The exams list in the request payload should now allow an object containing the input data and any hints.
```json
{
  "exams": [
    {
      "input_data": { "exam_name": "...", "exam_code": "...", "modality_code": "..." },
      "unique_input_id": "sha256_hash...",
      "reprocessing_hint": {
        "force_secondary_pipeline": true,
        "use_reranker": "claude-3-haiku"
      }
    }
  ]
}```

Inside the _process_batch function, when looping through exams, pass these hints down to the process_exam_request function.
The process_exam_request function must use these hints to override default behavior (e.g., force enable_secondary to True or select a different reranker_key).

###Task 3: Create the HITL Orchestration Scripts
These scripts will be run from the command line to drive the validation cycle. They should reside in the validation/ directory.

#### 3.1. Create validation/prepare_batch.py - DONE
Action: This script reads the state file and creates a list of exams that need processing.
Logic:
Load validation/validation_state.json.
Initialize an empty list exams_to_process.
Iterate through every entry in the state file.
If an entry's status is NOT approved and NOT failed, add it to the exams_to_process list.
Format each item for the /parse_batch endpoint, including input_data, unique_input_id, and any reprocessing_hint.
Save the exams_to_process list to a temporary file (e.g., validation/_current_batch.json).

#### 3.2. Create validation/generate_view.py - DONE
Action: This script takes the output from the batch run and prepares it for the UI.
Logic:
Load the consolidated_results.json file generated by /parse_batch.
Initialize an empty dictionary grouped_by_snomed = {}.
Iterate through the results and group them into grouped_by_snomed using the matched snomed_id as the key.
Iterate through the grouped_by_snomed dictionary:
For each group, count the number of items.
If count == 1, this is a singleton. Add a suspicion_flag: "singleton_mapping" to the single item in that group.
For every item in every group, apply the "smart highlighting" logic:
Add a needs_attention: true flag if confidence < 0.85 OR ambiguous == true OR suspicion_flag exists.
Save the final, structured, and flagged data to validation/view_data.json. This file will be loaded by the UI.

#### 3.3. Create validation/update_state.py - DONE
Action: This script applies the human's decisions to the master state file.
Logic:
Requires one argument: the path to the human's decision file (e.g., decisions.json).
The decisions.json file will be an object mapping unique_input_id to a decision:
Generated ```json
{
  "sha256_hash_1": { "action": "fail", "note": "Maps to wrong body part." },
  "sha256_hash_2": { "action": "review", "hint": { "use_reranker": "medcpt" } },
  "sha256_hash_3": { "action": "defer" }
}```

Load validation/validation_state.json.
Load the consolidated_results.json from the last run to know which items were processed.
Iterate through all items from the last run:
Check if the item's unique_input_id has a decision in the decisions.json file.
If a decision exists: Update the state file accordingly (status: "failed", status: "needs_reprocessing", or status: "pending_review").
If NO decision exists (The "Approve by Default" case): Update the item's status in the state file to status: "approved".
Save the updated validation/validation_state.json.
Finally, regenerate caches:
Create a new validation/gold_standard_cache.json by iterating through the state file and including all entries where status == "approved".
Create a new validation/failed_mappings.json from all entries where status == "failed".

### Task 4: Build the Validation UI
This can be a simple, local, single-page static HTML file that uses JavaScript.

#### 4.1. Design validation_ui/index.html - DONE
Action: Describe the necessary HTML elements.
Required Components:
A file input element to allow the user to load the view_data.json.
A main container element (e.g., a div) where the validation view will be dynamically rendered.
A "Save Decisions" button element to trigger the download of the decision file.
A script tag to include the JavaScript file (app.js).

#### 4.2. Implement validation_ui/app.js - DONE
Action: Implement the client-side logic for rendering and interaction.
Logic:
loadData() function: Reads the view_data.json file selected by the user.
renderView(data) function:
Takes the parsed view_data.json as input.
Dynamically creates the HTML for the grouped view.
Uses the needs_attention flag to apply a CSS class (e.g., .highlight) to rows requiring review.
Creates the [Review ▼], [Fail], and [Defer] buttons/dropdowns for each row. Each button should store the unique_input_id in a data attribute.
Event Listeners:
Attach click listeners to all action buttons.
When a button is clicked, store the decision in a global JavaScript object, e.g., let userDecisions = {};.
The key should be the unique_input_id from the row's data attribute.
Visually update the row's "Status" to show it has been actioned (e.g., "Flagged for Fail").
saveDecisions() function:
Attached to the "Save Decisions" button.
Converts the userDecisions object to a JSON string.
Triggers a browser download of this JSON, naming the file decisions.json. This is the file that will be passed to update_state.py.

### Task 5: Document the End-to-End Workflow - DONE
Create a validation/README.md file explaining the cycle to a human user.

Run python validation/initialize_state.py (only once).
Run python validation/prepare_batch.py to select which exams to process.
Run your main application's batch processing using validation/_current_batch.json as input.
Run python validation/generate_view.py to create the UI data file.
Open validation_ui/index.html in a browser, load validation/view_data.json, and make decisions.
Click "Save Decisions" to download decisions.json.
Run python validation/update_state.py decisions.json to apply the changes.
Repeat the cycle from step 2.