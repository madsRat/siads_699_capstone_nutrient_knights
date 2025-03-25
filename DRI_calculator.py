import pandas as pd

def calculate_patient_needs():
    # feed in fake data
    age = '30 years'  # years
    weight = '160 lbs'  # lbs
    height = '72 inches'  # inches
    sex = 'male'
    activity_level = 'active'

    print('sex', sex)
    print('age:', age)
    print('weight:', weight)
    print('height:', height)
    print('activity_level:', activity_level)
    print('\n')

    # import DRI Tables
    if sex == 'male':
        df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='male')
    if sex == 'female':
        df = pd.read_excel('DRI_TABLES.xlsx', sheet_name='female')

    print('Loaded', sex, 'dataset.')
    print(df)

    # Compute Basal Metabolic Rate

    return None

def basal_metabolic_rate():
    # Compute Basal Metabolic Rate
    activity_levels = {
        'inactive': 1.4,
        'low active': 1.6,
        'active': 1.75,
        'very active': 2.0,
    }

calculate_patient_needs()