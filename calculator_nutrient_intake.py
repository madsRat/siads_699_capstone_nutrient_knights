import pandas as pd
import requests
import json


def create_nutrient_table(llm_output_json):
    # find food list from intake json file

    # Load JSON data from file
    file_path = llm_output_json  # "Intake.txt"  # Update with the correct path
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Extract food descriptions
    food_items = []
    for meal in data["patient"]["diet_recall"]:
        for food in meal["food"]:
            food_items.append(food["description"])

    # Print the extracted food items
    print("Food Items:")
    print("\n".join(food_items))

    # find nutrition fact for each food, but exclude water
    # Dictionary to collect nutrient data
    nutrient_data = {}

    # API setup
    API_KEY = "A2cUE0WUknfVIuJGdkebUCcKjddw1RD0bpAny1SC"
    search_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    headers = {"Content-Type": "application/json"}

    # Iterate over food items
    for food in food_items:
        if food.lower() == 'water':
            continue

        payload = {
            "query": food,
            "requireAllWords": True,
        }

        try:
            response = requests.post(f"{search_url}?api_key={API_KEY}", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            foods = data.get("foods", [])
            if not foods:
                continue

            first_fdc_id = foods[0]["fdcId"]
            detail_url = f"https://api.nal.usda.gov/fdc/v1/food/{first_fdc_id}?api_key={API_KEY}"
            response = requests.get(detail_url)
            response.raise_for_status()

            food_data = response.json()
            food_name = food_data.get("description", food)

            for nutrient in food_data.get("foodNutrients", []):
                name = nutrient["nutrient"]["name"]
                amount = nutrient.get("amount")
                unit = nutrient["nutrient"]["unitName"]
                label = f"{amount} {unit}" if amount is not None else "N/A"

                if name not in nutrient_data:
                    nutrient_data[name] = {}
                nutrient_data[name][food] = label

        except Exception as e:
            print(f"Error processing {food}: {e}")
            continue
    # print(nutrient_data)
    # Create DataFrame
    df = pd.DataFrame(nutrient_data).T
    df.index.name = "Nutrition"
    df.to_csv("nutrition_table.csv")
    df
    return None


create_nutrient_table("Intake.txt")
print("Complete")
