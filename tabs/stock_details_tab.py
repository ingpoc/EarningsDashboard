import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
from util.charting import create_financial_metrics_chart, create_stock_price_chart
from util.utils import parse_numeric_value, get_collection
from util.recommendation import generate_stock_recommendation
from pymongo import MongoClient
from util.stock_utils import create_info_card
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

def prepare_data_sections(selected_data):
    basic_info = [
        ("CMP", selected_data.get('cmp', 'N/A')),
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

    return basic_info, valuation_metrics, financial_performance, insights

def stock_details_layout(company_name, show_full_layout=True):
    stock = get_collection('detailed_financials').find_one({"company_name": company_name})

    if not stock or not stock.get('financial_metrics'):
        return html.Div(["Stock not found or no data available."], className="text-danger")

    # Generate dropdown options from available quarters
    dropdown_options = [
        {'label': metric.get('quarter', 'N/A'), 'value': idx}
        for idx, metric in enumerate(stock['financial_metrics'])
    ]

    # Set default value to the last quarter
    default_value = len(stock['financial_metrics']) - 1

    # Fetch data for the default quarter
    selected_data = stock['financial_metrics'][default_value]

    # Prepare data for display using the helper function
    basic_info, valuation_metrics, financial_performance, insights = prepare_data_sections(selected_data)

    # Create info cards
    cards = [
        dbc.Col(create_info_card("Basic Information", basic_info, "fa-info-circle"), width=6),
        dbc.Col(create_info_card("Valuation Metrics", valuation_metrics, "fa-chart-line"), width=6),
        dbc.Col(create_info_card("Financial Performance", financial_performance, "fa-money-bill-wave"), width=6),
        dbc.Col(create_info_card("Insights", insights, "fa-lightbulb"), width=6)
    ]

    # Recommendation
    recommendation = generate_stock_recommendation(selected_data)

    # Layout with quarter dropdown and info cards container
    layout = dbc.Container([
        # Hidden Div to store company name
        html.Div(company_name, id='company-name-store', style={'display': 'none'}),
        html.H3(f"Details for {company_name}", className="mb-3 text-center text-primary font-weight-bold"),
        # Quarter dropdown
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='quarter-dropdown',
                    options=dropdown_options,
                    value=default_value,
                    clearable=False,
                    style={'width': '300px', 'margin': '0 auto'}
                )
            ], width=12, className='d-flex justify-content-center mb-4')
        ]),
        # Container for info cards
        dbc.Row(id='info-cards', children=cards, className="g-2 mb-4"),
        # Recommendation alert with an assigned ID
        html.H4("Recommendation", className="text-center"),
        dbc.Alert(recommendation, color="info", className="text-center mb-4", id='recommendation-alert'),
        # Remaining components (charts, buttons, etc.)
        html.H4("Stock Price Chart", className="text-center"),
        dcc.Graph(figure=create_stock_price_chart(company_name), className="mb-4"),
        html.H4("Financial Metrics Chart", className="text-center"),
        dcc.Graph(figure=create_financial_metrics_chart(fetch_stock_data(company_name))),
        dbc.Button("Share to Twitter", id="twitter-share-button", color="primary", className="mt-3 rounded-pill"),
        html.Div(id='twitter-share-response', className="mt-3")
    ], fluid=True, className="py-2")

    if show_full_layout:
        return layout

    return dbc.Container([
        dbc.Row(cards, className="g-2"),
    ], fluid=True, className="py-2")


def fetch_stock_data(company_name):
    stock = get_collection('detailed_financials').find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
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



# Callback to store selected data for sharing
def register_stock_details_callbacks(app):
    @app.callback(
        [Output('info-cards', 'children'),
         Output('recommendation-alert', 'children')],
        [Input('quarter-dropdown', 'value')],
        [State('company-name-store', 'children')]
    )
    def update_info_cards(selected_quarter_idx, company_name):
        stock = get_collection('detailed_financials').find_one({"company_name": company_name})
        if stock and stock.get('financial_metrics'):
            selected_data = stock['financial_metrics'][int(selected_quarter_idx)]

            # Prepare data for display using the helper function
            basic_info, valuation_metrics, financial_performance, insights = prepare_data_sections(selected_data)

            # Create info cards
            cards = [
                dbc.Col(create_info_card("Basic Information", basic_info, "fa-info-circle"), width=6),
                dbc.Col(create_info_card("Valuation Metrics", valuation_metrics, "fa-chart-line"), width=6),
                dbc.Col(create_info_card("Financial Performance", financial_performance, "fa-money-bill-wave"), width=6),
                dbc.Col(create_info_card("Insights", insights, "fa-lightbulb"), width=6)
            ]

            # Generate recommendation
            recommendation = generate_stock_recommendation(selected_data)

            return cards, recommendation

        # Return empty if no data is available
        return [], ""