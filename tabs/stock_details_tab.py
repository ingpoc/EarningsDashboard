import dash_bootstrap_components as dbc
from dash import html, dash_table
import pandas as pd
from dash.dash_table.Format import Format, Scheme
from pymongo import MongoClient
from util.utils import fetch_latest_quarter_data, process_estimates
from dash.dependencies import Input, Output, State
import dash
from util.utils import parse_numeric_value
from util.charting import create_financial_metrics_chart, create_stock_price_chart
from dash import dcc, html, dash_table, callback_context

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']

def stock_details_layout(company_name, show_full_layout=True):
    stock = collection.find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
    
    if not stock or not stock.get('financial_metrics'):
        return html.Div(["Stock not found or no data available."], className="text-danger")

    selected_data = stock['financial_metrics'][-1]
    colors = {'background': '#ffffff', 'text': '#333333', 'primary': '#003366'}

    financials_layout = create_financial_segments(selected_data, colors)
    twitter_button = dbc.Button("Share to Twitter", id="twitter-share-button", color="info", className="mt-3")
    twitter_share_response = html.Div(id='twitter-share-response', className="mt-3")

    # Store selected_data in dcc.Store
    data_store = dcc.Store(id='selected-data-store', data=selected_data)

    if show_full_layout:
        return dbc.Container([
            html.H3(f"Details for {company_name}", className="mb-4 text-center", style={'color': colors['primary']}),
            dcc.Dropdown(
                id='quarter-dropdown',
                options=[{'label': quarter, 'value': quarter} for quarter in [selected_data['quarter']]],
                value=selected_data['quarter'],
                clearable=False,
                style={'width': '50%', 'margin': '0 auto', 'marginBottom': '20px'}
            ),
            dbc.Tabs([
                dbc.Tab(financials_layout, label="Financials"),
                dbc.Tab([
                    dcc.Graph(id='stock-price-chart', figure=create_stock_price_chart(company_name)),
                    dcc.Graph(id='financial-metrics-chart', figure=create_financial_metrics_chart(fetch_stock_data(company_name))),
                ], label="Charts"),
                # Uncomment below line to add news tab
                # dbc.Tab([html.Ul([html.Li(html.A(article['title'], href=article['url'], target="_blank")) for article in fetch_stock_news(company_name)])], label="News"),
            ]),
            html.Br(),
            dbc.Alert(id='recommendation-alert', color="info"),
            twitter_button,
            twitter_share_response
        ], fluid=True, style={'backgroundColor': colors['background'], 'padding': '20px'})

    return dbc.Container([financials_layout, twitter_button, twitter_share_response, data_store], fluid=True, style={'backgroundColor': colors['background'], 'padding': '20px'})


def create_financial_segments(selected_data, colors):
    def format_estimate(estimate):
        if 'Beat' in estimate:
            return html.Span(estimate, style={'color': 'green'})
        elif 'Missed' in estimate:
            return html.Span(estimate, style={'color': 'red'})
        else:
            return estimate

    cards = [
        ("Basic Information", [
            f"CMP: {selected_data.get('cmp', 'N/A')}",
            f"Report Type: {selected_data.get('report_type', 'N/A')}",
            f"Result Date: {selected_data.get('result_date', 'N/A')}"
        ]),
        ("Valuation Metrics", [
            f"Market Cap: {selected_data.get('market_cap', 'N/A')}",
            f"Face Value: {selected_data.get('face_value', 'N/A')}",
            f"Book Value: {selected_data.get('book_value', 'N/A')}",
            f"Dividend Yield: {selected_data.get('dividend_yield', 'N/A')}",
            f"TTM EPS: {selected_data.get('ttm_eps', 'N/A')}",
            f"TTM P/E: {selected_data.get('ttm_pe', 'N/A')}",
            f"P/B Ratio: {selected_data.get('pb_ratio', 'N/A')}",
            f"Sector P/E: {selected_data.get('sector_pe', 'N/A')}"
        ]),
        ("Financial Performance", [
            f"Revenue: {selected_data.get('revenue', 'N/A')}",
            f"Gross Profit: {selected_data.get('gross_profit', 'N/A')}",
            f"Gross Profit Growth: {selected_data.get('gross_profit_growth', 'N/A')}",
            f"Revenue Growth: {selected_data.get('revenue_growth', 'N/A')}",
            f"Net Profit: {selected_data.get('net_profit', 'N/A')}"
        ]),
        ("Insights", [
            f"Strengths: {selected_data.get('strengths', 'N/A')}",
            f"Weaknesses: {selected_data.get('weaknesses', 'N/A')}",
            f"Technicals Trend: {selected_data.get('technicals_trend', 'N/A')}",
            f"Fundamental Insights: {selected_data.get('fundamental_insights', 'N/A')}",
            f"Net Profit Growth: {selected_data.get('net_profit_growth', 'N/A')}",
            f"Piotroski Score: {selected_data.get('piotroski_score', 'N/A')}",
            html.Span(["Estimates: ", format_estimate(selected_data.get('estimates', 'N/A'))])
        ])
    ]

    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5(title, className="mb-0")),
                dbc.CardBody([html.P(item, className="mb-1") for item in items])
            ], className="mb-4 shadow-sm"), width=6) 
            for title, items in cards
        ])
    ])




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