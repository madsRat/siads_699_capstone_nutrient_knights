import pandas as pd
import numpy as np
import requests
import json
from pathlib import Path

def create_nutrient_table():
    # find food list from intake json file

    import json
    with open('results/llm_output_data.json', 'r') as file:
        data = json.load(file)

    # Extract food descriptions
    food_items = []
    for meal in data["diet_recall"]:
        for food in meal["items"]:
            food_items.append(food['food_description'])

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

    # export table to results directory
    filepath = Path(r"results/nutrition_table.csv")
    df.to_csv(filepath)

def separate_units_from_table(nutrition_table):
    # seperate unit and amount for nutrition_table

    import pandas as pd
    import re

    # Load the CSV file
    df = pd.read_csv(nutrition_table, index_col=0)

    # Select the first food column to extract units from
    first_food_col = df.columns[0]

    # Initialize UNIT column
    unit_column = []

    # Process each row to extract unit and strip it from all columns
    for index, row in df.iterrows():
        first_val = row[first_food_col]
        if pd.isna(first_val) or not isinstance(first_val, str):
            unit_column.append(None)
            continue

        # Extract numeric value and unit using regex
        match = re.match(r"([-+]?\d*\.\d+|\d+)\s*(\D+)", first_val.strip())
        if match:
            unit = match.group(2).strip()
        else:
            unit = None
        unit_column.append(unit)

    # Add the UNIT column
    df["UNIT"] = unit_column

    # Remove units and convert to numeric values
    for col in df.columns[:-1]:  # Skip the UNIT column
        df[col] = df[col].astype(str).str.extract(r"([-+]?\d*\.\d+|\d+)")[0]
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # export table to results directory
    filepath = Path(r"results/food_nutrition_table.csv")
    df.to_csv(filepath)

def extract_intake_amounts():
    # load food intake json file again to get food intake, convert unit to ml or g

    import json
    import pandas as pd

    # Conversion factors to grams or milliliters (approximate values)
    CONVERSIONS = {
        "cup": (240, "ml"),  # ml
        "oz": (29.57, "ml"),  # ml
        "ml": (1, "ml"),  # ml
        "g": (1, "g"),  # g
        "medium": (150, "g")  # g
    }

    # Fractions to float
    FRACTIONS = {
        "¼": 0.25,
        "½": 0.5,
        "¾": 0.75
    }

    def parse_amount(amount):
        for frac, val in FRACTIONS.items():
            amount = amount.replace(frac, str(val))
        return amount

    def convert_to_float(amount):
        try:
            return eval(amount)
        except:
            return None

    def convert_unit(amount_str):
        parts = amount_str.strip().split()
        if len(parts) == 2:
            value_str, unit = parts
            parsed_value_str = parse_amount(value_str)
            value = convert_to_float(parsed_value_str)
            if value is not None and unit in CONVERSIONS:
                factor, target_unit = CONVERSIONS[unit]
                return value * factor, target_unit, value
        elif len(parts) == 1 and parts[0] in CONVERSIONS:
            factor, target_unit = CONVERSIONS[parts[0]]
            return factor, target_unit, 1
        return None, None, None

    import json
    with open('results/llm_output_data.json', 'r') as file:
        data = json.load(file)
        print('PATIENT DICTIONARY:\n', data)

    # Process and convert food items
    converted_foods = []
    for meal in data["diet_recall"]:
        for food in meal["items"]:
            amount_str = food["amount"]
            description = food["food_description"]
            converted_value, target_unit, numeric_value = convert_unit(amount_str)
            if converted_value is not None:
                rounded_value = int(converted_value) if converted_value.is_integer() else round(converted_value)  # , 2)
                converted_foods.append({
                    "food": description,
                    "amount": amount_str,
                    "amount_in_ml_or_g": rounded_value
                })
            else:
                converted_foods.append({
                    "food": description,
                    "amount": amount_str,
                    "amount_in_ml_or_g": "unknown"
                })

    # Create DataFrame
    df = pd.DataFrame(converted_foods)

    # Filter out unknowns
    df_clean = df[df["amount_in_ml_or_g"] != "unknown"]

    # Group and sum by food
    df_food_summary = df_clean.groupby("food", as_index=False)["amount_in_ml_or_g"].sum()

    # export table to results directory
    filepath = Path(r"results/food_summary.csv")
    df_food_summary.to_csv(filepath)

def tally_nutrients(food_summary_table, food_nutrition_table):
    # Sum nutrition

    import pandas as pd

    # Load the data
    food_summary = pd.read_csv(food_summary_table)
    food_nutrition_table = pd.read_csv(food_nutrition_table)

    # get water amount first
    water_amount = food_summary.loc[food_summary["food"] == "Water", "amount_in_ml_or_g"].values[0]

    # Drop the 'Unnamed: 0' column from food_summary
    food_summary = food_summary.drop(columns=["Unnamed: 0"])

    # Set 'Nutrition' column as index and drop 'UNIT' temporarily
    nutrition_data = food_nutrition_table.set_index("Nutrition").drop(columns=["UNIT"])

    # Create a dictionary of scaling factors: {food_name: amount / 100}
    scaling_factors = dict(zip(food_summary["food"], food_summary["amount_in_ml_or_g"] / 100))

    # Multiply each food column by its corresponding scaling factor (if it exists)
    adjusted_nutrition = nutrition_data.copy()
    for food in adjusted_nutrition.columns:
        # print('food: ', food)
        if food in scaling_factors:
            adjusted_nutrition[food] *= scaling_factors[food]
        else:
            adjusted_nutrition[food] = 0  # food not consumed that day

    # Sum across all food columns to get total nutrient intake
    df_nutrition_summary = adjusted_nutrition.sum(axis=1).to_frame(name="Amount")
    # Extract the UNIT column from the original food_nutrition_table
    unit_column = food_nutrition_table.set_index("Nutrition")["UNIT"]
    # Join the unit column with df_nutrition_summary
    df_nutrition_summary = df_nutrition_summary.join(unit_column)
    # add water back to nutrition list
    df_nutrition_summary.loc["Water"] = [water_amount / 1000, "liters"]

    # export table to results directory
    filepath = Path(r"results/nutrition_total_intake.csv")
    df_nutrition_summary.to_csv(filepath)

def create_mapped_nutrient_table():
    # Define the ordered Need_Nutrition list
    ordered_need_nutrition = [
        "Calories", "Carbohydrate", "Total Fiber", "Protein", "Fat",
        "Saturated fatty acids", "Trans fatty acids", "Î±-Linolenic Acid", "Linoleic Acid",
        "Dietary Cholesterol", "Total Water", "Vitamin A", "Vitamin C", "Vitamin D",
        "Vitamin B6", "Vitamin E", "Vitamin K", "Thiamin", "Vitamin B12", "Riboflavin",
        "Folate", "Niacin", "Choline", "Pantothenic Acid", "Biotin", "Carotenoids",
        "Calcium", "Chloride", "Chromium", "Copper", "Fluoride", "Iodine", "Iron",
        "Magnesium", "Manganese", "Molybdenum", "Phosphorus", "Potassium", "Selenium",
        "Sodium", "Zinc"
    ]

    # Define the combined mapping as a dictionary
    mapping_dict = {
        "Calories": "Energy",
        "Carbohydrate": "Carbohydrate, by difference",
        "Total Fiber": "Fiber, total dietary",
        "Protein": "Protein",
        "Fat": "Total lipid (fat)",
        "Saturated fatty acids": "Fatty acids, total saturated",
        "Trans fatty acids": "Fatty acids, total trans",
        "Î±-Linolenic Acid": "*Not directly available*",
        "Linoleic Acid": "*Not directly available*",
        "Dietary Cholesterol": "Cholesterol",
        "Total Water": "Water",
        "Vitamin A": "Vitamin A",
        "Vitamin C": "Vitamin C, total ascorbic acid",
        "Vitamin D": "Vitamin D (D2 + D3)",
        "Vitamin B6": "Vitamin B-6",
        "Vitamin E": "*Not available*",
        "Vitamin K": "*Not available*",
        "Thiamin": "Thiamin",
        "Vitamin B12": "Vitamin B-12",
        "Riboflavin": "Riboflavin",
        "Folate": "Folate, total",
        "Niacin": "Niacin",
        "Choline": "*Not available*",
        "Pantothenic Acid": "*Not available*",
        "Biotin": "*Not available*",
        "Carotenoids": "*Not available*",
        "Calcium": "Calcium, Ca",
        "Chloride": "*Not available*",
        "Chromium": "*Not available*",
        "Copper": "Copper, Cu",
        "Fluoride": "*Not available*",
        "Iodine": "*Not available*",
        "Iron": "Iron, Fe",
        "Magnesium": "Magnesium, Mg",
        "Manganese": "*Not available*",
        "Molybdenum": "*Not available*",
        "Phosphorus": "Phosphorus, P",
        "Potassium": "Potassium, K",
        "Selenium": "*Not available*",
        "Sodium": "Sodium, Na",
        "Zinc": "Zinc, Zn"
    }

    # Create ordered DataFrame
    ordered_df = pd.DataFrame([
        (nutrient, mapping_dict.get(nutrient, "*Not available*"))
        for nutrient in ordered_need_nutrition
    ], columns=["Need_Nutrition", "Intake_Nutrition"])

    # export table to results directory
    filepath = Path(r"results/Ordered_Mapped_Nutrients.csv")
    ordered_df.to_csv(filepath, index=False)

def create_intake_vs_needs_table(nutrition_total_intake, nutrition_total_needs, ordered_mapped_nutrients):
    # Load the uploaded CSV files
    intake_df = pd.read_csv(nutrition_total_intake)
    needs_df = nutrition_total_needs # input is dataframe from DRI calculator
    mapping_df = pd.read_csv(ordered_mapped_nutrients)

    # Create mapping dictionary
    name_mapping = dict(zip(mapping_df["Intake_Nutrition"], mapping_df["Need_Nutrition"]))

    # Map and prepare intake data
    intake_df["Nutrition"] = intake_df["Nutrition"].map(name_mapping)
    intake_df = intake_df.dropna(subset=["Nutrition"])  # Drop unmapped rows
    intake_df = intake_df.rename(columns={"UNIT": "Intake_Unit"})

    # Merge with needs data
    # merged_df = pd.merge(needs_df, intake_df, on="Nutrition", how="left")
    merged_df = pd.merge(needs_df, intake_df, on="Nutrition", how="left").drop(columns=["Unnamed: 0"], errors="ignore")

    # data cleaning
    merged_df['Amount'] = merged_df['Amount'].fillna(0) # replace nan with 0 intake
    # replace missing intake units with needs units.
    merged_df['Intake_Unit'] = np.where(merged_df['Intake_Unit'].isnull(), merged_df['Need_Unit'], merged_df['Intake_Unit'])

    merged_df["Deviation"] = merged_df["Amount"] - merged_df["Need_Amount"]
    # Round all numeric columns to 1 decimal point
    numeric_cols = merged_df.select_dtypes(include=["float64", "int64"]).columns
    merged_df[numeric_cols] = merged_df[numeric_cols].round(1)
    merged_df = merged_df.rename(columns={"Amount": "Intake_Amount"})

    # export table to results directory
    filepath = Path(r"results/Nutrition_Intake_vs_Needs.csv")
    merged_df.to_csv(filepath, index=False)

def calculate_nutrient_intake():
    # chain all functions above and create nutrient intake table
    create_nutrient_table()
    separate_units_from_table("results/nutrition_table.csv")
    extract_intake_amounts()
    tally_nutrients("results/food_summary.csv", "results/food_nutrition_table.csv")
    return None

# TODO use mapped nutrition tables to send (macronutrients, vitamins, essential minearls tables) to main gui
def compare_nutrient_intake_and_needs(patient_nutrient_needs):
    # get_patient_nutrient_needs(patient_nutrient_needs)
    # prepare final table
    create_mapped_nutrient_table()
    create_intake_vs_needs_table("results/nutrition_total_intake.csv", patient_nutrient_needs, "results/Ordered_Mapped_Nutrients.csv")

