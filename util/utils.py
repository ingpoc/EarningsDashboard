import base64
from functools import lru_cache
import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']
holdings_collection = db['holdings']

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

@lru_cache(maxsize=32)
def fetch_latest_quarter_data():
    stocks = list(collection.find({}, {"company_name": 1, "symbol": 1, "financial_metrics": {"$slice": -1}, "_id": 0}))
    
    # Fetch portfolio stocks
    portfolio_stocks = set(holdings_collection.distinct('Instrument'))
    
    # Read the SVG file
    with open('assets/portfolio_indicator.svg', 'r') as f:
        svg_content = f.read()
    
    # Encode the SVG content
    encoded_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    
    stock_data = [{
        "company_name": stock['company_name'],
        "symbol": stock['symbol'],
        "company_name_with_indicator": f'<div style="position: relative; padding-left: 30px;"><img src="data:image/svg+xml;base64,{encoded_svg}" width="24" height="24" style="position: absolute; left: 0; top: 50%; transform: translateY(-50%);"> {stock["company_name"]}</div>' if stock['symbol'] in portfolio_stocks else f'<div style="padding-left: 30px;">{stock["company_name"]}</div>',"result_date": pd.to_datetime(latest_metric.get("result_date", "N/A")),
        "net_profit_growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0%")),
        "cmp": parse_numeric_value(latest_metric.get("cmp", "0").split()[0]),
        "quarter": latest_metric.get("quarter", "N/A"),
        "ttm_pe": parse_numeric_value(latest_metric.get("ttm_pe", "N/A")),
        "net_profit": parse_numeric_value(latest_metric.get("net_profit", "0")),
        "estimates": latest_metric.get("estimates", "N/A"),
        "strengths": extract_numeric(latest_metric.get("strengths", "0")),
        "weaknesses": extract_numeric(latest_metric.get("weaknesses", "0"))
    } for stock in stocks for latest_metric in stock['financial_metrics']]
    
    df = pd.DataFrame(stock_data)
    df = df.sort_values(by="result_date", ascending=False)
    return df    

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