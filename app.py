import base64
import io
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from functools import lru_cache
from tabs.scraper_tab import scraper_layout, register_scraper_callbacks
from tabs.community_tab import (
    community_layout,
    settings_layout,
    register_community_callbacks,
    register_twitter_callbacks,
    register_twitter_post_callbacks  
)
from util.utils import  get_stock_recommendation, parse_numeric_value, get_recommendation  
from util.charting import create_stock_price_chart, create_financial_metrics_chart
from util.layout import app_layout  # Import the layout
from tabs.ipo_tab import ipo_layout, register_ipo_callbacks
from dash.dash_table.Format import Format, Scheme

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']
holdings_collection = db['holdings']

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Register callbacks from other files
register_community_callbacks(app)
register_twitter_callbacks(app)
register_twitter_post_callbacks(app)  
register_scraper_callbacks(app)
register_ipo_callbacks(app)  # Register IPO callbacks


app.layout = app_layout

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
    stocks = list(collection.find({}, {"company_name": 1, "symbol": 1, "financial_metrics": {"$slice": -1}, "_id": 0}))
    
    stock_data = [{
        "company_name": stock['company_name'],
        "symbol": stock['symbol'],
        "result_date": pd.to_datetime(latest_metric.get("result_date", "N/A")),
        "net_profit_growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0%")),
        "cmp": parse_numeric_value(latest_metric.get("cmp", "0").split()[0]),
        "quarter": latest_metric.get("quarter", "N/A"),
        "ttm_pe": parse_numeric_value(latest_metric.get("ttm_pe", "N/A")),
        "revenue": parse_numeric_value(latest_metric.get("revenue", "0")),
        "net_profit": parse_numeric_value(latest_metric.get("net_profit", "0")),
        "estimates": latest_metric.get("estimates", "N/A")  # Added this line
    } for stock in stocks for latest_metric in stock['financial_metrics']]
    
    df = pd.DataFrame(stock_data)

    # Ensure sorting by 'result_date' in descending order to get the latest results first
    df = df.sort_values(by="result_date", ascending=False)

    return df



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



@app.callback(
    [Output('overview-details-modal', 'is_open'),
     Output('overview-details-body', 'children'),
     Output('modal-title', 'children')],
    [Input('stocks-table', 'selected_rows'),
     Input('top-performers-table', 'selected_rows'),
     Input('worst-performers-table', 'selected_rows'),
     Input('latest-results-table', 'selected_rows')],
    [State('stocks-table', 'data'),
     State('top-performers-table', 'data'),
     State('worst-performers-table', 'data'),
     State('latest-results-table', 'data')]
)
def display_overview_details(stocks_selected, top_selected, worst_selected, latest_selected,
                             stocks_data, top_data, worst_data, latest_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", ""
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == 'stocks-table' and stocks_selected:
        row = stocks_data[stocks_selected[0]]
    elif triggered_id == 'top-performers-table' and top_selected:
        row = top_data[top_selected[0]]
    elif triggered_id == 'worst-performers-table' and worst_selected:
        row = worst_data[worst_selected[0]]
    elif triggered_id == 'latest-results-table' and latest_selected:
        row = latest_data[latest_selected[0]]
    else:
        return False, "", ""

    company_name = row['company_name']
    stock_details = stock_details_layout(company_name, show_full_layout=False)
    return True, stock_details, f"Stock Details of {company_name}"


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
    if not selected_rows:
        return False, []

    row = rows[selected_rows[0]]
    instrument_name = row['Instrument']
    stock_details = fetch_latest_metrics(instrument_name)
    holding = holdings_collection.find_one({"Instrument": instrument_name})

    # Fetch full stock details
    stock = collection.find_one({"symbol": instrument_name})
    if not stock or not stock.get('financial_metrics'):
        return False, html.Div("Stock details not found.", className="text-danger")

    selected_data = stock['financial_metrics'][-1]

    def format_estimate(estimate):
        if 'Beat' in estimate:
            return html.Span(estimate, style={'color': 'green'})
        elif 'Missed' in estimate:
            return html.Span(estimate, style={'color': 'red'})
        else:
            return estimate

    cards = [
        ("Basic Information", [
            f"Instrument: {instrument_name}",
            f"Quantity: {holding.get('Qty.', 'N/A')}",
            f"Avg Cost: {holding.get('Avg. cost', 'N/A')}",
            f"Current Value: {holding.get('Cur. val', 'N/A')}",
            f"P&L: {holding.get('P&L', 'N/A')}",
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
            f"Net Profit: {selected_data.get('net_profit', 'N/A')}",
            f"Net Profit Growth: {stock_details.get('net_profit_growth', 'N/A')}"
        ]),
        ("Insights", [
            f"Strengths: {stock_details.get('strengths', 'N/A')}",
            f"Weaknesses: {stock_details.get('weaknesses', 'N/A')}",
            f"Technicals Trend: {stock_details.get('technicals_trend', 'N/A')}",
            f"Fundamental Insights: {stock_details.get('fundamental_insights', 'N/A')}",
            f"Piotroski Score: {stock_details.get('piotroski_score', 'N/A')}",
            html.Span(["Estimates: ", format_estimate(selected_data.get('estimates', 'N/A'))])
        ])
    ]

    details_content = dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5(title, className="mb-0")),
                dbc.CardBody([html.P(item, className="mb-1") for item in items])
            ], className="mb-3 shadow-sm"), width=6) 
            for title, items in cards
        ])
    ], fluid=True)

    return True, details_content

def fetch_latest_metrics(symbol):
    stock = collection.find_one({"symbol": symbol})
    
    if not stock or not stock.get('financial_metrics'):
        return {
            "net_profit_growth": "0",
            "strengths": "0",
            "weaknesses": "0",
            "technicals_trend": "NA",
            "fundamental_insights": "NA",
            "piotroski_score": "0"
        }

    latest_metric = max(stock['financial_metrics'], key=lambda x: pd.to_datetime(x.get("result_date", "N/A")))
    
    return {
        "net_profit_growth": latest_metric.get("net_profit_growth", "0"),
        "strengths": latest_metric.get("strengths", "0"),
        "weaknesses": latest_metric.get("weaknesses", "0"),
        "technicals_trend": latest_metric.get("technicals_trend", "NA"),
        "fundamental_insights": latest_metric.get("fundamental_insights", "NA"),
        "piotroski_score": latest_metric.get("piotroski_score", "0")
    }

# Callback to update page content
# Callback to update page content
@app.callback(
    dash.dependencies.Output('page-content', 'children'),
    [dash.dependencies.Input('url', 'pathname')]
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
    elif pathname == "/ipos":
        return ipo_layout()  # This should now include the 'refresh-ipo-data' button
    elif pathname == "/settings":
        return settings_layout()
    return html.Div(["404 - Page not found"], className="text-danger")


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

def overview_layout():
    df = fetch_latest_quarter_data()

    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    df['processed_estimates'] = df['estimates'].apply(process_estimates)

    top_performers = df.sort_values(by="net_profit_growth", ascending=False).head(10)
    worst_performers = df.sort_values(by="net_profit_growth", ascending=True).head(10)
    latest_results = df.sort_values(by="result_date", ascending=False).head(10)

    def create_data_table(id, data):
        return dash_table.DataTable(
            id=id,
            columns=[
                {"name": "Company Name", "id": "company_name"},
                {"name": "Result Date", "id": "result_date_display"},
                {"name": "Net Profit Growth (%)", "id": "net_profit_growth", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                {"name": "CMP", "id": "cmp", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                {"name": "Estimates (%)", "id": "processed_estimates", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            ],
            data=data.to_dict('records'),
            sort_action="native",
            sort_mode="single",
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                },
                {
                    'if': {
                        'filter_query': '{processed_estimates} < 0',
                        'column_id': 'processed_estimates'
                    },
                    'color': 'red'
                },
                {
                    'if': {
                        'filter_query': '{processed_estimates} > 0',
                        'column_id': 'processed_estimates'
                    },
                    'color': 'green'
                }
            ],
            style_as_list_view=True,
            row_selectable='single',
            selected_rows=[],
        )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4("Top 10 Performers", className="mt-4 mb-3"),
                create_data_table('top-performers-table', top_performers),
            ], md=12),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col([
                html.H4("Worst 10 Performers", className="mt-4 mb-3"),
                create_data_table('worst-performers-table', worst_performers),
            ], md=12),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col([
                html.H4("Latest 10 Results", className="mt-4 mb-3"),
                create_data_table('latest-results-table', latest_results),
            ], md=12),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col([
                html.H4("Stocks Overview", className="mt-4 mb-3"),
                dash_table.DataTable(
                id='stocks-table',
                columns=[
                    {"name": "Company Name", "id": "company_name"},
                    {"name": "CMP", "id": "cmp", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                    {"name": "P/E Ratio", "id": "ttm_pe", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                    {"name": "Revenue", "id": "revenue", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
                    {"name": "Net Profit", "id": "net_profit", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
                    {"name": "Net Profit Growth(%)", "id": "net_profit_growth", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                    {"name": "Result Date", "id": "result_date_display"},
                    {"name": "Estimates (%)", "id": "processed_estimates", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
                ],
                    data=df.to_dict('records'),
                    sort_action="native",
                    filter_action="native",
                    page_action="native",
                    page_current=0,
                    page_size=22,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {
                                'filter_query': '{processed_estimates} < 0',
                                'column_id': 'processed_estimates'
                            },
                            'color': 'red'
                        },
                        {
                            'if': {
                                'filter_query': '{processed_estimates} > 0',
                                'column_id': 'processed_estimates'
                            },
                            'color': 'green'
                        }
                    ],
                    style_as_list_view=True,
                    row_selectable='single',
                    selected_rows=[],
                ),
            ], md=12),
        ]),
    ])

# Portfolio page layout
def portfolio_layout():
    # Fetch the data from holdings_collection
    holdings_data = list(holdings_collection.find())

    if not holdings_data:
        return html.Div("No portfolio data available.", className="text-danger")

    # Convert the holdings data to a DataFrame
    df = pd.DataFrame(holdings_data)

    # Fetch all the required metrics for each instrument
    metrics = df['Instrument'].apply(fetch_latest_metrics).apply(pd.Series)

    # Function to extract numeric value from strengths and weaknesses
    def extract_numeric(value):
        if pd.isna(value) or value == 'NA':
            return 0
        try:
            return int(''.join(filter(str.isdigit, str(value))))
        except ValueError:
            return 0

    # Convert strengths and weaknesses to numeric
    metrics['strengths'] = metrics['strengths'].apply(extract_numeric)
    metrics['weaknesses'] = metrics['weaknesses'].apply(extract_numeric)

    # Replace 'NA' with suitable default values and convert to appropriate data types
    metrics['net_profit_growth'] = metrics['net_profit_growth'].replace('NA', '0').str.replace('%', '', regex=False).str.replace(',', '', regex=False).astype(float)
    metrics['piotroski_score'] = metrics['piotroski_score'].replace('NA', '0').astype(float)

    # Combine the metrics with the original DataFrame
    df = pd.concat([df, metrics], axis=1)

    # Ensure the column name is consistent
    df.rename(columns={"net_profit_growth": "Net Profit Growth %"}, inplace=True)

    # Fetch estimates data
    estimates_data = fetch_latest_quarter_data()
    estimates_dict = dict(zip(estimates_data['symbol'], estimates_data['estimates']))
    df['Estimates'] = df['Instrument'].map(estimates_dict)
    df['Estimates (%)'] = df['Estimates'].apply(process_estimates)

    # Filter columns to show only relevant ones
    filtered_df = df[['Instrument', 'LTP', 'P&L', 'Net Profit Growth %', 'strengths', 'weaknesses', 'technicals_trend', 'fundamental_insights', 'piotroski_score', 'Estimates (%)']]

    # Add a recommendation column based on the criteria
    filtered_df = filtered_df.assign(Recommendation=filtered_df.apply(get_stock_recommendation, axis=1))

    table = dash_table.DataTable(
        id='portfolio-table',
        data=filtered_df.to_dict('records'),
        columns=[
            {"name": i, "id": i, "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)} 
            if i in ['LTP', 'P&L', 'Net Profit Growth %', 'piotroski_score', 'Estimates (%)'] 
            else {"name": i, "id": i, "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)} 
            if i in ['strengths', 'weaknesses']
            else {"name": i, "id": i}
            for i in filtered_df.columns
        ],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_as_list_view=True,
        filter_action="native",
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=30,
        row_selectable='single',
        selected_rows=[],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Estimates (%)} < 0',
                    'column_id': 'Estimates (%)'
                },
                'color': 'red'
            },
            {
                'if': {
                    'filter_query': '{Estimates (%)} > 0',
                    'column_id': 'Estimates (%)'
                },
                'color': 'green'
            },
            {
                'if': {'column_id': 'technicals_trend'},
                'backgroundColor': 'rgba(0, 0, 255, 0.1)'  # Light blue background for technicals_trend
            },
            {
                'if': {'column_id': 'Recommendation'},
                'backgroundColor': 'rgba(0, 255, 0, 0.1)'  # Light green background for Recommendation
            }
        ]
    )

    return html.Div([
        html.H3("Portfolio Management", className="mb-4"),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload'),
        html.Br(),
        html.H4("Current Portfolio", className="mb-3"),
        table,
        html.Div(id="portfolio-summary", className="mt-4")
    ])


@app.callback(
    Output('stocks-table', 'data'),
    Input('stocks-table', 'sort_by')
)
def update_table(sort_by):
    df = fetch_latest_quarter_data()
    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    
    if sort_by and len(sort_by):
        col = sort_by[0]['column_id']
        if col == 'result_date_display':
            col = 'result_date'
        df = df.sort_values(
            col,
            ascending=sort_by[0]['direction'] == 'asc',
            inplace=False
        )
    
    return df.to_dict('records')


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

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
