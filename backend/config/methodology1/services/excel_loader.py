import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXCEL_FILE = BASE_DIR / 'methodology1' / 'excel_data' / 'class3_4.xlsx'

def load_sheet(sheet_name):

    return pd.read_excel(
        EXCEL_FILE,
        sheet_name=sheet_name,
        header=1
    )

def load_pay_scale_table():
    return load_sheet('PayScale')

def load_special_da_table():
    return load_sheet('SpecialDA')

def load_da_1992_table():
    return load_sheet('DA_1992')

def load_special_allowance_table():
    return load_sheet('SpecialAllowance')

def load_fixed_da_table():
    return load_sheet('Fixed_DA')

def load_Matrix_2017_table():
    return pd.read_excel(
        EXCEL_FILE,
        sheet_name='Matrix2017',
        header=None,
        skiprows=1
    )

def load_Matrix_2022_table():
    return pd.read_excel(
        EXCEL_FILE,
        sheet_name='Matrix2022',
        header=None,
        skiprows=1
    )