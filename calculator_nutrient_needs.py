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
    height = "5' 11" #'72 inches'  # inches
    activity_level = 'active'

    # unit conversions to metric for DRI calculations
    # target variables weight and height
    CONVERSIONS = {
        # cover all possible representations of pounds
        "lb": (2.20462, "kg"),  # kilograms
        "-lb": (2.20462, "kg"),  # kilograms
        "lbs": (2.20462, "kg"),  # kilograms
        "-lbs": (2.20462, "kg"),  # kilograms
        "pound": (2.20462, "kg"),  # kilograms
        "-pound": (2.20462, "kg"),  # kilograms
        "pounds": (2.20462, "kg"),  # kilograms
        "-pounds": (2.20462, "kg"),  # kilograms

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

    anthropometrics = [sex, age, weight, height, activity_level]
    anthro_amount_units = []

    # split units from values
    for metric in anthropometrics:
        print('metric:', metric)

        # check if 5' 11" notation is used and convert to cm
        if "'" in metric:
            height = metric.split("'")
            feet = int(height[0])
            inches = int(height[1])

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

        anthro_amount_units.append([val, unit])

    print(anthro_amount_units)
    df = pd.DataFrame(anthro_amount_units, columns=['value', 'unit'])
    print(df)















    # # print('sex', sex)
    # # print('age:', age)
    # # print('weight:', weight)
    # # print('height:', height)
    # # print('activity_level:', activity_level)
    # # print('\n')
    # #
    # # # import DRI Tables
    # # if sex == 'male':
    # #     df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
    # # if sex == 'female':
    # #     df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')
    # #
    # # print('Loaded', sex, 'dataset.')
    # # print(df)
    # #
    # # # Compute Basal Metabolic Rate


def basal_metabolic_rate():
    # Compute Basal Metabolic Rate
    activity_levels = {
        'inactive': 1.4,
        'low active': 1.6,
        'active': 1.75,
        'very active': 2.0,
    }

calculate_patient_needs()
