import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html

# Utility function for fetching stock names
def fetch_stock_names(collection):
    stocks = collection.find({}, {"company_name": 1})
    return [stock['company_name'] for stock in stocks]

# Utility function for converting strings to numeric values
def parse_numeric_value(value, remove_chars='%'):
    if isinstance(value, str):
        for char in remove_chars:
            value = value.replace(char, '')
        return pd.to_numeric(value.replace(',', ''), errors='coerce')
    return value

# Function to parse all numeric values in a dictionary
def parse_all_numeric_values(data, keys, remove_chars='%'):
    for key in keys:
        data[key] = parse_numeric_value(data.get(key, "0"), remove_chars)
    return data

# Function to generate stock recommendation
def get_stock_recommendation(row):
    net_profit_growth = row['Net Profit Growth %']

    if net_profit_growth > 0:
        return "Hold"
    elif net_profit_growth < 0:
        return "Sell"
    else:
        return "Hold"
    
def get_recommendation(df):
    if df is None or df.empty:
        return "No Data Available"

    # Simple recommendation logic based on growth metrics
    latest = df.iloc[-1]

    revenue_growth = parse_numeric_value(latest['revenue_growth'], '%')
    net_profit_growth = parse_numeric_value(latest['net_profit_growth'], '%')

    # Handle cases where conversion fails (NaN values)
    if pd.isna(revenue_growth) or pd.isna(net_profit_growth):
        return "No Data Available"

    # Now use the cleaned numeric values for recommendation logic
    if revenue_growth > 10 and net_profit_growth > 10:
        return "Strong Buy"
    elif revenue_growth > 5 and net_profit_growth > 5:
        return "Buy"
    elif revenue_growth < 0 or net_profit_growth < 0:
        return "Sell"
    else:
        return "Hold"    
    