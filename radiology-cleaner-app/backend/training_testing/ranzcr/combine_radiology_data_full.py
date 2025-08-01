import json
import os

def combine_radiology_data_full(ranzcr_filepath: str, nhs_filepath: str, output_filepath: str):
    """
    Combines data from an NHS JSON file with a RANZCR FHIR ValueSet.

    This script processes all records from the NHS file. If a matching SNOMED CT ID
    is found in the RANZCR ValueSet, it adds the RANZCR display name to the record.
    If no match is found, it adds an empty 'ranzcr_name' field.

    Args:
        ranzcr_filepath (str): The file path for the RANZCR FHIR ValueSet JSON.
        nhs_filepath (str): The file path for the NHS procedures JSON.
        output_filepath (str): The file path for the combined JSON output.
    """
    print("Starting the data combination process...")

    # --- Step 1: Load the JSON files ---
    try:
        with open(ranzcr_filepath, 'r', encoding='utf-8') as f:
            ranzcr_data = json.load(f)
        print(f"Successfully loaded RANZCR file: {ranzcr_filepath}")

        with open(nhs_filepath, 'r', encoding='utf-8') as f:
            nhs_data = json.load(f)
        print(f"Successfully loaded NHS file: {nhs_filepath}")

    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse a JSON file. {e}")
        return

    # --- Step 2: Prepare RANZCR data for efficient lookup ---
    ranzcr_lookup = {}
    try:
        for item in ranzcr_data['expansion']['contains']:
            snomed_id = item.get('code')
            ranzcr_name = item.get('display')
            if snomed_id and ranzcr_name:
                ranzcr_lookup[snomed_id] = ranzcr_name
    except KeyError as e:
        print(f"Error: The RANZCR JSON file is missing an expected key: {e}. "
              "Please ensure it is a valid FHIR ValueSet with an expansion.")
        return
    
    print(f"Created a lookup map with {len(ranzcr_lookup)} entries from the RANZCR set.")

    # --- Step 3 & 4: Iterate through all NHS data and enrich it ---
    combined_records = []
    match_count = 0
    for nhs_record in nhs_data:
        snomed_id = str(nhs_record.get('snomed_concept_id'))
        
        # Create a copy to add the new field
        new_record = nhs_record.copy()
        
        # Use .get() to find a match. If found, use the RANZCR name.
        # If not found, use an empty string as the default value.
        ranzcr_name = ranzcr_lookup.get(snomed_id, "")
        new_record['ranzcr_name'] = ranzcr_name
        
        if ranzcr_name: # If a name was found (i.e., not an empty string)
            match_count += 1
            
        combined_records.append(new_record)

    print(f"Processed {len(combined_records)} NHS records.")
    print(f"Found and added {match_count} matching RANZCR names.")

    # --- Step 5: Write the output JSON file ---
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            # Use indent=2 for pretty-printing the JSON
            json.dump(combined_records, f, indent=2, ensure_ascii=False)
        print(f"Successfully created the combined file: {output_filepath}")
    except IOError as e:
        print(f"Error: Could not write to the output file. {e}")


if __name__ == '__main__':
    # Define file paths relative to the script's location
    # Assumes the script and data files are in the same directory.
    current_directory = os.path.dirname(os.path.abspath(__file__))
    
    RANZCR_FILE = os.path.join(current_directory, 'RANZCR-Radiology-Requesting-reference-set-20250731-expansion.json')
    NHS_FILE = os.path.join(current_directory, 'NHS.json')
    OUTPUT_FILE = os.path.join(current_directory, 'nhs_with_ranzcr_procedures.json')

    # Run the main function
    combine_radiology_data_full(RANZCR_FILE, NHS_FILE, OUTPUT_FILE)