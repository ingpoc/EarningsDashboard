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
    stocks = list(collection.find({}, {"company_name": 1, "financial_metrics": {"$slice": -1}, "_id": 0}))
    
    stock_data = [{
        "company_name": stock['company_name'],
        "result_date": pd.to_datetime(latest_metric.get("result_date", "N/A")),
        "net_profit_growth": parse_numeric_value(latest_metric.get("net_profit_growth", "0%")),
        "cmp": parse_numeric_value(latest_metric.get("cmp", "0").split()[0]),
        "quarter": latest_metric.get("quarter", "N/A"),
        "ttm_pe": parse_numeric_value(latest_metric.get("ttm_pe", "N/A")),
        "revenue": parse_numeric_value(latest_metric.get("revenue", "0")),
        "net_profit": parse_numeric_value(latest_metric.get("net_profit", "0"))
    } for stock in stocks for latest_metric in stock['financial_metrics']]
    
    df = pd.DataFrame(stock_data)

    # Ensure sorting by 'result_date' in descending order to get the latest results first
    df = df.sort_values(by="result_date", ascending=False)

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



def stock_details_layout(company_name, show_full_layout=True):
    stock = collection.find_one({"company_name": company_name}, {"financial_metrics": 1, "_id": 0})
    
    if not stock or not stock.get('financial_metrics'):
        return html.Div(["Stock not found or no data available."], className="text-danger")

    selected_data = stock['financial_metrics'][-1]
    colors = {'background': '#ffffff', 'text': '#333333', 'primary': '#003366'}

    financials_layout = create_financial_segments(selected_data, colors)
    twitter_button = dbc.Button("Share to Twitter", id="twitter-share-button", color="info", style={"marginTop": "10px"})
    twitter_share_response = html.Div(id='twitter-share-response', style={'marginTop': 20})

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
             #   dbc.Tab([html.Ul([html.Li(html.A(article['title'], href=article['url'], target="_blank")) for article in fetch_stock_news(company_name)])], label="News"),
            ]),
            html.Br(),
            dbc.Alert(id='recommendation-alert', color="info")
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
    # Query the collection using the symbol instead of the company name
    stock = collection.find_one({"symbol": symbol})
    
    if not stock or not stock.get('financial_metrics'):
        return {
            "net_profit_growth": "NA",
            "strengths": "NA",
            "weaknesses": "NA",
            "technicals_trend": "NA",
            "fundamental_insights": "NA",
            "piotroski_score": "NA"
        }

    # Get the latest financial metric based on result date
    latest_metric = max(stock['financial_metrics'], key=lambda x: pd.to_datetime(x.get("result_date", "N/A")))
    
    return {
        "net_profit_growth": latest_metric.get("net_profit_growth", "NA"),
        "strengths": latest_metric.get("strengths", "NA"),
        "weaknesses": latest_metric.get("weaknesses", "NA"),
        "technicals_trend": latest_metric.get("technicals_trend", "NA"),
        "fundamental_insights": latest_metric.get("fundamental_insights", "NA"),
        "piotroski_score": latest_metric.get("piotroski_score", "NA")
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


def overview_layout():
    df = fetch_latest_quarter_data()

    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')

    top_performers = df.sort_values(by="net_profit_growth", ascending=False).head(10)
    worst_performers = df.sort_values(by="net_profit_growth", ascending=True).head(10)
    latest_results = df.sort_values(by="result_date", ascending=False).head(10)

    def create_data_table(id, data):
        return dash_table.DataTable(
            id=id,
            columns=[
                {"name": "Company Name", "id": "company_name"},
                {"name": "Result Date", "id": "result_date_display"},
                {"name": "Net Profit Growth (%)", "id": "net_profit_growth"},
                {"name": "CMP", "id": "cmp"},
            ],
            data=data.to_dict('records'),
            sort_action="custom",
            sort_mode="multi",
            sort_by=[],
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
                }
            ],
            style_as_list_view=True,
            row_selectable='single',
            selected_rows=[],
        )

    return dbc.Container([
        # Top 10 Performers Section
        html.H4("Top 10 Performers", className="mt-4 mb-3"),
        create_data_table('top-performers-table', top_performers),
        html.Br(),

        # Worst 10 Performers Section
        html.H4("Worst 10 Performers", className="mt-4 mb-3"),
        create_data_table('worst-performers-table', worst_performers),
        html.Br(),

        # Latest 10 Results Section
        html.H4("Latest 10 Results", className="mt-4 mb-3"),
        create_data_table('latest-results-table', latest_results),
        html.Br(),

        # Stocks Overview Section
        html.H4("Stocks Overview", className="mt-4 mb-3"),
        dash_table.DataTable(
            id='stocks-table',
            columns=[
                {"name": "Company Name", "id": "company_name"},
                {"name": "CMP", "id": "cmp"},
                {"name": "P/E Ratio", "id": "ttm_pe"},
                {"name": "Revenue", "id": "revenue"},
                {"name": "Net Profit", "id": "net_profit"},
                {"name": "Net Profit Growth(%)", "id": "net_profit_growth"},
                {"name": "Result Date", "id": "result_date_display"},
            ],
            data=df.to_dict('records'),
            sort_action="custom",
            sort_mode="multi",
            sort_by=[],
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
                }
            ],
            style_as_list_view=True,
            row_selectable='single',
            selected_rows=[],
        ),
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

    # Extract numerical parts for strengths and weaknesses
    metrics['strengths'] = metrics['strengths'].str.extract(r'(\d+)').fillna('NA')
    metrics['weaknesses'] = metrics['weaknesses'].str.extract(r'(\d+)').fillna('NA')

    # Replace 'NA' with suitable default values and convert to appropriate data types
    metrics['net_profit_growth'] = metrics['net_profit_growth'].replace('NA', '0').str.replace('%', '', regex=False).str.replace(',', '', regex=False).astype(float)
    metrics['piotroski_score'] = metrics['piotroski_score'].replace('NA', '0').astype(float)

    # Combine the metrics with the original DataFrame
    df = pd.concat([df, metrics], axis=1)

    # Ensure the column name is consistent
    df.rename(columns={"net_profit_growth": "Net Profit Growth %"}, inplace=True)

    # Check if 'Net Profit Growth (Latest) %' exists now
    if 'Net Profit Growth %' not in df.columns:
        print("Column 'Net Profit Growth %' does not exist in DataFrame.")
        return html.Div("Failed to fetch necessary data.", className="text-danger")

    # Filter columns to show only relevant ones
    filtered_df = df[['Instrument', 'LTP','Cur. val', 'P&L', 'Net Profit Growth %', 'strengths', 'weaknesses', 'technicals_trend', 'fundamental_insights', 'piotroski_score']]

    # Add a recommendation column based on the new criteria
    filtered_df = filtered_df.assign(Recommendation=filtered_df.apply(get_stock_recommendation, axis=1))


    table = dash_table.DataTable(
    id='portfolio-table',  # Give the table an ID
    data=filtered_df.to_dict('records'),
    columns=[{'name': i, 'id': i} for i in filtered_df.columns],
    style_table={'overflowX': 'auto'},
    style_cell={'textAlign': 'left'},
    style_as_list_view=True,
    filter_action="native",  # Enable filtering
    sort_action="native",  # Enable sorting
    page_action="native",  # Enable pagination
    page_current=0,
    page_size=30,
    row_selectable='single',  # Enable row selection via checkboxes
    selected_rows=[],  # Initialize with no rows selected
)


    return html.Div([
        html.H3("Portfolio Management"),
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
        html.H4("Current Portfolio"),
        table
    ])

@app.callback(
    Output('stocks-table', 'data'),
    Input('stocks-table', 'sort_by')
)
def update_table(sort_by):
    df = fetch_latest_quarter_data()
    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    
    if len(sort_by):
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
