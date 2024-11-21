
import re
import base64
import pandas as pd
import numpy as np
from util.database import DatabaseConnection
from util.general_util import parse_numeric_value, extract_numeric, load_svg_indicator




    

def process_stock_data(stock, latest_metric, portfolio_stocks, portfolio_indicator, ai_indicator, ai_recommendation):
    company_name = stock['company_name']
    symbol = stock.get('symbol', 'N/A')
    in_portfolio = symbol in portfolio_stocks
    indicator = f'<img src="{portfolio_indicator}" width="24" height="24">' if in_portfolio else ''
    company_name_with_indicator = f'{indicator} {company_name}'

    # Fetch the latest AI analysis
    analysis_doc = DatabaseConnection.get_collection('ai_analysis').find_one({'symbol': symbol}, sort=[('timestamp', -1)])
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

    return {
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
    }


def load_ai_indicator():
    # Get the selected AI API from the settings
    settings_doc = DatabaseConnection.get_collection('settings').find_one({'_id': 'ai_api_selection'})
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
    analyses = list(DatabaseConnection.get_collection('ai_analysis').find({'symbol': symbol}).sort('timestamp', 1))
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

def process_stock_batch(stocks, portfolio_stocks, ai_analyses):
    """Process a batch of stocks efficiently"""
    processed_data = []
    
    # Load indicators once per batch
    portfolio_indicator = load_svg_indicator('portfolio_indicator.svg')
    ai_indicator = load_ai_indicator()
    
    for stock in stocks:
        if not stock.get('financial_metrics'):
            continue
            
        latest_metric = stock['financial_metrics'][0]
        
        # Get AI analysis from prefetched data
        ai_analysis = ai_analyses.get(stock['symbol'])
        ai_recommendation = None
        if ai_analysis:
            ai_recommendation = extract_recommendation(ai_analysis['analysis'])
        
        processed_data.append(process_stock_data(
            stock, 
            latest_metric, 
            portfolio_stocks,
            portfolio_indicator,
            ai_indicator,
            ai_recommendation
        ))
    
    return processed_data
