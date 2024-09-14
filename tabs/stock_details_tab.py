
import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
from util.charting import create_financial_metrics_chart, create_stock_price_chart
from util.utils import parse_numeric_value
from pymongo import MongoClient

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']

def create_info_item(label, value, is_percentage=False):
    color = ""
    if is_percentage:
        try:
            value_float = float(value.strip('%'))
            if value_float > 0:
                color = "text-success"
            elif value_float < 0:
                color = "text-danger"
        except ValueError:
            pass
    
    return html.Div([
        html.Span(label, className="stock-details-label"),
        html.Span(value, className=f"stock-details-value {color}")
    ], className="stock-details-item")

def create_info_card(title, items, icon):
    return dbc.Card([
        dbc.CardHeader([
            html.I(className=f"fas {icon} me-2"),
            html.Span(title, className="h6 mb-0")
        ], className="d-flex align-items-center py-2"),
        dbc.CardBody([create_info_item(label, value, 'growth' in label.lower() or 'yield' in label.lower()) for label, value in items], className="py-2")
    ], className="stock-details-card h-100")

def stock_details_layout(company_name, show_full_layout=True):
    stock = collection.find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
    
    if not stock or not stock.get('financial_metrics'):
        return html.Div(["Stock not found or no data available."], className="text-danger")

    selected_data = stock['financial_metrics'][-1]

    basic_info = [
        ("CMP", f"{selected_data.get('cmp', 'N/A')}"),
        ("Report Type", selected_data.get('report_type', 'N/A')),
        ("Result Date", selected_data.get('result_date', 'N/A'))
    ]

    valuation_metrics = [
        ("Market Cap", selected_data.get('market_cap', 'N/A')),
        ("Face Value", selected_data.get('face_value', 'N/A')),
        ("Book Value", selected_data.get('book_value', 'N/A')),
        ("Dividend Yield", selected_data.get('dividend_yield', 'N/A')),
        ("TTM EPS", selected_data.get('ttm_eps', 'N/A')),
        ("TTM P/E", selected_data.get('ttm_pe', 'N/A')),
        ("P/B Ratio", selected_data.get('pb_ratio', 'N/A')),
        ("Sector P/E", selected_data.get('sector_pe', 'N/A'))
    ]

    financial_performance = [
        ("Revenue", selected_data.get('revenue', 'N/A')),
        ("Gross Profit", selected_data.get('gross_profit', 'N/A')),
        ("Gross Profit Growth", selected_data.get('gross_profit_growth', 'N/A')),
        ("Revenue Growth", selected_data.get('revenue_growth', 'N/A')),
        ("Net Profit", selected_data.get('net_profit', 'N/A'))
    ]

    insights = [
        ("Strengths", selected_data.get('strengths', 'N/A')),
        ("Weaknesses", selected_data.get('weaknesses', 'N/A')),
        ("Technicals Trend", selected_data.get('technicals_trend', 'N/A')),
        ("Fundamental Insights", selected_data.get('fundamental_insights', 'N/A')),
        ("Net Profit Growth", selected_data.get('net_profit_growth', 'N/A')),
        ("Piotroski Score", selected_data.get('piotroski_score', 'N/A')),
        ("Estimates", selected_data.get('estimates', 'N/A'))
    ]

    cards = [
        dbc.Col(create_info_card("Basic Information", basic_info, "fa-info-circle"), width=6),
        dbc.Col(create_info_card("Valuation Metrics", valuation_metrics, "fa-chart-line"), width=6),
        dbc.Col(create_info_card("Financial Performance", financial_performance, "fa-money-bill-wave"), width=6),
        dbc.Col(create_info_card("Insights", insights, "fa-lightbulb"), width=6)
    ]

    layout = dbc.Container([
        dbc.Row(cards, className="g-2"),
        dbc.Button("Share to Twitter", id="twitter-share-button", color="primary", className="mt-3 rounded-pill"),
        html.Div(id='twitter-share-response', className="mt-3")
    ], fluid=True, className="py-2")

    if show_full_layout:
        return dbc.Container([
            html.H3(f"Details for {company_name}", className="mb-3 text-center text-primary font-weight-bold"),
            dcc.Dropdown(
                id='quarter-dropdown',
                options=[{'label': quarter, 'value': quarter} for quarter in [selected_data['quarter']]],
                value=selected_data['quarter'],
                clearable=False,
                className="mb-3 w-50 mx-auto"
            ),
            dbc.Tabs([
                dbc.Tab(layout, label="Financials", className="border-bottom"),
                dbc.Tab([
                    dcc.Graph(id='stock-price-chart', figure=create_stock_price_chart(company_name)),
                    dcc.Graph(id='financial-metrics-chart', figure=create_financial_metrics_chart(fetch_stock_data(company_name))),
                ], label="Charts", className="border-bottom"),
            ], className="mb-3"),
            dbc.Alert(id='recommendation-alert', color="info", className="mb-3"),
        ], fluid=True, className="bg-light p-3 rounded shadow-sm")

    return layout


def fetch_stock_data(company_name):
    stock = collection.find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
    if not stock:
        print(f"Stock not found in MongoDB: {company_name}")
        return pd.DataFrame()
    
    stock_data = [{
        "quarter": metric.get("quarter", "N/A"),
        "market_cap": parse_numeric_value(metric.get("market_cap")),
        "ttm_pe": parse_numeric_value(metric.get("ttm_pe")),
        "revenue": parse_numeric_value(metric.get("revenue")),
        "gross_profit": parse_numeric_value(metric.get("gross_profit")),
        "net_profit": parse_numeric_value(metric.get("net_profit")),
        "revenue_growth": parse_numeric_value(metric.get("revenue_growth"), '%'),
        "gross_profit_growth": parse_numeric_value(metric.get("gross_profit_growth"), '%'),
        "net_profit_growth": parse_numeric_value(metric.get("net_profit_growth"), '%'),
        "dividend_yield": parse_numeric_value(metric.get("dividend_yield"), '%'),
        "debt_to_equity": parse_numeric_value(metric.get("debt_to_equity"))
    } for metric in stock['financial_metrics']]
    
    return pd.DataFrame(stock_data)