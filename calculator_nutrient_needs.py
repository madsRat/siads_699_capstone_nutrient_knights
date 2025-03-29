import pandas as pd
import re

def parse_amount_unit(value):
    splitted = value.split()
    if len(splitted) == 2:
        val = splitted[0]
        unit = splitted[1]
    elif len(splitted) == 1:
        val = splitted[0]
        unit = None
    else:
        val = None
        unit = None
        print('parse_amount_unit: value is None.')
    return val, unit

def preprocess_anthropometrics():

    # feed in fake data
    sex = 'Male'
    age = '30 years'  # years
    weight = '160 lbs'  # lbs
    height = "6'" #'72 inches' # inches
    activity_level = 'Active'

    # unit conversions to metric for DRI calculations
    # target variables weight and height
    CONVERSIONS = {
        # cover all possible representations of pounds
        "lb": (0.453592, "kg"),  # kilograms
        "-lb": (0.453592, "kg"),  # kilograms
        "lbs": (0.453592, "kg"),  # kilograms
        "-lbs": (0.453592, "kg"),  # kilograms
        "pound": (0.453592, "kg"),  # kilograms
        "-pound": (0.453592, "kg"),  # kilograms
        "pounds": (0.453592, "kg"),  # kilograms
        "-pounds": (0.453592, "kg"),  # kilograms

        "kg": (1, "kg"),  # kilograms
        "g": (0.001, "kg"),  # kilograms

        # cover all possible representations of inches
        "in": (2.54, "cm"),  # centimeters
        "inch": (2.54, "cm"),  # centimeters
        "inches": (2.54, "cm"),  # centimeters
        "-in": (2.54, "cm"),  # centimeters
        "-inch": (2.54, "cm"),  # centimeters
        "-inches": (2.54, "cm"),  # centimeters

        "cm": (1, "cm"),  # centimeters
        "-cm": (1, "cm"),  # centimeters
        "centimeter": (1, "cm"),  # centimeters
        "-centimeter": (1, "cm"),  # centimeters
        "centimeters": (1, "cm"),  # centimeters
        "-centimeters": (1, "cm"),  # centimeters

        "years": (1, "years"),  # years
        "y": (1, "years"),  # years
        "months": (12, "years"),  # years
    }

    # anthropometrics = [sex, age, weight, height, activity_level]
    # anthro_amount_units = []

    anthropometrics = {'sex': sex,
                       'age': age,
                       'weight': weight,
                       'height': height,
                       'activity_level': activity_level}

    # split units from values
    for key, metric in anthropometrics.items():

        # check if 5' 11" notation is used and convert to cm
        if "'" in metric:
            height = metric.split("'")
            feet = int(height[0])

            if len(height) > 2:
                inches = int(height[1])
            else:
                inches = 0

            val = 2.54 * (12 * feet + inches) # in centimeters
            unit = 'cm'
        else:
            # do normal/expected parsing
            val, unit = parse_amount_unit(metric)

        # convert units to metric for DRI calculations
        if unit in CONVERSIONS:
            factor, target_unit = CONVERSIONS[unit]
            val = round(float(val) * factor, 2)
            unit = target_unit

        alternative_names = {
            'inactive': 'inactive',
            'in-active': 'inactive',
            'not active': 'inactive',

            'low_active': 'low_active',
            'low active': 'low_active',
            'not very active': 'low_active',

            'active': 'active',

            'very_active': 'very_active',
            'very active': 'very_active',

            'male': 'male',
            'm': 'male',
            'female': 'female',
            'f': 'female',
        }

        # format sex and activity_level
        if key in ['activity_level', 'sex']:
            val = val.lower()
            val = alternative_names[val]

        anthropometrics[key] = val  # [val, unit]

    print(anthropometrics)
    return anthropometrics

def basal_metabolic_rate(patient_info, df):
    # Compute Basal Metabolic Rate (BMR)
    activity_levels = {
        'inactive': 1.4,
        'low_active': 1.6,
        'active': 1.75,
        'very_active': 2.0,
    }

    if patient_info['sex'] == 'male':
        s_constant = 5
    elif patient_info['sex'] == 'female':
        s_constant = -161
    else:
        s_constant = None
        print("Patient Sex undefined.")

    BMR = 10 * patient_info['weight'] + 6.25 * patient_info['height'] - 5 * patient_info['age'] + s_constant
    bmr_adjusted = BMR * activity_levels[patient_info['activity_level']]

    return round(bmr_adjusted, 2)

def calculate_patient_needs(patient_info):

    # import DRI Tables
    if patient_info['sex'] == 'male':
        dri_df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
    if patient_info['sex']== 'female':
        dri_df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')

    print('Loaded', patient_info['sex'], 'dataset.')
    print(dri_df)

    interval = list(dri_df['age']) + [150]
    print('interval', interval)
    # establish interval index for age ranges
    intervals = pd.IntervalIndex.from_breaks(interval, closed='left')
    print(intervals)

    # assign index
    dri_df = dri_df.set_index(intervals)
    print(dri_df.head())
    print(dri_df.loc[1.9999])
    # print(dri_df['protein_g_kg_day'])
    print('protein \n',dri_df.loc[patient_info['age']]['protein_g_kg_day'])

    # Compute Basal Metabolic Rate (BMR)
    bmr = basal_metabolic_rate(patient_info, dri_df)
    print('Basal Metabolic Rate:', bmr)

    age = patient_info['age']

    # recommended protein = patient weight (kg) * protein table (by age)
    protein = patient_info['weight'] * dri_df.loc[age]['protein_g_kg_day']

    # Table 3 Energy Provided by Macronutrients (kcal/g)
    energy_provided = {
        'carbohydrate': 4,
        'fat': 9,
        'protein': 4,
        'alcohol': 7,
    }

    # carbohydrates
    carb_percentage_low = 0.45
    carb_percentage_high = 0.65
    carb_low = bmr * carb_percentage_low / energy_provided['carbohydrate']
    carb_high = bmr * carb_percentage_high / energy_provided['carbohydrate']
    carbohydrate = str(round(carb_low)) + '-' + str(round(carb_high))
    print(carbohydrate)

    # fiber
    fiber = round(dri_df.loc[age]['fiber_g_kcal'] * bmr / 1000)
    print(fiber)

    # fat
    fat_low = bmr * dri_df.loc[age]['fat_lowEnd_energy_percent'] / energy_provided['fat'] / 100
    fat_high = bmr * dri_df.loc[age]['fat_highEnd_energy_percent'] / energy_provided['fat'] / 100
    fat = str(round(fat_low)) + '-' + str(round(fat_high))
    print(fat)

    # alpha lenolic acid
    fat_alphaLenoic_acid = bmr * dri_df.loc[age]['fat_alphaLenolic_acid_energy_percent'] / energy_provided['fat'] / 100
    print(fat_alphaLenoic_acid)

    # lenolic acid
    fat_lenolic_acid = bmr * dri_df.loc[age]['fat_lenolic_acid_energy_percent'] / energy_provided['fat'] / 100
    print('fat_lenolic_acid: ', fat_lenolic_acid)

    fat_cholesterol = 'As low as possible while consuming a nutritionally adequate diet'
    fat_saturated_fatty_acids = 'As low as possible while consuming a nutritionally adequate diet'
    fat_trans_fatty_acids = 'As low as possible while consuming a nutritionally adequate diet'

    total_water = dri_df.loc[age]['total_water_liters']

    # macronutrients_table
    macronutrient_names = ['Carbohydrate',
                           'Total Fiber',
                           'Protein',
                           'Fat',
                           'Saturated fatty acids',
                           'Trans fatty acids',
                           'alpha-linolenic acid',
                           'Linoleic acid',
                           'Cholesterol',
                           'Total Water']

    macronutrient_dri = [carbohydrate,
                            fiber,
                            protein,
                            fat,
                            fat_saturated_fatty_acids,
                            fat_trans_fatty_acids,
                            fat_alphaLenoic_acid,
                            fat_lenolic_acid,
                            fat_cholesterol,
                            total_water]

    macronutrient_intake = [0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0]

    macronutrients = {'nutrient': macronutrient_names,
                      'intake': macronutrient_intake,
                      'DRI': macronutrient_dri}

    df_macronutrients = pd.DataFrame(macronutrients)
    print(df_macronutrients)

    # TODO Create Essential Vitamin table
    vitamin_names = ['Vitamin A',
                     'Vitamin C',
                     'Vitamin D',
                     'Vitamin B6',
                     'Vitamin E',
                     'Vitamin K',
                     'Thiamin',
                     'Vitamin B12',
                     'Riboflavin',
                     'Folate',
                     'Niacin',
                     'Choline',
                     'Pantothenic Acid',
                     'Biotin']

    vitamin_dri = [dri_df.loc[age]['vitamin_a_mcg'],
                   dri_df.loc[age]['vitamin_c_mg'],
                   dri_df.loc[age]['vitamin_d_mcg'],
                   dri_df.loc[age]['vitamin_b6_mcg'],
                   dri_df.loc[age]['vitamin_e_mcg'],
                   dri_df.loc[age]['vitamin_k_mcg'],
                   dri_df.loc[age]['thiamin_mg'],
                   dri_df.loc[age]['vitamin_b12_mcg'],
                   dri_df.loc[age]['riboflavin_mg'],
                   dri_df.loc[age]['folate_mcg'],
                   dri_df.loc[age]['niacin_mg'],
                   dri_df.loc[age]['choline_mg'],
                   dri_df.loc[age]['pantothenic_acid_mg'],
                   dri_df.loc[age]['biotin_mg']
                   ]

    vitamin_intake =[0] * 14

    vitamins = {'nutrient': vitamin_names,
                      'intake': vitamin_intake,
                      'DRI': vitamin_dri}

    df_vitamins = pd.DataFrame(vitamins)
    print(df_vitamins)

    essential_minerals_names = [
        'Calcium',
        'Chloride',
        'Chromium',
        'Copper',
        'Fluoride',
        'Iodine',
        'Iron',
        'Magnesium',
        'Manganese',
        'Molybdenum',
        'Phosphorus',
        'Potassium',
        'Selenium',
        'Sodium',
        'Zinc'
    ]

    essential_mineral_dri = [
        dri_df.loc[age]['calcium_mg'],
        dri_df.loc[age]['chloride_g'],
        dri_df.loc[age]['chromium_mcg'],
        dri_df.loc[age]['copper_mcg'],
        dri_df.loc[age]['fluoride_mg'],
        dri_df.loc[age]['iodine_mcg'],
        dri_df.loc[age]['iron_mg'],
        dri_df.loc[age]['magnesium_mg'],
        dri_df.loc[age]['manganese_mg'],
        dri_df.loc[age]['molybdenum_mcg'],
        dri_df.loc[age]['phosphorus_mg'],
        dri_df.loc[age]['potassium_g'],
        dri_df.loc[age]['selenium_mcg'],
        dri_df.loc[age]['sodium_g'],
        dri_df.loc[age]['zinc_mg']
    ]

    essential_minerals_intake = [0] * len(essential_mineral_dri)
    essential_minerals = {
        'nutrient': essential_minerals_names,
        'intake': essential_minerals_intake,
        'DRI': essential_mineral_dri
    }

    df_essential_minerals = pd.DataFrame(essential_minerals)
    print(df_essential_minerals)

    return df_macronutrients, df_vitamins, df_essential_minerals


# patient_info = preprocess_anthropometrics()
# df_macronutrients, df_vitamins, df_essential_minerals = calculate_patient_needs(patient_info)

