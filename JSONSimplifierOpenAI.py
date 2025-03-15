###References
# https://community.openai.com/t/how-do-i-use-the-new-json-mode/475890
# ChatGPT, Gemini

import openai
import json
import os
from openai import OpenAI

# OpenAI API key setup
openai.api_key = os.getenv("OPENAI_API_KEY")


def ConvertToJSON(data):
    """Function to take in a JSON file and simplify it using OpenAI's GPT-4 model.
    The function strips all data except the 'amount' and 'food' fields from the 'diet_recall' entry in the JSON data.'
    """

    # Convert JSON data to string for OpenAI API
    data_string = json.dumps(data, indent=2)

    # OpenAI API call
    client = OpenAI()  # Create an OpenAI client instance
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI that extracts structured nutrient information from patient diet records.",
            },
            {
                "role": "user",
                # "content": f"Extract only the 'amount' and 'description' fields under 'diet_recall' from the json. Output it as a structured JSON array:\n\n{data_string}",
                "content": f"Extract only the food_items from the following JSON data, excluding time and place. Keep only 'amount' and 'food' fields. Output it as a structured JSON array:\n\n{data_string}",
                # "content": f"Extract only the food details from the following JSON data, excluding time and place. Keep only 'amount' and 'food' fields. Output it as python dictionary:\n\n{data_string}",
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
    )

    # Parse and print the extracted data
    try:
        extracted_data = json.loads(response.choices[0].message.content)
        print(json.dumps(extracted_data, indent=2))
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing response: {e}")
        print(response)

    return extracted_data


### Code below is to test the function.  It uses a locally created JSON file.

# Open TestJSON.json file and onstruct the full path to the file
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

converted_json = ConvertToJSON(data)
print(type(converted_json))
print(json.dumps(converted_json, indent=2))
