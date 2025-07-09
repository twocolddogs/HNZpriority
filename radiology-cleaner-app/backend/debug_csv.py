import csv
import io

def debug_csv():
    csv_path = 'base_code_set.csv'
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    print("Raw content first 500 chars:")
    print(repr(content[:500]))
    print("\n" + "="*50 + "\n")
    
    # Fix the content
    content = content.replace('"SNOMED CT \nConcept-ID\n"', '"SNOMED CT Concept-ID"')
    content = content.replace('"Clean Name\n"', '"Clean Name"')
    
    lines = content.strip().split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Find data start
    data_start = 0
    for i, line in enumerate(lines):
        print(f"Line {i}: {repr(line[:100])}")
        if i < 10 and line.strip() and line[0].isdigit():
            data_start = i
            print(f"Found data start at line {i}")
            break
    
    if data_start > 0:
        header = lines[data_start - 1]
        print(f"Header: {repr(header)}")
        
        # Try parsing a few rows
        data_lines = lines[data_start:data_start+3]
        cleaned_csv = header + '\n' + '\n'.join(data_lines)
        
        print(f"Cleaned CSV sample:\n{repr(cleaned_csv)}")
        
        reader = csv.DictReader(io.StringIO(cleaned_csv))
        for i, row in enumerate(reader):
            print(f"Row {i}: {dict(row)}")
            if i >= 2:
                break

if __name__ == '__main__':
    debug_csv()