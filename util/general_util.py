
import base64
import pandas as pd
import numpy as np
import re
from datetime import datetime
from functools import lru_cache



def parse_numeric_value(value, remove_chars='%'):
    if not value or pd.isna(value) or value in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
        return np.nan
    
    if isinstance(value, (int, float)):
        return float(value)
        
    try:
        if isinstance(value, str):
            value = value.translate(str.maketrans('', '', remove_chars))
            value = value.replace(',', '').strip()
            return float(value) if value else np.nan
    except (ValueError, TypeError):
        return np.nan
    
    # Helper function to load SVG indicators
def load_svg_indicator(filename):
    try:
        with open(f'assets/{filename}', 'r') as f:
            svg_content = f.read()
        return f'data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}'
    except FileNotFoundError:
        print(f"Error: SVG file '{filename}' not found")
        return ''
    

# Function to parse all numeric values in a dictionary
def parse_all_numeric_values(data, keys, remove_chars='%'):
    for key in keys:
        data[key] = parse_numeric_value(data.get(key, "0"), remove_chars)
    return data


def extract_numeric(value):
    if pd.isna(value) or value == 'NA':
        return 0
    try:
        return int(''.join(filter(str.isdigit, str(value))))
    except ValueError:
        return 0
    


def process_estimates(estimate_str):
    if pd.isna(estimate_str) or estimate_str == 'N/A':
        return None
    
    try:
        if 'Missed' in estimate_str or 'Beat' in estimate_str:
            value = float(estimate_str.split(':')[-1].strip().rstrip('%'))
            return value
        else:
            return None
    except ValueError:
        return None