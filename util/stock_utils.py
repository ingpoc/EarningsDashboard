# util/stock_utils.py

import dash_bootstrap_components as dbc
from dash import html
from typing import Any, Tuple, Optional
from functools import lru_cache
from util.database import DatabaseConnection


def get_value_attributes(value: Any, label: str) -> Tuple[str, str, str]:
    """Helper function to determine color and icon for values"""
    color = ""
    icon = ""
    
    if value is None or str(value).strip() in ['--', 'NA', 'nan', 'N/A', '', 'NaN']:
        return "", "", "N/A"
        
    try:
        if any(term in label.lower() for term in ['growth', 'yield', 'estimates']):
            value_float = float(str(value).replace(',', '').strip('%').split(':')[-1].strip())
            if value_float > 0:
                return "text-success", "▲", str(value)
            elif value_float < 0:
                return "text-danger", "▼", str(value)
    except (ValueError, IndexError):
        pass
        
    return color, icon, str(value)

def create_info_item(label: str, value: Any, is_percentage: bool = False, 
                    is_estimate: bool = False, is_piotroski: bool = False) -> html.Div:
    color, icon, formatted_value = get_value_attributes(value, label)
    
    if is_estimate and ':' in str(value):
        value_parts = str(value).split(':', 1)
        value_component = html.Div([
            html.Span(value_parts[0] + ':'),
            html.Span(value_parts[1].strip() if len(value_parts) > 1 else '')
        ])
    else:
        value_component = f"{icon} {formatted_value}" if icon else formatted_value
        
    return html.Div([
        html.Span(label, className="stock-details-label"),
        html.Div(value_component, className=f"stock-details-value {color}")
    ], className="stock-details-item")

def create_info_card(title, items, icon):
    return dbc.Card([
        dbc.CardHeader([
            html.I(className=f"fas {icon} me-2"),
            html.Span(title, className="h6 mb-0")
        ], className="d-flex align-items-center py-2"),
        dbc.CardBody([
            create_info_item(label, value, 
                             is_percentage='growth' in label.lower() or 'yield' in label.lower(),
                             is_estimate='estimates' in label.lower(),
                             is_piotroski='piotroski score' in label.lower())
            for label, value in items
        ], className="py-2")
    ], className="stock-details-card h-100")

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

# Optimize fetch_stock_names with error handling
@lru_cache(maxsize=500)
def fetch_stock_names():
    try:
        collection = DatabaseConnection.get_collection('detailed_financials')
        return sorted(list(set(stock['company_name'] for stock in collection.find({}, {"company_name": 1}))))
    except Exception as e:
        print(f"Error fetching stock names: {str(e)}")
        return []

def get_stock_symbol(company_name):
    stock = DatabaseConnection.get_collection('detailed_financials').find_one({"company_name": company_name})
    if stock and 'symbol' in stock:
        return f"{stock['symbol']}.NS"
    return None