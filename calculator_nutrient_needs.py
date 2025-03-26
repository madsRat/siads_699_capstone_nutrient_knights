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

def calculate_patient_needs():

    # feed in fake data
    sex = 'male'
    age = '30 years'  # years
    weight = '160 lbs'  # lbs
    height = '72 inches'  # inches
    activity_level = 'active'

    print(age.split())
    print(len(age.split()))
    print(age.split()[0])
    print(age.split()[1])

    anthropometrics = [sex, age, weight, height, activity_level]
    anthro_amount_units = []

    for metric in anthropometrics:
        print('metric:', metric)
        val, unit = parse_amount_unit(metric)
        anthro_amount_units.append([val, unit])

    print(anthro_amount_units)
    df = pd.DataFrame(anthro_amount_units, columns=['value', 'unit'])
    print(df)

    # TODO Handle unit conversions for weight and height
    # TODO lower case sex, activity level
    # # Conversion factors to grams or milliliters (approximate values)
    # CONVERSIONS = {
    #     "cup": (240, "ml"),  # ml
    #     "oz": (29.57, "ml"),  # ml
    #     "ml": (1, "ml"),  # ml
    #     "g": (1, "g"),  # g
    #     "medium": (150, "g")  # g
    # }
    #
    # def convert_unit(amount_str):
    #     parts = amount_str.strip().split()
    #     if len(parts) == 2:
    #         value_str, unit = parts
    #         parsed_value_str = parse_amount(value_str)
    #         value = convert_to_float(parsed_value_str)
    #         if value is not None and unit in CONVERSIONS:
    #             factor, target_unit = CONVERSIONS[unit]
    #             return value * factor, target_unit, value
    #     elif len(parts) == 1 and parts[0] in CONVERSIONS:
    #         factor, target_unit = CONVERSIONS[parts[0]]
    #         return factor, target_unit, 1
    #     return None, None, None
    #
    # converted_value, target_unit, numeric_value = convert_unit(amount_str)








    # print('sex', sex)
    # print('age:', age)
    # print('weight:', weight)
    # print('height:', height)
    # print('activity_level:', activity_level)
    # print('\n')
    #
    # # import DRI Tables
    # if sex == 'male':
    #     df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
    # if sex == 'female':
    #     df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')
    #
    # print('Loaded', sex, 'dataset.')
    # print(df)
    #
    # # Compute Basal Metabolic Rate


def basal_metabolic_rate():
    # Compute Basal Metabolic Rate
    activity_levels = {
        'inactive': 1.4,
        'low active': 1.6,
        'active': 1.75,
        'very active': 2.0,
    }

calculate_patient_needs()
