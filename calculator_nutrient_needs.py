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
        df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
    if patient_info['sex']== 'female':
        df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')

    print('Loaded', patient_info['sex'], 'dataset.')
    print(df)

    # Compute Basal Metabolic Rate
    bmr = basal_metabolic_rate(patient_info, df)
    print('Basal Metabolic Rate:', bmr)

patient_info = preprocess_anthropometrics()
calculate_patient_needs(patient_info)

