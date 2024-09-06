import base64
from functools import lru_cache
import io
import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html
from util.utils import fetch_latest_quarter_data, process_estimates, get_stock_recommendation, fetch_latest_metrics, extract_numeric
from dash import dcc, html, dash_table, callback_context
from dash.dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output, State


# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']
holdings_collection = db['holdings']

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


#portfolio



def register_portfolio_callback(app):
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