#tabs/portfolio_tab.py
import base64
from functools import lru_cache
import io
import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme
from util.utils import fetch_latest_quarter_data, process_estimates, get_stock_recommendation, fetch_latest_metrics, extract_numeric
from util.stock_utils import create_info_card

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['stock_data']
collection = db['detailed_financials']
holdings_collection = db['holdings']

def portfolio_layout():
    holdings_data = list(holdings_collection.find())

    if not holdings_data:
        return html.Div("No portfolio data available.", className="text-danger")

    df = pd.DataFrame(holdings_data)
    metrics = df['Instrument'].apply(fetch_latest_metrics).apply(pd.Series)
    
    metrics['strengths'] = metrics['strengths'].apply(extract_numeric)
    metrics['weaknesses'] = metrics['weaknesses'].apply(extract_numeric)
    metrics['net_profit_growth'] = metrics['net_profit_growth'].replace('NA', '0').str.replace('%', '', regex=False).str.replace(',', '', regex=False).astype(float)
    metrics['piotroski_score'] = metrics['piotroski_score'].replace('NA', '0').astype(float)

    df = pd.concat([df, metrics], axis=1)
    df.rename(columns={"net_profit_growth": "Net Profit Growth %"}, inplace=True)

    estimates_data = fetch_latest_quarter_data()
    estimates_dict = dict(zip(estimates_data['symbol'], estimates_data['estimates']))
    df['Estimates'] = df['Instrument'].map(estimates_dict)
    df['Estimates (%)'] = df['Estimates'].apply(process_estimates)

    filtered_df = df[['Instrument', 'LTP', 'P&L', 'Net Profit Growth %', 'strengths', 'weaknesses', 'technicals_trend', 'fundamental_insights', 'piotroski_score', 'Estimates (%)']]
    filtered_df = filtered_df.assign(Recommendation=filtered_df.apply(get_stock_recommendation, axis=1))

    content = html.Div([
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
        create_portfolio_table(filtered_df),
        html.Div(id="portfolio-summary", className="mt-4")
    ])

    return dbc.Container(content, fluid=True, className="py-3")

def create_portfolio_table(df):
    return dash_table.DataTable(
        id='portfolio-table',
        columns=[
            {"name": i, "id": i, "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)} 
            if i in ['LTP', 'P&L', 'Net Profit Growth %', 'piotroski_score', 'Estimates (%)'] 
            else {"name": i, "id": i, "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)} 
            if i in ['strengths', 'weaknesses']
            else {"name": i, "id": i}
            for i in df.columns
        ],
        data=df.to_dict('records'),
        editable=False,
        filter_action="native",
        style_as_list_view=True,
        sort_action="native",
        sort_mode="single",
        row_selectable="single",
        row_deletable=False,
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=15,
        style_table={'overflowX': 'auto'},
        style_cell={
            'fontSize': '14px',
            'padding': '12px',
            'textAlign': 'left',
        },
        style_header={
            'backgroundColor': '#2c3e50',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'padding': '12px',
            'height': 'auto',
        },
        style_data={
            'whiteSpace': 'normal',
            'height': 'auto',
            'lineHeight': '15px'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            },
            {
                'if': {
                    'filter_query': '{P&L} > 0',
                    'column_id': 'P&L'
                },
                'color': '#28a745',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{P&L} < 0',
                    'column_id': 'P&L'
                },
                'color': '#dc3545',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{Net Profit Growth %} > 0',
                    'column_id': 'Net Profit Growth %'
                },
                'color': '#28a745',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{Net Profit Growth %} < 0',
                    'column_id': 'Net Profit Growth %'
                },
                'color': '#dc3545',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{Estimates (%)} > 0',
                    'column_id': 'Estimates (%)'
                },
                'color': '#28a745',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{Estimates (%)} < 0',
                    'column_id': 'Estimates (%)'
                },
                'color': '#dc3545',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'technicals_trend'},
                'backgroundColor': 'rgba(0, 0, 255, 0.1)'
            },
            {
                'if': {'column_id': 'Recommendation'},
                'backgroundColor': 'rgba(0, 255, 0, 0.1)'
            }
        ],
    )

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

        modal_content = dbc.Container([
            dbc.Row([
                dbc.Col(create_info_card("Basic Information", [
                    ("Instrument", instrument_name),
                    ("Quantity", holding.get('Qty.', 'N/A')),
                    ("Avg Cost", f"₹{holding.get('Avg. cost', 'N/A')}"),
                    ("Current Value", f"₹{holding.get('Cur. val', 'N/A')}"),
                    ("P&L", f"₹{holding.get('P&L', 'N/A')}"),
                    ("CMP", stock_details.get('cmp', 'N/A')),
                    ("Report Type", stock_details.get('report_type', 'N/A')),
                    ("Result Date", stock_details.get('result_date', 'N/A'))
                ], "fa-info-circle"), width=6),
                dbc.Col(create_info_card("Valuation Metrics", [
                    ("Market Cap", stock_details.get('market_cap', 'N/A')),
                    ("Face Value", stock_details.get('face_value', 'N/A')),
                    ("Book Value", stock_details.get('book_value', 'N/A')),
                    ("Dividend Yield", stock_details.get('dividend_yield', 'N/A')),
                    ("TTM EPS", stock_details.get('ttm_eps', 'N/A')),
                    ("TTM P/E", stock_details.get('ttm_pe', 'N/A')),
                    ("P/B Ratio", stock_details.get('pb_ratio', 'N/A')),
                    ("Sector P/E", stock_details.get('sector_pe', 'N/A'))
                ], "fa-chart-line"), width=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(create_info_card("Financial Performance", [
                    ("Revenue", stock_details.get('revenue', 'N/A')),
                    ("Gross Profit", stock_details.get('gross_profit', 'N/A')),
                    ("Gross Profit Growth", stock_details.get('gross_profit_growth', 'N/A')),
                    ("Revenue Growth", stock_details.get('revenue_growth', 'N/A')),
                    ("Net Profit", stock_details.get('net_profit', 'N/A'))
                ], "fa-money-bill-wave"), width=6),
                dbc.Col(create_info_card("Insights", [
                    ("Strengths", stock_details.get('strengths', 'N/A')),
                    ("Weaknesses", stock_details.get('weaknesses', 'N/A')),
                    ("Technicals Trend", stock_details.get('technicals_trend', 'N/A')),
                    ("Fundamental Insights", stock_details.get('fundamental_insights', 'N/A')),
                    ("Net Profit Growth", stock_details.get('net_profit_growth', 'N/A')),
                    ("Piotroski Score", stock_details.get('piotroski_score', 'N/A')),
                    ("Estimates", stock_details.get('estimates', 'N/A'))
                ], "fa-lightbulb"), width=6),
            ]),
        ])

        return True, modal_content

    @app.callback(
        Output('output-data-upload', 'children'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename')
    )
    def update_output(contents, filename):
        if contents is None:
            return html.Div()

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

            return html.Div([
                html.H5("Uploaded Portfolio Data", className="mt-4 mb-3"),
                create_portfolio_table(filtered_df)
            ])

        except Exception as e:
            return html.Div([f'There was an error processing this file: {str(e)}'], className="text-danger")

 