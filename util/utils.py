import base64
from functools import lru_cache
import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html
import numpy as np
from functools import lru_cache
import re
from datetime import datetime, timedelta
from util.database import DatabaseConnection





# Centralized MongoDB connection
def get_mongo_client():
    """Create a singleton MongoDB client."""
    if not hasattr(get_mongo_client, "_client"):
        get_mongo_client._client = MongoClient('mongodb://localhost:27017/')
    return get_mongo_client._client

# Fetch the database only once
def get_db():
    client = get_mongo_client()
    return client['stock_data']

# Reuse the same collections for data access
def get_collection(collection_name):
    db = get_db()
    return db[collection_name]


@lru_cache(maxsize=500)
def fetch_stock_names():
    try:
        collection = DatabaseConnection.get_collection('detailed_financials')
        return sorted([stock['company_name'] for stock in collection.find({}, {"company_name": 1})])
    except Exception as e:
        print(f"Error fetching stock names: {str(e)}")
        return []

# Utility function for converting strings to numeric values
def parse_numeric_value(value, remove_chars='%'):
    """
    Parses a numeric value from a string, handling specified characters.

    Parameters:
    - value: The value to parse (could be a string or a number).
    - remove_chars (str): Characters to remove from the string.

    Returns:
    - float: The numeric value parsed from the input, or np.nan if parsing fails.
    """
    if value is None or pd.isnull(value) or value in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
        return np.nan
    try:
        if isinstance(value, str):
            for char in remove_chars:
                value = value.replace(char, '')
            value = value.replace(',', '').strip()
            if value == '':
                return np.nan
            return float(value)
        else:
            return float(value)
    except (ValueError, TypeError):
        return np.nan

# Function to parse all numeric values in a dictionary
def parse_all_numeric_values(data, keys, remove_chars='%'):
    for key in keys:
        data[key] = parse_numeric_value(data.get(key, "0"), remove_chars)
    return data

# Function to generate stock recommendation



def fetch_latest_quarter_data():
    stocks = list(get_collection('detailed_financials').find({}, {"company_name": 1, "symbol": 1, "financial_metrics": {"$slice": -1}, "_id": 0}))

    # Fetch portfolio stocks
    portfolio_stocks = set(get_collection('holdings').distinct('Instrument'))

    # Read the SVG file for portfolio indicator
    with open('assets/portfolio_indicator.svg', 'r') as f:
        svg_content = f.read()

    # Encode the SVG content
    encoded_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')

    # Load the AI indicator
    ai_indicator = load_ai_indicator()

    stock_data = []
    for stock in stocks:
        latest_metric = stock['financial_metrics'][0]
        company_name = stock['company_name']
        symbol = stock.get('symbol', 'N/A')
        in_portfolio = symbol in portfolio_stocks
        indicator = f'<img src="data:image/svg+xml;base64,{encoded_svg}" width="24" height="24">' if in_portfolio else ''
        company_name_with_indicator = f'{indicator} {company_name}'

        # Fetch the latest AI analysis
        analysis_doc = get_collection('ai_analysis').find_one({'symbol': symbol}, sort=[('timestamp', -1)])
        if analysis_doc:
            analysis_text = analysis_doc['analysis'] 
            ai_recommendation = extract_recommendation(analysis_text)
            
        else:
            ai_recommendation = None

        # Create the AI indicator HTML
        ai_indicator_html = f'<img src="{ai_indicator}" width="24" height="24" style="cursor: pointer;" />'

        # Combine AI indicator and recommendation
        if ai_recommendation:
            ai_indicator_html += f' {ai_recommendation}'

        stock_data.append({
            "company_name": company_name,
            "symbol": symbol,
            "company_name_with_indicator": company_name_with_indicator,
            "ai_indicator": ai_indicator_html,
            "result_date": pd.to_datetime(latest_metric.get("result_date", "N/A")),
            "net_profit_growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0%")),
            "cmp": parse_numeric_value(latest_metric.get("cmp", "0").split()[0]),
            "quarter": latest_metric.get("quarter", "N/A"),
            "ttm_pe": parse_numeric_value(latest_metric.get("ttm_pe", "N/A")),
            "net_profit": parse_numeric_value(latest_metric.get("net_profit", "0")),
            "estimates": latest_metric.get("estimates", "N/A"),
            "strengths": extract_numeric(latest_metric.get("strengths", "0")),
            "weaknesses": extract_numeric(latest_metric.get("weaknesses", "0")),
            "pb_ratio": parse_numeric_value(latest_metric.get("pb_ratio", "N/A")),
            "sector_pe": parse_numeric_value(latest_metric.get("sector_pe", "N/A")),
            "ttm_eps": parse_numeric_value(latest_metric.get("ttm_eps", "N/A")),
            "dividend_yield": parse_numeric_value(latest_metric.get("dividend_yield", "N/A")),
            "book_value": parse_numeric_value(latest_metric.get("book_value", "N/A")),
            "face_value": parse_numeric_value(latest_metric.get("face_value", "N/A")),
            "piotroski_score": parse_numeric_value(latest_metric.get("piotroski_score", "0")),
            "technicals_trend": latest_metric.get("technicals_trend", "NA"),
            "revenue_growth": parse_numeric_value(latest_metric.get("revenue_growth", "0%")),
            "fundamental_insights": latest_metric.get("fundamental_insights", "N/A"),
            # Add the AI recommendation to the data
            "ai_recommendation": ai_recommendation if ai_recommendation else "N/A",
        })

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

def get_stock_symbol(company_name):
    stock = get_collection('detailed_financials').find_one({"company_name": company_name})
    if stock and 'symbol' in stock:
        return f"{stock['symbol']}.NS"
    return None

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

@lru_cache(maxsize=1000)
def fetch_latest_metrics(symbol):
    collection = DatabaseConnection.get_collection('detailed_financials')
    stock = collection.find_one({"symbol": symbol})
    
    if not stock or not stock.get('financial_metrics'):
        return {
            "net_profit_growth": "0",
            "strengths": "0",
            "weaknesses": "0",
            "technicals_trend": "NA",
            "fundamental_insights": "NA",
            "piotroski_score": "0",
            "market_cap": "NA",
            "face_value": "NA",
            "book_value": "NA",
            "dividend_yield": "NA",
            "ttm_pe": "NA",
            "revenue": "NA",
            "net_profit": "NA",
            "cmp": "NA",
            "report_type": "NA",
            "result_date": "NA",
            "gross_profit": "NA",
            "gross_profit_growth": "NA",
            "revenue_growth": "NA",
            "ttm_eps": "NA",
            "pb_ratio": "NA",
            "sector_pe": "NA",
            "estimates": "NA"
        }

    latest_metric = max(stock['financial_metrics'], key=lambda x: pd.to_datetime(x.get("result_date", "N/A")))

    return {
        "net_profit_growth": latest_metric.get("net_profit_growth", "0"),
        "strengths": latest_metric.get("strengths", "0"),
        "weaknesses": latest_metric.get("weaknesses", "0"),
        "technicals_trend": latest_metric.get("technicals_trend", "NA"),
        "fundamental_insights": latest_metric.get("fundamental_insights", "NA"),
        "piotroski_score": latest_metric.get("piotroski_score", "0"),
        "market_cap": latest_metric.get("market_cap", "NA"),
        "face_value": latest_metric.get("face_value", "NA"),
        "book_value": latest_metric.get("book_value", "NA"),
        "dividend_yield": latest_metric.get("dividend_yield", "NA"),
        "ttm_pe": latest_metric.get("ttm_pe", "NA"),
        "revenue": latest_metric.get("revenue", "NA"),
        "net_profit": latest_metric.get("net_profit", "NA"),
        "cmp": latest_metric.get("cmp", "NA"),
        "report_type": latest_metric.get("report_type", "NA"),
        "result_date": latest_metric.get("result_date", "NA"),
        "gross_profit": latest_metric.get("gross_profit", "NA"),
        "gross_profit_growth": latest_metric.get("gross_profit_growth", "NA"),
        "revenue_growth": latest_metric.get("revenue_growth", "NA"),
        "ttm_eps": latest_metric.get("ttm_eps", "NA"),
        "pb_ratio": latest_metric.get("pb_ratio", "NA"),
        "sector_pe": latest_metric.get("sector_pe", "NA"),
        "estimates": latest_metric.get("estimates", "NA")
    }

def load_ai_indicator():
    # Get the selected AI API from the settings
    settings_doc = get_collection('settings').find_one({'_id': 'ai_api_selection'})
    selected_api = settings_doc.get('selected_api', 'perplexity') if settings_doc else 'perplexity'

    # Determine the SVG file based on the selected API
    if selected_api == 'xai':
        svg_filename = 'xAI_indicator.svg'
    else:
        svg_filename = 'ai_indicator.svg'

    # Load the SVG content
    try:
        with open(f'assets/{svg_filename}', 'r') as f:
            svg_content = f.read()
        # Encode the SVG content
        encoded_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
        return f'data:image/svg+xml;base64,{encoded_svg}'
    except FileNotFoundError:
        print(f"Error: SVG file '{svg_filename}' not found in the 'assets' directory.")
        return ''


# Implement get_previous_analyses function
def get_previous_analyses(symbol):
    analyses = list(get_collection('ai_analysis').find({'symbol': symbol}).sort('timestamp', 1))
    return analyses


def extract_recommendation(analysis_text):
    """
    Extracts the recommendation from the AI analysis text.
    """
    # Attempt to extract the 'Recommendation:' or 'Stock Recommendation:' section
    recommendation_section = None
    match = re.search(r'(Recommendation|Stock Recommendation):\s*(.*?)(?:\n\n|$)', analysis_text, re.DOTALL | re.IGNORECASE)
    if match:
        recommendation_section = match.group(2).strip()
    else:
        recommendation_section = analysis_text  # Search the entire text if no specific section is found

    # Define patterns to search for the recommendation
    patterns = [
        r'it is recommended to (buy|hold|sell|strong buy|strong sell)',
        r'recommended to (buy|hold|sell|strong buy|strong sell)',
        r'we recommend (buying|holding|selling)',
        r'^(Buy|Hold|Sell|Strong Buy|Strong Sell)[\.:]',  # Line starts with 'Buy', possibly followed by '.' or ':'
        r'\b(Buy|Hold|Sell|Strong Buy|Strong Sell)\b',    # Matches standalone words
    ]

    for pattern in patterns:
        # Search within the recommendation section first
        rec_match = re.search(pattern, recommendation_section, re.IGNORECASE | re.MULTILINE)
        if rec_match:
            recommendation = rec_match.group(1).lower()
            # Normalize the recommendation word
            if recommendation in ['buying']:
                return 'Buy'
            elif recommendation in ['holding']:
                return 'Hold'
            elif recommendation in ['selling']:
                return 'Sell'
            else:
                return recommendation.title()

    # If not found in the section, search the entire analysis text
    for pattern in patterns:
        rec_match = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if rec_match:
            recommendation = rec_match.group(1).lower()
            if recommendation in ['buying']:
                return 'Buy'
            elif recommendation in ['holding']:
                return 'Hold'
            elif recommendation in ['selling']:
                return 'Sell'
            else:
                return recommendation.title()

    # If not found, log a warning
    print(f"Warning: No recommendation found in analysis text")
    return None

    
