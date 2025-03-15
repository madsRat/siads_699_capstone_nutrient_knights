###References
# https://www.geeksforgeeks.org/convert-json-to-dictionary-in-python/
# ChatGPT, Gemini

import json
import os


def convert_to_dict(data):
    """Extracts only the 'amount' and 'description' fields from 'diet_recall' in the
    JSON data and returns a dictionary."""
    extracted_data = {}

    # Iterate through diet_recall and extract only necessary fields
    for entry in data.get("patient", {}).get("diet_recall", []):
        for food_item in entry.get("food", []):
            extracted_data.setdefault("food_items", []).append(
                {
                    "amount": food_item.get("amount"),
                    "description": food_item.get("description"),
                }
            )

    return extracted_data


### Code below is to test the function.  It uses a locally created JSON file.

# Construct the full path to the JSON file in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "TestJSON.json")

# Try opening the file
try:
    with open(file_path, encoding="utf-8") as json_file:
        data = json.load(json_file)
    print("File loaded successfully!")
except FileNotFoundError:
    print(
        f"Error: File '{file_path}' not found. Check if it exists in the same directory as this script."
    )
    exit(1)

# Process and print the extracted dictionary data
converted_dict = convert_to_dict(data)
print(type(converted_dict))
print(json.dumps(converted_dict, indent=2))  # Print the dictionary in a readable format
