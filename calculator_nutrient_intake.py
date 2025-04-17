import pandas as pd
import numpy as np
import requests
import json
from pathlib import Path
from code_profiler import timeit

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QThread, QRunnable
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

@timeit
def create_nutrient_table(self):
    global nutrient_data
    # find food list from intake json file

    import json
    with open('results/llm_output_data.json', 'r') as file:
        data = json.load(file)

    # Extract food descriptions
    food_items = []
    for meal in data["diet_recall"]:
        for food in meal["items"]:
            food_items.append(food['food_description'])

    # try different search method, "Foundation" provide best nutrition details, 'Survey (FNDDS)', 'SR Legacy'
    payloads = [{"requireAllWords": True, "dataType": ["Foundation"]},  # excatly match
                {"requireAllWords": False, "dataType": ["Foundation"]},  # try no excatly match
                {"requireAllWords": True, "dataType": ["SR Legacy"]},  # check other type
                {"requireAllWords": True, "dataType": ["Survey (FNDDS)"]},  # check other type
                {"requireAllWords": True, "dataType": ["Branded"]},  # try "Branded"
                {"requireAllWords": False, "dataType": ["Branded"]},
                # last chance to try "Branded" without requireAllWords
                ]

    # API setup
    API_KEY = "A2cUE0WUknfVIuJGdkebUCcKjddw1RD0bpAny1SC"
    search_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    headers = {"Content-Type": "application/json"}

    # find nutrition fact for each food, but exclude water
    # Dictionary to collect nutrient data
    nutrient_data = {}

    # Iterate over food items
    for food in food_items:
        if food.lower() == 'water':
            continue

        # payload = {
        #     "query": food,
        #     "requireAllWords": True,
        # }

        # extract_nutrition(search_url, API_KEY, headers, payload, food)
        worker = Worker_extract_nutrition(search_url, API_KEY, headers, payloads, food)
        self.threadpool_extract_nutrients.start(worker)

    self.threadpool_extract_nutrients.waitForDone()

    # Create DataFrame
    df = pd.DataFrame(nutrient_data).T

    # check if a query has no result, we need create zero column for it to avoid errors afterwords
    missed_food = list(set(food_items) - set(df.columns) - set({'Water'}))
    if missed_food:
        print("missed those foods: ", missed_food)
        df[missed_food] = 0

    df.index.name = "Nutrition"

    # export table to results directory
    filepath = Path(r"results/nutrition_table.csv")
    df.to_csv(filepath)
    return None

class Worker_extract_nutrition(QRunnable):
    def __init__(self, search_url, API_KEY, headers, payloads, query):
        super().__init__()
        self.search_url = search_url
        self.API_KEY = API_KEY
        self.headers = headers
        self.payloads = payloads
        self.food = query
    @pyqtSlot()
    def run(self):
        extract_nutrition(self.search_url, self.API_KEY, self.headers, self.payloads, self.food)


def extract_nutrition(search_url, API_KEY, headers, payloads, query):
    global nutrient_data

    def similarity_score(string1, string2):
        # compare how similar of two strings:
        # similarity_score("apple", "Apples") => 0.91;  similarity_score("single malt", "malt") => 0.53
        import difflib
        similarity = difflib.SequenceMatcher(None, string1.lower(), string2.lower()).ratio()
        return round(similarity, 2)

    try:
        print("\n ====== query: ", query, "=========")
        similarity = 0.0
        for payload in payloads:
            # food = []
            if similarity > 0.49:
                break
            payload['query'] = query
            response = requests.post(f"{search_url}?api_key={API_KEY}", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            foods = data.get("foods", [])
            # print(foods)
            if len(foods) != 0:
                loops1 = 0
                for food in foods:

                    first_word = food['description'].split(',')[0].lower()
                    similarity = similarity_score(query, first_word)
                    if similarity > 0.49 or loops1 > 4:
                        print("query: ", query, "||food ID: ", food['fdcId'], "||similarity: ", similarity,
                              "||data type: ", food['dataType'], "||food: ", food['description'])

                        # print(food["foodNutrients"])
                        # get nutrition data
                        for nutrient in food["foodNutrients"]:
                            # name = nutrient["nutrient"]["nam]
                            name = nutrient["nutrientName"]
                            amount = nutrient["value"]
                            unit = nutrient["unitName"].lower()
                            label = f"{amount} {unit}" if amount is not None else "N/A"

                            if name not in nutrient_data:
                                nutrient_data[name] = {}
                            # nutrient_data[name][food] = label
                            nutrient_data[name][query] = label

                        break
                    else:
                        print("xxx no good match(", similarity, ") ", query, ":", food['description'])
                        loops1 += 1
                        print("loops: ", loops1)
            else:
                print("----- No found by", payload)

    except Exception as e:
        print(f"Error processing {query}: {e}")

@timeit
def separate_units_from_table(nutrition_table):
    # seperate unit and amount for nutrition_table

    import pandas as pd
    import re

    # Load the CSV file
    df = pd.read_csv(nutrition_table)

    # Function to extract numeric value and unit
    def extract_value_and_unit(cell):
        if pd.isna(cell):
            return pd.NA, pd.NA
        match = re.match(r"([\d\.]+)\s*(\w+)", str(cell))
        if match:
            return float(match.group(1)), match.group(2).lower()
        return pd.NA, pd.NA

    values_df = df.copy()
    units_df = pd.DataFrame(index=df.index, columns=df.columns)

    for col in df.columns[1:]:
        extracted = df[col].apply(extract_value_and_unit)
        values_df[col] = extracted.apply(lambda x: x[0])
        units_df[col] = extracted.apply(lambda x: x[1])

    # Define conversion factors
    kj_to_kcal = 0.239005736
    iu_to_ug = 0.6  # 1 IU = 0.6 mcg of beta-carotene (from food)

    # Force convert "kj" to "kcal" and "iu" to "ug" regardless of other units
    for col in df.columns[1:]:
        for i in values_df.index:
            unit = units_df.at[i, col]
            value = values_df.at[i, col]
            if pd.notna(unit) and pd.notna(value):
                if unit == "kj":
                    values_df.at[i, col] = value * kj_to_kcal
                    units_df.at[i, col] = "kcal"
                elif unit == "iu":
                    values_df.at[i, col] = value * iu_to_ug
                    units_df.at[i, col] = "ug"

    # Determine the unit for each row
    unit_column = []
    for i in units_df.index:
        row_units = units_df.iloc[i, 1:].dropna().unique()
        unit_column.append(row_units[0] if len(row_units) == 1 else pd.NA)

    # Append Unit column to final DataFrame
    values_df["UNIT"] = unit_column
    values_df.to_csv("results/food_nutrition_table.csv")

@timeit
def extract_intake_amounts():
    # load food intake json file again to get food intake, convert unit to ml or g

    import json
    import pandas as pd

    # Conversion factors to grams or milliliters (approximate values)
    CONVERSIONS = {
        # Volume-based
        "cup": (240, "ml"),
        "oz": (29.57, "ml"),
        "ml": (1, "ml"),
        "tsp": (5, "ml"),
        "tbsp": (15, "ml"),

        # Weight-based
        "g": (1, "g"),
        "kg": (1000, "g"),
        "mg": (0.001, "g"),
        "lb": (453.6, "g"),
        # "oz (weight)": (28.35, "g"),

        # Approximate weights for subjective portion sizes
        "medium": (150, "g"),
        "small": (100, "g"),
        "large": (200, "g"),

        # Units often used for pre-packaged or common snack items
        "bar": (40, "g"),
        "can": (355, "ml"),
        "bag": (50, "g"),
        "bottle": (500, "ml"),
        "pouch": (100, "g"),
        "slice": (100, "g"),  # assume most of case we use "slice" for cake or pizza

        # "slice (bread)": (30, "g"),         # 1 slice of sandwich bread
        # "slice (cheese)": (20, "g"),        # 1 slice of processed cheese
        # "slice (ham)": (25, "g"),           # 1 slice of deli ham
        # "slice (turkey)": (25, "g"),        # 1 slice of deli turkey
        # "slice (tomato)": (20, "g"),        # 1 medium-thick tomato slice
        # "slice (apple)": (15, "g"),         # 1 apple slice
        # "slice (cake)": (80, "g"),          # 1 standard slice of cake
        # "slice (pizza)": (125, "g")         # 1 average slice of pizza

        # Liquid alcohol serving estimate
        "glass": (150, "ml"),
        "ml": (1, "ml"),
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

@timeit
def tally_nutrients(food_summary_table, food_nutrition):
    # Sum nutrition

    import pandas as pd

    # Load the data
    food_summary = pd.read_csv(food_summary_table)
    food_nutrition_table = pd.read_csv(food_nutrition)
    food_nutrition_table = food_nutrition_table.fillna(0)

    # get water amount first
    try:
        water_amount = food_summary.loc[food_summary["food"] == "Water", "amount_in_ml_or_g"].values[0]
    except:
        water_amount = 0

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
    # add water back to nutrition list, water_amount is g, covert to liter
    df_nutrition_summary.loc['Water', 'Amount'] = (df_nutrition_summary.loc['Water', 'Amount'] + water_amount) / 1000
    df_nutrition_summary.loc["Water", 'UNIT'] = "liters"

    # export table to results directory
    filepath = Path(r"results/nutrition_total_intake.csv")
    df_nutrition_summary.to_csv(filepath)

@timeit
def create_intake_vs_needs_table(nutrition_total_intake, nutrition_total_needs, ordered_mapped_nutrients):
    # Load the uploaded CSV files
    intake_df = pd.read_csv(nutrition_total_intake)
    needs_df = nutrition_total_needs # input is dataframe from DRI calculator

    # Define mapping from intake_nutrition to need_nutrition
    intake_to_need_mapping = {
        'Iron, Fe': 'Iron', 'Magnesium, Mg': 'Magnesium', 'Phosphorus, P': 'Phosphorus',
        'Potassium, K': 'Potassium', 'Sodium, Na': 'Sodium', 'Zinc, Zn': 'Zinc',
        'Nitrogen': None, 'Copper, Cu': 'Copper', 'Total lipid (fat)': 'Fat',
        'Thiamin': 'Thiamin', 'Manganese, Mn': 'Manganese', 'Niacin': 'Niacin',
        'Ash': None, 'Starch': None, 'Vitamin B-6': 'Vitamin B6', 'Fiber, total dietary': 'Total Fiber',
        'Biotin': 'Biotin', 'Water': 'Total Water', 'Calcium, Ca': 'Calcium',
        'Protein': 'Protein', 'Carbohydrate, by difference': 'Carbohydrate',
        'Energy (Atwater General Factors)': 'Calories', 'Energy (Atwater Specific Factors)': None,
        'Citric acid': None, 'Vitamin C, total ascorbic acid': 'Vitamin C',
        'Malic acid': None, 'Oxalic acid': None, 'Quinic acid': None, 'Folate, total': 'Folate',
        'Sucrose': None, 'Galactose': None, 'Glucose': None, 'Fructose': None,
        'Lactose': None, 'Maltose': None, 'Sugars, Total': None, 'Energy': 'Calories',
        'Cryptoxanthin, beta': None, 'Lycopene': None, 'Riboflavin': 'Riboflavin',
        'Vitamin K (Dihydrophylloquinone)': 'Vitamin K', 'Vitamin K (phylloquinone)': 'Vitamin K',
        'Vitamin A, RAE': 'Vitamin A',
        'Carotene, alpha': None, 'Tryptophan': None, 'Threonine': None, 'Methionine': None,
        'Phenylalanine': None, 'Tyrosine': None, 'Alanine': None, 'Glutamic acid': None,
        'Glycine': None, 'Proline': None, 'Lutein + zeaxanthin': None,
        'Pantothenic acid': 'Pantothenic Acid', 'Selenium, Se': 'Selenium',
        'Isoleucine': None, 'Leucine': None, 'Lysine': None, 'Cystine': None,
        'Valine': None, 'Arginine': None, 'Histidine': None, 'Aspartic acid': None,
        'Serine': None, 'Fiber, insoluble': None, 'Fiber, soluble': None,
        'Carbohydrate, by summation': None, 'Cholesterol': 'Dietary Cholesterol',
        'Fatty acids, total polyunsaturated': None, 'Fatty acids, total monounsaturated': None,
        'Fatty acids, total trans': 'Trans fatty acids', 'Fatty acids, total saturated': 'Saturated fatty acids',
        'Ergothioneine': None, 'Vitamin D4': 'Vitamin D', 'Vitamin D2 (ergocalciferol)': 'Vitamin D',
        'Vitamin D (D2 + D3)': 'Vitamin D', 'Vitamin D (D2 + D3), International Units': None,
        'Delta-5-avenasterol': None, 'Ergosterol': None, 'Delta-7-Stigmastenol': None,
        'Stigmasterol': None, 'Campesterol': None, 'Beta-sitosterol': None, 'Beta-glucan': None,
        'Ergosta-7-enol': None, 'Ergosta-7,22-dienol': None, 'Ergosta-5,7-dienol': None,
        'Beta-sitostanol': None, 'Glutathione': None, 'Molybdenum, Mo': 'Molybdenum',
        'Vitamin K (Menaquinone-4)': 'Vitamin K', 'Total Sugars': None,
        'Vitamin A, IU': 'Vitamin A', 'Vitamin B-12': 'Vitamin B12'
    }

    # Map intake nutrients to need equivalents
    intake_df["Mapped_Nutrition"] = intake_df["Nutrition"].map(intake_to_need_mapping)

    # Aggregate total intake and select first unit per Mapped_Nutrition
    aggregated_intake_with_unit = (
        intake_df.dropna(subset=["Mapped_Nutrition"])
        .groupby("Mapped_Nutrition")
        .agg({"Amount": "sum", "UNIT": "first"})
        .reset_index()
        .rename(columns={"Mapped_Nutrition": "Nutrition", "Amount": "Total Intake", "UNIT": "Intake_Unit"})
    )

    # Merge aggregated data into needs dataframe
    final_needs_df = pd.merge(needs_df, aggregated_intake_with_unit, how="left", on="Nutrition")

    final_needs_df['Intake_Unit'] = np.where(final_needs_df['Intake_Unit'].isnull(), final_needs_df['Need_Unit'],
                                        final_needs_df['Intake_Unit'])

    final_needs_df['Need_Amount'] = final_needs_df['Need_Amount'].fillna(0)
    final_needs_df["Deviation"] = final_needs_df["Need_Amount"] - final_needs_df["Total Intake"]
    final_needs_df.rename(columns={"Total Intake": "Intake_Amount"}, inplace=True)
    final_needs_df['Intake_Amount'] = final_needs_df['Intake_Amount'].round(2)
    final_needs_df['Deviation'] = final_needs_df['Deviation'].round(2)
    final_needs_df['Need_Amount'] = final_needs_df['Need_Amount'].round(2)

    # Save the final merged file
    final_output_path = "results/Nutrition_Intake_vs_Needs.csv"
    final_needs_df.to_csv(final_output_path, index=False)

@timeit
def calculate_nutrient_intake(self):

    # chain all functions above and create nutrient intake table
    create_nutrient_table(self)
    separate_units_from_table("results/nutrition_table.csv")
    extract_intake_amounts()
    tally_nutrients("results/food_summary.csv", "results/food_nutrition_table.csv")
    return None

@timeit
def compare_nutrient_intake_and_needs(patient_nutrient_needs):
    # get_patient_nutrient_needs(patient_nutrient_needs)
    # prepare final table
    create_intake_vs_needs_table("results/nutrition_total_intake.csv", patient_nutrient_needs, "results/Ordered_Mapped_Nutrients.csv")
