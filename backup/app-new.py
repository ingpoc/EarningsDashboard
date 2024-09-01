import base64
import io
import subprocess
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from functools import lru_cache
import requests
import html
import tweepy
import os
import requests
from dash import html
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf


# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']
holdings_collection = db['holdings']

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Register callbacks from other files
#register_community_callbacks(app)
#register_twitter_callbacks(app)
#register_twitter_post_callbacks(app)  
#register_scraper_callbacks(app)

#### Community Tab ####
# community_tab.py

# Community page layout


TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    return_type=requests.Response,
    wait_on_rate_limit=True
)

#### utils.py#####

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
    net_profit_growth = row.get('net_profit_growth', 0)  # Use 'net_profit_growth' instead of 'Net Profit Growth %'
    
    if pd.isna(net_profit_growth):
        return "N/A"
    elif net_profit_growth > 10:
        return "Buy"
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
    


#### Layout.py #####
# layout.py

# Define a custom CSS style
custom_style = {
    'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
    'transition': '0.3s',
    'borderRadius': '5px',
    'padding': '20px',
    'marginBottom': '20px'
}

# Update the sidebar style
sidebar_style = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# Update the content style
content_style = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}
# Define the modal for displaying stock details
details_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Portfolio Stock Details")),
        dbc.ModalBody(id='details-body'),
    ],
    id="details-modal",
    size="lg",
)

# Define the modal for displaying stock details from the overview table
overview_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle(id='modal-title')),  # Dynamic title
        dbc.ModalBody(id='overview-details-body'),
    ],
    id="overview-details-modal",
    size="lg",
)

# Sidebar layout
sidebar = html.Div(
    [
        html.H2("Earnings Dashboard", className="display-4"),
        html.Hr(),
        dcc.Dropdown(
            id='stock-search-sidebar',
            options=[{'label': name, 'value': name} for name in fetch_stock_names(collection)],
            placeholder="Search for a stock...",
            className="mb-3",
        ),
        dbc.Nav(
            [
                dbc.NavLink("Overview", href="/overview", active="exact", className="mb-1"),
                dbc.NavLink("Portfolio", href="/portfolio", active="exact", className="mb-1"),
                dbc.NavLink("Scraper", href="/scraper", active="exact", className="mb-1"),
                dbc.NavLink("Community", href="/community", active="exact", className="mb-1"),
                dbc.NavLink("Settings", href="/settings", active="exact", className="mb-1"),
            ],
            vertical=True,
            pills=True,
        ),
        dbc.Switch(id="dark-mode-switch", label="Dark Mode", value=False, className="mt-3"),
    ],
    style=sidebar_style,
)

# Content layout
content = dbc.Col(id="page-content", width=10, style={"margin-left": "16.666667%", "padding": "20px"})

# App layout
app_layout = dbc.Container(
    [
        dcc.Location(id='url', refresh=False),
        dbc.Row(
            [
                sidebar,
                content,
                details_modal, # Include the modal in the layout
                overview_modal  # Modal for Overview section
            ]
        )
    ],
    fluid=True,
    style={"background-color": "#f0f2f5"}
)

# Set the app layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    sidebar,
    html.Div(id="page-content", style=content_style)
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


@lru_cache(maxsize=32)
def fetch_latest_quarter_data():
    stocks = list(collection.find({}, {"company_name": 1, "financial_metrics": {"$slice": -1}, "_id": 0}))
    
    stock_data = [{
        "company_name": stock['company_name'],
        "formatted_date": pd.to_datetime(latest_metric.get("result_date", "N/A")).strftime("%d, %B %Y"),
        "net_profit_growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0")),
        "cmp": parse_numeric_value(latest_metric.get("cmp", "0").split()[0]),
        "quarter": latest_metric.get("quarter", "N/A"),
        "ttm_pe": parse_numeric_value(latest_metric.get("ttm_pe", "0")),
        "revenue": parse_numeric_value(latest_metric.get("revenue", "0")),
        "net_profit": parse_numeric_value(latest_metric.get("net_profit", "0"))
    } for stock in stocks for latest_metric in stock['financial_metrics']]
    
    df = pd.DataFrame(stock_data).sort_values(by="formatted_date", ascending=False)
    return df


def create_financial_segments(selected_data, colors):
   
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
            f"Ttm Eps: {selected_data.get('ttm_eps', 'N/A')}",
            f"Ttm Pe: {selected_data.get('ttm_pe', 'N/A')}",
            f"Pb Ratio: {selected_data.get('pb_ratio', 'N/A')}",
            f"Sector Pe: {selected_data.get('sector_pe', 'N/A')}"
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
            f"Piotroski Score: {selected_data.get('piotroski_score', 'N/A')}"
        ])
    ]

    return dbc.Container([
        html.Br(),
        dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader(title), dbc.CardBody([html.P(item) for item in items])], className="mb-4 shadow-sm"), width=6) for title, items in cards[:2]]),
        dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader(title), dbc.CardBody([html.P(item) for item in items])], className="mb-4 shadow-sm"), width=6) for title, items in cards[2:]])
    ])



def stock_details_layout(company_name, show_full_layout=False):
    stock = collection.find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
    
    if not stock or not stock.get('financial_metrics'):
        return html.Div(["No data available for this stock."], className="text-danger")

    selected_data = stock['financial_metrics'][-1]
    colors = {'background': '#ffffff', 'text': '#333333', 'primary': '#003366'}

    # Create a safe_get function to handle potentially missing data
    def safe_get(data, key, default="N/A"):
        return data.get(key, default)

    financials_layout = dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Basic Information"),
                dbc.CardBody([
                    html.P(f"CMP: {safe_get(selected_data, 'cmp')}"),
                    html.P(f"Report Type: {safe_get(selected_data, 'report_type')}"),
                    html.P(f"Result Date: {safe_get(selected_data, 'result_date')}")
                ])
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Valuation Metrics"),
                dbc.CardBody([
                    html.P(f"Market Cap: {safe_get(selected_data, 'market_cap')}"),
                    html.P(f"Face Value: {safe_get(selected_data, 'face_value')}"),
                    html.P(f"Book Value: {safe_get(selected_data, 'book_value')}"),
                    html.P(f"Dividend Yield: {safe_get(selected_data, 'dividend_yield')}")
                ])
            ]), width=6),
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Financial Performance"),
                dbc.CardBody([
                    html.P(f"Revenue: {safe_get(selected_data, 'revenue')}"),
                    html.P(f"Gross Profit: {safe_get(selected_data, 'gross_profit')}"),
                    html.P(f"Net Profit: {safe_get(selected_data, 'net_profit')}"),
                    html.P(f"Net Profit Growth: {safe_get(selected_data, 'net_profit_growth')}")
                ])
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("Insights"),
                dbc.CardBody([
                    html.P(f"Strengths: {safe_get(selected_data, 'strengths')}"),
                    html.P(f"Weaknesses: {safe_get(selected_data, 'weaknesses')}"),
                    html.P(f"Technicals Trend: {safe_get(selected_data, 'technicals_trend')}"),
                    html.P(f"Fundamental Insights: {safe_get(selected_data, 'fundamental_insights')}")
                ])
            ]), width=6),
        ])
    ])

    return financials_layout

@app.callback(
    [Output('overview-details-modal', 'is_open'),
     Output('overview-details-body', 'children'),
     Output('modal-title', 'children')],
    [Input('stocks-table', 'selected_rows')],
    [State('stocks-table', 'data')]
)
def display_overview_details(selected_rows, rows):
    if selected_rows:
        row = rows[selected_rows[0]]
        company_name = row['company_name']
        stock_details = stock_details_layout(company_name, show_full_layout=False)
        return True, stock_details, f"Stock Details of {company_name}"
    return False, "", ""


@app.callback(
    Output('recommendation-alert', 'children'),
    Input('quarter-dropdown', 'value'),
    State('url', 'pathname')
)
def update_quarter_details(selected_quarter, pathname):
    company_name = pathname.split("/stock/")[1]
    stock = collection.find_one({"company_name": company_name})
    
    if not stock:
        return "No data available."

    selected_data = next((metric for metric in stock['financial_metrics'] if metric['quarter'] == selected_quarter), None)
    
    if not selected_data:
        return "No data available for this quarter."
    
    recommendation = get_recommendation(pd.DataFrame([selected_data]))
    return f"Recommendation: {recommendation}"


@app.callback(
    Output('details-modal', 'is_open'),
    Output('details-body', 'children'),
    [Input('portfolio-table', 'selected_rows')],
    [State('portfolio-table', 'data')]
)
def display_details(selected_rows, rows):
    if selected_rows:
        row = rows[selected_rows[0]]
        instrument_name = row['Instrument']
        stock_details = fetch_latest_metrics(instrument_name)
        holding = holdings_collection.find_one({"Instrument": instrument_name})

        net_profit_growth = stock_details.get('net_profit_growth', 'N/A')
        if isinstance(net_profit_growth, (int, float)):
            net_profit_growth = f"{net_profit_growth}%"
        elif isinstance(net_profit_growth, str) and not net_profit_growth.endswith('%'):
            net_profit_growth = f"{net_profit_growth}%"

        details_content = dbc.Container([
            dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Basic Information", className="card-title"),
                html.P(f"Instrument: {instrument_name}"),
                html.P(f"Quantity: {holding.get('Qty.', 'N/A')}"),
                html.P(f"Avg Cost: {holding.get('Avg. cost', 'N/A')}"),
                html.P(f"Current Value: {holding.get('Cur. val', 'N/A')}"),
                html.P(f"P&L: {holding.get('P&L', 'N/A')}")
            ]), className="mb-3"), md=6),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Financial Performance", className="card-title"),
                    html.P(f"Net Profit Growth: {net_profit_growth}"),
                    html.P(f"Piotroski Score: {stock_details.get('piotroski_score', 'N/A')}"),
                    html.P(f"Strengths: {stock_details.get('strengths', 'N/A')}"),
                    html.P(f"Weaknesses: {stock_details.get('weaknesses', 'N/A')}")
                ]), className="mb-3"), md=6)]),
            dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Technical Insights", className="card-title"),
                html.P(f"Technicals Trend: {stock_details.get('technicals_trend', 'N/A')}"),
                html.P(f"Fundamental Insights: {stock_details.get('fundamental_insights', 'N/A')}")
            ]), className="mb-3"), md=12)])
        ], fluid=True)

        return True, details_content
    return False, []

def fetch_latest_metrics(symbol):
    stock = collection.find_one({"symbol": symbol})
    
    if not stock or not stock.get('financial_metrics'):
        return {
            "Net Profit Growth": 0,
            "Strengths": 0,
            "Weaknesses": 0,
            "Technicals Trend": "NA",
            "Fundamental Insights": "NA",
            "Piotroski Score": 0
        }

    latest_metric = max(stock['financial_metrics'], key=lambda x: pd.to_datetime(x.get("result_date", "N/A")))
    
    # Extract only the number from strengths and weaknesses
    strengths = latest_metric.get("strengths", "0")
    weaknesses = latest_metric.get("weaknesses", "0")
    strengths_num = int(''.join(filter(str.isdigit, strengths))) if strengths else 0
    weaknesses_num = int(''.join(filter(str.isdigit, weaknesses))) if weaknesses else 0
    
    return {
        "Net Profit Growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0")),
        "Strengths": strengths_num,
        "Weaknesses": weaknesses_num,
        "Technicals Trend": latest_metric.get("technicals_trend", "NA"),
        "Fundamental Insights": latest_metric.get("fundamental_insights", "NA"),
        "Piotroski Score": parse_numeric_value(latest_metric.get("piotroski_score", "0"))
    }

# Callback to update page content
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == "/overview" or pathname == "/":
        return overview_layout()
    elif pathname.startswith("/stock/"):
        company_name = pathname.split("/stock/")[1]
        return stock_details_layout(company_name)
    elif pathname == "/portfolio":
        return portfolio_layout()
    elif pathname == "/scraper":
        return scraper_layout()
    elif pathname == "/community":
        return community_layout()
    elif pathname == "/settings":
        return settings_layout()
    return html.Div(["404 - Page not found"], className="text-danger")


# Update the create_card function
def create_card(title, content):
    return dbc.Card(
        [
            dbc.CardHeader(html.H4(title, className="card-title")),
            dbc.CardBody(content)
        ],
        className="mb-4",
        style=custom_style
    )

# Update the create_table function
def create_table(id, data, columns):
    return dash_table.DataTable(
        id=id,
        data=data,
        columns=columns,
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'font-family': 'Arial, sans-serif',
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'border': '1px solid #ddd',
        },
        style_data={
            'border': '1px solid #ddd',
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f9f9f9',
            }
        ],
        filter_action="native",
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=10,
        row_selectable='single',
        selected_rows=[],
    )



def overview_layout():
    df = fetch_latest_quarter_data()
    top_performers = df.sort_values(by="net_profit_growth", ascending=False).head(10)
    worst_performers = df.sort_values(by="net_profit_growth", ascending=True).head(10)
    latest_results = df.head(10).sort_values(by="net_profit_growth", ascending=False)

    return dbc.Container([
        dbc.Row([
            dbc.Col(create_card("Top 10 Performers", create_table('top-performers-table', top_performers.to_dict('records'), [
                {"name": "Company Name", "id": "company_name"},
                {"name": "Result Date", "id": "formatted_date"},
                {"name": "Net Profit Growth (%)", "id": "net_profit_growth"},
                {"name": "CMP", "id": "cmp"},
            ])), md=6),
            dbc.Col(create_card("Worst 10 Performers", create_table('worst-performers-table', worst_performers.to_dict('records'), [
                {"name": "Company Name", "id": "company_name"},
                {"name": "Result Date", "id": "formatted_date"},
                {"name": "Net Profit Growth (%)", "id": "net_profit_growth"},
                {"name": "CMP", "id": "cmp"},
            ])), md=6),
        ]),
        dbc.Row([
            dbc.Col(create_card("Latest 10 Results", create_table('latest-results-table', latest_results.to_dict('records'), [
                {"name": "Company Name", "id": "company_name"},
                {"name": "Result Date", "id": "formatted_date"},
                {"name": "Net Profit Growth (%)", "id": "net_profit_growth"},
                {"name": "Quarter", "id": "quarter"},
            ])), md=12),
        ]),
        dbc.Row([
            dbc.Col(create_card("Stocks Overview", create_table('stocks-table', df.to_dict('records'), [
                {"name": "Company Name", "id": "company_name"},
                {"name": "CMP", "id": "cmp"},
                {"name": "P/E Ratio", "id": "ttm_pe"},
                {"name": "Revenue", "id": "revenue"},
                {"name": "Net Profit", "id": "net_profit"},
                {"name": "Net Profit Growth(%)", "id": "net_profit_growth"},
                {"name": "Result Date", "id": "formatted_date"},
            ])), md=12),
        ]),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="overview-modal-title")),
                dbc.ModalBody(id="overview-modal-body"),
            ],
            id="overview-modal",
            size="lg",
        ),
    ], fluid=True)


@app.callback(
    [Output("overview-modal", "is_open"),
     Output("overview-modal-title", "children"),
     Output("overview-modal-body", "children")],
    [Input("top-performers-table", "selected_rows"),
     Input("worst-performers-table", "selected_rows"),
     Input("latest-results-table", "selected_rows"),
     Input("stocks-table", "selected_rows")],
    [State("top-performers-table", "data"),
     State("worst-performers-table", "data"),
     State("latest-results-table", "data"),
     State("stocks-table", "data")]
)
def toggle_overview_modal(top_selected, worst_selected, latest_selected, stocks_selected,
                          top_data, worst_data, latest_data, stocks_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_rows = ctx.triggered[0]['value']
    
    if selected_rows:
        if button_id == "top-performers-table":
            data = top_data
        elif button_id == "worst-performers-table":
            data = worst_data
        elif button_id == "latest-results-table":
            data = latest_data
        else:
            data = stocks_data
        
        selected_row = data[selected_rows[0]]
        company_name = selected_row['company_name']
        return True, f"Details for {company_name}", stock_details_layout(company_name)
    
    return False, "", ""

@app.callback(
    [Output("portfolio-modal", "is_open"),
     Output("portfolio-modal-title", "children"),
     Output("portfolio-modal-body", "children")],
    [Input("portfolio-table", "selected_rows")],
    [State("portfolio-table", "data")]
)
def toggle_portfolio_modal(selected_rows, rows):
    if selected_rows:
        selected_row = rows[selected_rows[0]]
        instrument_name = selected_row['Instrument']
        stock_details = fetch_latest_metrics(instrument_name)
        details_content = create_portfolio_details_content(selected_row, stock_details)
        return True, f"Details for {instrument_name}", details_content
    return False, "", ""

def create_portfolio_details_content(row, stock_details):
    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Basic Information", className="card-title"),
                html.P(f"Instrument: {row['Instrument']}"),
                html.P(f"Quantity: {row.get('Qty.', 'N/A')}"),
                html.P(f"Avg Cost: {row.get('Avg. cost', 'N/A')}"),
                html.P(f"Current Value: {row.get('Cur. val', 'N/A')}"),
                html.P(f"P&L: {row.get('P&L', 'N/A')}")
            ])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Financial Performance", className="card-title"),
                html.P(f"Net Profit Growth: {stock_details.get('Net Profit Growth', 'N/A')}"),
                html.P(f"Piotroski Score: {stock_details.get('Piotroski Score', 'N/A')}"),
                html.P(f"Strengths: {stock_details.get('Strengths', 'N/A')}"),
                html.P(f"Weaknesses: {stock_details.get('Weaknesses', 'N/A')}")
            ])), width=6),
        ]),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Technical Insights", className="card-title"),
                html.P(f"Technicals Trend: {stock_details.get('Technicals Trend', 'N/A')}"),
                html.P(f"Fundamental Insights: {stock_details.get('Fundamental Insights', 'N/A')}")
            ])), width=12),
        ]),
    ])

# Portfolio page layout
def portfolio_layout():
    try:
        holdings_data = list(holdings_collection.find())
        if not holdings_data:
            return html.Div("No portfolio data available.", className="text-danger")

        df = pd.DataFrame(holdings_data)
        metrics = df['Instrument'].apply(fetch_latest_metrics).apply(pd.Series)
        df = pd.concat([df, metrics], axis=1)

        df = df.rename(columns={
            "net_profit_growth": "Net Profit Growth",
            "strengths": "Strengths",
            "weaknesses": "Weaknesses",
            "technicals_trend": "Technicals Trend",
            "fundamental_insights": "Fundamental Insights",
            "piotroski_score": "Piotroski Score"
        })

        # Convert numeric columns to appropriate types
        numeric_columns = ['Net Profit Growth', 'Strengths', 'Weaknesses', 'Piotroski Score']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        filtered_df = df[['Instrument', 'LTP', 'Cur. val', 'P&L', 'Net Profit Growth', 'Strengths', 'Weaknesses', 'Technicals Trend', 'Fundamental Insights', 'Piotroski Score']]
        filtered_df['Recommendation'] = filtered_df.apply(get_stock_recommendation, axis=1)

        return dbc.Container([
            dbc.Row([
                dbc.Col(html.H3("Portfolio Management"), width=12),
            ]),
            dbc.Row([
                dbc.Col(dcc.Upload(
                    id='upload-data',
                    children=dbc.Button("Upload Portfolio Data", color="primary"),
                    multiple=False
                ), width=12, className="mb-3"),
            ]),
            html.Div(id='output-data-upload'),
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        id="loading-portfolio",
                        type="circle",
                        children=[
                            create_card("Current Portfolio", create_table('portfolio-table', filtered_df.to_dict('records'), [{'name': i, 'id': i} for i in filtered_df.columns]))
                        ]
                    ),
                    width=12
                ),
            ]),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="portfolio-modal-title")),
                    dbc.ModalBody(id="portfolio-modal-body"),
                ],
                id="portfolio-modal",
                size="lg",
            ),
        ], fluid=True)
    except Exception as e:
        return html.Div(f"An error occurred: {str(e)}", className="text-danger")
    

@app.callback(
    Output('url', 'pathname'),
    [Input('stock-search-sidebar', 'value')]
)
def search_stock(value):
    if value:
        return f"/stock/{value}"
    return dash.no_update


@app.callback(
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(contents, filename):
    if contents is not None:
        holdings_collection.delete_many({})

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8'))) if 'csv' in filename else pd.read_excel(io.BytesIO(decoded))
            holdings_collection.insert_many(df.to_dict("records"))

            holdings_data = list(holdings_collection.find())

            if not holdings_data:
                return html.Div("No portfolio data available.", className="text-danger")

            df = pd.DataFrame(holdings_data)

            filtered_df = df[['Instrument', 'Qty.', 'Avg. cost', 'LTP', 'Cur. val', 'P&L']]
            filtered_df['Recommendation'] = filtered_df.apply(get_stock_recommendation, axis=1)

            return dash_table.DataTable(
                data=filtered_df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in filtered_df.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
                style_as_list_view=True,
            )

        except Exception as e:
            return html.Div([f'There was an error processing this file: {str(e)}'])

# Callback for dark mode
@app.callback(
    Output('page-content', 'style'),
    [Input('dark-mode-switch', 'value')]
)
def toggle_dark_mode(dark_mode):
    return {'backgroundColor': '#222', 'color': '#ddd', 'margin-left': '16.666667%'} if dark_mode else {'backgroundColor': '#fff', 'color': '#000', 'margin-left': '16.666667%'}






#### Charting.py #####
def create_market_summary_chart():
    indices = ['S&P 500', 'NASDAQ', 'DOW']
    values = [4200, 14000, 34000]
    changes = [2.1, 1.5, 1.8]
    
    fig = go.Figure(data=[
        go.Bar(name='Value', x=indices, y=values),
        go.Bar(name='Change %', x=indices, y=changes)
    ])
    fig.update_layout(barmode='group', title='Market Summary', title_x=0.5)
    return fig

def create_sector_performance_chart():
    sectors = ['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy']
    performance = [5.2, 3.1, 2.5, 1.8, -0.5]
    
    fig = px.bar(x=sectors, y=performance, title='Sector Performance', color=performance)
    fig.update_layout(title_x=0.5)
    return fig

def create_stock_price_chart(company_name):
    stock = yf.Ticker(company_name)
    hist = stock.history(period="1y")
    
    fig = go.Figure(data=[go.Candlestick(x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'])])
    fig.update_layout(title=f'{company_name} Stock Price - Past Year', xaxis_rangeslider_visible=False, title_x=0.5)
    return fig

def create_financial_metrics_chart(df):
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()
    if 'revenue' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['revenue'], mode='lines+markers', name='Revenue'))
    if 'gross_profit' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['gross_profit'], mode='lines+markers', name='Gross Profit'))
    if 'net_profit' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['net_profit'], mode='lines+markers', name='Net Profit'))
    if 'dividend_yield' in df.columns:
        fig.add_trace(go.Scatter(x=df['quarter'], y=df['dividend_yield'], mode='lines+markers', name='Dividend Yield', yaxis='y2'))

    # Update layout to correctly handle dual y-axes
    fig.update_layout(
        title='Financial Metrics Over Time',
        xaxis_title='Quarter',
        yaxis=dict(
            title='Amount',
        ),
        yaxis2=dict(
            title='Dividend Yield (%)',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig



#### Scraper Tab ######
#scraper_tab.py
# scraper_tab.py
# Scraper page layout
def scraper_layout():
    return html.Div([
        html.H3("Stock Scraper"),
        dbc.Button("Scrape Latest Results", id="scrape-latest-button", color="primary"),
        dbc.Button("Scrape Best Performers", id="scrape-best-button", color="success", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Worst Performers", id="scrape-worst-button", color="danger", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Positive Turn Around", id="scrape-positive-turn-around-button", color="success", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Negative Turn Around", id="scrape-negative-turn-around-button", color="danger", style={"marginLeft": "10px"}),
        html.Div(id='scraper-results', style={'marginTop': 20})
    ])

# Callback for scraper  
#def register_scraper_callbacks(app):
@app.callback(
        Output('scraper-results', 'children'),
        [Input('scrape-latest-button', 'n_clicks'),
         Input('scrape-best-button', 'n_clicks'),
         Input('scrape-worst-button', 'n_clicks'),
         Input('scrape-positive-turn-around-button', 'n_clicks'),
         Input('scrape-negative-turn-around-button', 'n_clicks')]
    )
def trigger_scraper(latest_clicks, best_clicks, worst_clicks,positive_turnaround_clicks, negative_turnaround_clicks):
        ctx = callback_context

        if not ctx.triggered:
            return "Click a button to start scraping."
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        url_map = {
            'scrape-latest-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=LR&subType=yoy",
            'scrape-best-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=BP&subType=yoy",
            'scrape-worst-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=WP&subType=yoy",
            'scrape-positive-turn-around-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=PT&subType=yoy",
            'scrape-negative-turn-around-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=NT&subType=yoy"
        }

        url = url_map.get(button_id, None)
        if not url:
            return "Unknown button clicked."

        try:
            result = subprocess.run(['python3', './scraper/scrapedata.py', url], check=True, capture_output=True, text=True)
            return html.Div([
                html.P("Scraping started successfully!"),
                html.Pre(result.stdout)  # Display the output of the script
            ])
        except subprocess.CalledProcessError as e:
            return html.Div([
                html.P("There was an error during scraping."),
                html.Pre(e.stderr)  # Display any error messages
            ])





def community_layout():
    return html.Div([
        html.H3("Community Insights"),
        dbc.Input(id='post-input', type='text', placeholder="Share your insights..."),
        html.Br(),
        dbc.Button("Post to App", id='post-button', color="primary"),
        dbc.Button("Post to Twitter", id='twitter-post-button', color="info", style={"marginLeft": "10px"}),
        dbc.Button("Delete Last Tweet", id='twitter-delete-button', color="danger", style={"marginLeft": "10px"}),
        html.Br(),
        html.Div(id='community-feed'),
        html.Div(id='twitter-response', style={'marginTop': 20})
    ])


# Settings page layout
def settings_layout():
    return html.Div([
        html.H3("Settings"),
        dbc.Row([
            dbc.Col([
                dbc.Label("API Key"),
                dbc.Input(id='api-key-input', type='text', placeholder="Enter your API key..."),
                dbc.FormText("This key is used for fetching real-time data."),
            ])
        ]),
        dbc.Button("Save Settings", id='save-settings', color="primary"),
    ])

# Twitter API error handling decorator
def twitter_api_error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
            return response.json()
        except requests.exceptions.HTTPError as errh:
            print("Http Error:", errh)
            return {"error": str(errh)}
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
            return {"error": str(errc)}
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
            return {"error": str(errt)}
        except requests.exceptions.RequestException as err:
            print("Something went wrong", err)
            return {"error": str(err)}
    return wrapper

@twitter_api_error_handler
def tweet_post(text):
    return client.create_tweet(text=text)

@twitter_api_error_handler
def tweet_delete(tweet_id):
    return client.delete_tweet(tweet_id)


# Global variable for tracking the last tweet ID
last_tweet_id = None

#def register_twitter_callbacks(app):
@app.callback(
        Output('twitter-response', 'children'),
        [Input('twitter-post-button', 'n_clicks'),
         Input('twitter-delete-button', 'n_clicks')],
        [State('post-input', 'value')]
    )
def handle_twitter_actions(post_clicks, delete_clicks, post_content):
        global last_tweet_id  # Access the global variable
        ctx = callback_context

        if not ctx.triggered:
            return "No action taken."

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'twitter-post-button':
            if post_clicks and post_content:
                response = tweet_post(post_content)
                if 'data' in response:
                    last_tweet_id = response['data']['id']  # Store the tweet ID
                    return f"Tweet posted successfully: {last_tweet_id}"
                else:
                    return f"Failed to post tweet: {response.get('error', 'Unknown error')}"
            else:
                return "No content to post."

        elif button_id == 'twitter-delete-button':
            if delete_clicks and last_tweet_id:
                response = tweet_delete(last_tweet_id)
                if 'data' in response:
                    last_tweet_id = None  # Reset after deletion
                    return f"Tweet deleted successfully."
                else:
                    return f"Failed to delete tweet: {response.get('error', 'Unknown error')}"
            else:
                return "No tweet to delete."

        return "No action taken."
     

#def register_twitter_post_callbacks(app):
@app.callback(
        Output('twitter-share-response', 'children'),
        Input('twitter-share-button', 'n_clicks'),
        State('selected-data-store', 'data'),  # Retrieve data from dcc.Store
        State('modal-title', 'children')
    )
def post_to_twitter(n_clicks, selected_data, company_name):
        if n_clicks:
            # selected_data is directly available here as a dict
            tweet_content = format_tweet(selected_data, company_name)
            print(tweet_content)
            
            # Post to Twitter (uncomment when ready)
            response = tweet_post(tweet_content)
            
            if 'data' in response:
                last_tweet_id = response['data']['id']  # Store the tweet ID
                return f"Tweet posted successfully: {last_tweet_id}"
            else:
                return f"Failed to post tweet: {response.get('error', 'Unknown error')}"
        
        # Return an empty string if no clicks or any other issues
        return ""


    # Callback for community posts
#def register_community_callbacks(app):
@app.callback(
        Output('community-feed', 'children'),
        [Input('post-button', 'n_clicks')],
        [State('post-input', 'value')]
    )
def update_community_feed(n_clicks, post_content):
        if n_clicks is None or post_content is None:
            return html.Div("No posts yet.")
        
        # In a real application, you would store this in a database
        return html.Div([
            html.P(f"User posted: {post_content}"),
            html.Hr()
        ])


def format_tweet(selected_data, company_name):
    try:
        # Extract data directly from the dictionary
        report_type = selected_data.get('report_type', 'N/A')
        result_date = selected_data.get('result_date', 'N/A')

        # Valuation Metrics
        market_cap = selected_data.get('market_cap', 'N/A')
        ttm_pe = selected_data.get('ttm_pe', 'N/A')

        # Financial Performance
        revenue = selected_data.get('revenue', 'N/A')
        gross_profit = selected_data.get('gross_profit', 'N/A')
        revenue_growth = selected_data.get('revenue_growth', 'N/A')
        net_profit = selected_data.get('net_profit', 'N/A')

        # Insights
        net_profit_growth = selected_data.get('net_profit_growth', 'N/A')
        piotroski_score = selected_data.get('piotroski_score', 'N/A')

        # Formatting the tweet content
        tweet_content = f"""
📊  {company_name}*

📅 Report Type: {report_type}
🗓️ Result Date: {result_date}

💹 Valuation Metrics:
• Market Cap: {market_cap}
• TTM P/E: {ttm_pe}

📈 Financial Performance:
• Revenue: {revenue}
• Gross Profit: {gross_profit}
• Net Profit: {net_profit}

💡 Insights:
• Revenue Growth (YoY): {revenue_growth}
• Net Profit Growth (YoY): {net_profit_growth}
• Piotroski Score: {piotroski_score}

#StockAnalysis #Investing #FinancialPerformance #ValuationMetrics #Insights
        """

        return tweet_content.strip()
    except Exception as e:
        return f"Error formatting tweet: {str(e)}"


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
