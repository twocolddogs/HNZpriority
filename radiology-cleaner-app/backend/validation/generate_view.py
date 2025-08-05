import json
import os
import logging
from datetime import datetime
import uuid
import math

from r2_cache_manager import R2CacheManager

logger = logging.getLogger(__name__)

def generate_view_data():
    """
    Generates the view_data.json file for the Human-in-the-Loop (HITL) validation UI.
    This function fetches the latest batch processing results from R2, processes them
    into a structured format, and saves the view data to a temporary file.
    """
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        raise Exception("R2 storage not available. Cannot generate view data.")

    # 1. Fetch the latest batch results from R2
    try:
        # Get the most recent batch results file
        list_response = r2_manager.list_objects(prefix="batch-results/")
        latest_file_key = None
        if list_response:
            # Sort by LastModified (datetime object), newest first
            list_response.sort(key=lambda x: x['LastModified'], reverse=True)
            latest_file_key = list_response[0]['Key']
            logger.info(f"Found latest batch results file on R2: {latest_file_key}")
        
        if not latest_file_key:
            raise FileNotFoundError("No batch results files found on R2.")

        # Download the latest file
        temp_dir = os.environ.get('RENDER_DISK_PATH', '/tmp') # Use /tmp as fallback
        os.makedirs(temp_dir, exist_ok=True)
        latest_file_name = os.path.basename(latest_file_key)
        temp_download_path = os.path.join(temp_dir, latest_file_name)

        logger.info(f"Downloading {latest_file_key} from R2 to {temp_download_path}...")
        if not r2_manager.download_object(latest_file_key, temp_download_path):
            raise Exception(f"Failed to download {latest_file_key} from R2.")
        logger.info(f"Successfully downloaded {latest_file}.")

        with open(temp_download_path, 'r', encoding='utf-8') as f:
            raw_results = json.load(f) # Assuming it's a single JSON file now
        
        # Clean up the downloaded temporary file
        os.remove(temp_download_path)
        logger.info(f"Cleaned up temporary downloaded file: {temp_download_path}")

    except Exception as e:
        logger.error(f"Error fetching or loading latest batch results from R2: {e}", exc_info=True)
        raise Exception(f"Could not retrieve latest processing results: {str(e)}")

    # Extract actual results from the raw_results structure
    results = raw_results.get("results", [])
    metadata = raw_results.get("metadata", {})

    if not results:
        raise ValueError("No results found in the latest batch data.")

    # 2. Process results into the view_data structure
    grouped_results = {}
    total_items = 0
    needs_attention_items = 0
    auto_approved_items = 0
    
    # Use a set to track unique SNOMED FSNs for group counting
    unique_snomed_fsns = set()

    for item in results:
        total_items += 1
        
        # Ensure item has a unique_input_id for tracking decisions
        if "unique_input_id" not in item["input"] or not item["input"]["unique_input_id"]:
            # Generate a unique ID if missing (e.g., for older batch results)
            item["input"]["unique_input_id"] = str(uuid.uuid4())

        
        # Determine if the item needs attention
        needs_attention = False
        suspicion_flag = None

        if item["status"] == "error":
            needs_attention = True
            suspicion_flag = "processing_error"
        elif item["output"]["ambiguous"]:
            needs_attention = True
            suspicion_flag = "ambiguous_mapping"
        elif item["output"]["components"]["confidence"] < 0.8: # Example threshold
            needs_attention = True
            suspicion_flag = "low_confidence"
        
        # Check for singleton groups (only if not already flagged for attention)
        # This check is better done after initial grouping to know group size
        
        # Prepare the item for the view
        view_item = {
            "unique_input_id": item["input"]["unique_input_id"],
            "input_exam": item["input"].get("exam_name"),
            "exam_code": item["input"].get("exam_code"),
            "data_source": item["input"].get("data_source"),
            "clean_name": item["output"].get("clean_name"),
            "snomed_fsn": item["output"]["snomed"].get("fsn"),
            "snomed_id": item["output"]["snomed"].get("id"),
            "confidence": item["output"]["components"].get("confidence"),
            "ambiguous": item["output"].get("ambiguous", False),
            "error": item.get("error"), # Processing error from backend
            "needs_attention": needs_attention,
            "suspicion_flag": suspicion_flag,
            "all_candidates": item["output"].get("all_candidates", [])
        }

        # Group by SNOMED FSN or a special category for errors/unmatched
        group_key = view_item["snomed_id"] or view_item["clean_name"] or "UNMATCHED"
        if view_item["error"]:
            group_key = "ERROR"
        elif not view_item["snomed_id"] and not view_item["clean_name"]:
            group_key = "UNMATCHED"

        if group_key not in grouped_results:
            grouped_results[group_key] = []
        grouped_results[group_key].append(view_item)
        
        if needs_attention:
            needs_attention_items += 1
        else:
            auto_approved_items += 1

    # Post-processing for singleton groups and final attention count
    final_grouped_results = {}
    singleton_groups = 0
    for group_key, items in grouped_results.items():
        if group_key not in ["ERROR", "UNMATCHED"] and len(items) == 1:
            items[0]["needs_attention"] = True
            items[0]["suspicion_flag"] = "singleton_mapping"
            needs_attention_items += 1 # Increment attention count for singletons
            auto_approved_items -= 1 # Decrement auto-approved for singletons
            singleton_groups += 1
        
        # Re-evaluate needs_attention for the group header
        group_needs_attention = any(item["needs_attention"] for item in items)
        final_grouped_results[group_key] = items
        if group_needs_attention:
            # Ensure the group is marked for attention if any item within it is
            pass # Already handled by the hasAttention logic in frontend

        # Count unique SNOMED FSNs for total_groups
        if group_key not in ["ERROR", "UNMATCHED"] and items[0].get("snomed_fsn"):
            unique_snomed_fsns.add(items[0]["snomed_fsn"])

    # Calculate auto-approval rate
    approval_rate = auto_approved_items / total_items if total_items > 0 else 0

    summary = {
        "total_items": total_items,
        "total_groups": len(final_grouped_results), # Count of unique group_keys
        "needs_attention_items": needs_attention_items,
        "singleton_groups": singleton_groups,
        "auto_approved_items": auto_approved_items,
        "approval_rate": approval_rate,
        "generated_at": datetime.now().isoformat(),
        "source_batch_metadata": metadata
    }

    view_data_content = {
        "_metadata": {
            "summary": summary
        },
        "grouped_results": final_grouped_results
    }

    # 3. Save to a temporary file
    temp_dir = os.environ.get('RENDER_DISK_PATH', '/tmp') # Use /tmp as fallback
    os.makedirs(temp_dir, exist_ok=True)
    view_data_filename = f"view_data_{uuid.uuid4().hex}.json"
    view_data_filepath = os.path.join(temp_dir, view_data_filename)

    with open(view_data_filepath, 'w', encoding='utf-8') as f:
        json.dump(view_data_content, f, indent=2)
    logger.info(f"Generated view_data.json at: {view_data_filepath}")

    return view_data_filepath

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        # Example usage: This would typically be called by the Flask app
        generated_path = generate_view_data()
        print(f"View data generated successfully at: {generated_path}")
    except Exception as e:
        print(f"Failed to generate view data: {e}")
