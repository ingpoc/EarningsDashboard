import base64
import io
import pandas as pd
from pymongo import MongoClient
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme
from util.recommendation import generate_stock_recommendation
from util.stock_utils import create_info_card
from util.database import DatabaseConnection as db
from util.stock_utils import fetch_latest_metrics
from util.general_util import extract_numeric




def portfolio_layout():
    holdings_data = list(db.get_collection('holdings').find())

    content = html.Div([
        html.H3("Portfolio Management", className="mb-4"),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files', href='#')
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
        html.Div(id='portfolio-table-container'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="details-modal-title")),
            dbc.ModalBody(id="details-body"),
        ], id="details-modal", size="lg", scrollable=True),
    ])

    return dbc.Container(content, fluid=True, className="py-3")

def create_portfolio_table(df):
    return dash_table.DataTable(
        id='portfolio-table',
        columns=[
            {"name": i, "id": i, "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)}
            if i in ['LTP', 'P&L', 'Net Profit Growth %', 'piotroski_score', 'Estimates (%)']
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
            },
            {
                'if': {
                    'filter_query': '{P&L} > 0',
                    'column_id': 'P&L'
                },
                'fontWeight': 'bold',
                'className': 'positive-value',
            },
            {
                'if': {
                    'filter_query': '{P&L} < 0',
                    'column_id': 'P&L'
                },
                'fontWeight': 'bold',
                'className': 'negative-value',
            },
            {
                'if': {
                    'filter_query': '{Estimates (%)} < 0',
                    'column_id': 'Estimates (%)'
                },
                'color': '#dc3545',  # Red color
            },
            {
                'if': {
                    'filter_query': '{Estimates (%)} > 0',
                    'column_id': 'Estimates (%)'
                },
                'color': '#28a745',  # Green color
            },
            {
                'if': {'column_id': 'strengths'},
                'color': '#28a745',  # Green color
                'fontWeight': 'bold',
            },
            {
                'if': {'column_id': 'weaknesses'},
                'color': '#dc3545',  # Red color
                'fontWeight': 'bold',
            },
        ],
    )

def register_portfolio_callback(app):
    @app.callback(
        Output('details-modal', 'is_open'),
        Output('details-body', 'children'),
        Output('details-modal-title', 'children'),
        [Input('portfolio-table', 'selected_rows')],
        [State('portfolio-table', 'data')]
    )
    def display_details(selected_rows, rows):
        if not selected_rows:
            return False, [], ""

        row = rows[selected_rows[0]]
        instrument_name = row['Instrument']
        stock_details = fetch_latest_metrics(instrument_name)
        holding = db.get_collection('holdings').find_one({"Instrument": instrument_name})

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

        modal_title = f"Details for {instrument_name}"

        return True, modal_content, modal_title

    @app.callback(
        Output('portfolio-table-container', 'children'),
        [Input('output-data-upload', 'children'),
         Input('upload-data', 'contents'),
         Input('upload-data', 'filename')]
    )
    def update_portfolio_table(output_upload, contents, filename):
        holdings_data = list(db.get_collection('holdings').find())

        if not holdings_data:
            return html.Div("No portfolio data available.", className="text-danger")
            
        # Convert holdings data to DataFrame
        df = pd.DataFrame(holdings_data)
        
        # Create a list to store metrics for each instrument
        metrics_list = []
        for instrument in df['Instrument']:
            metrics = fetch_latest_metrics(instrument)
            metrics_list.append(metrics)
        
        # Convert metrics list to DataFrame
        metrics = pd.DataFrame(metrics_list)

        # Rest of the function remains the same...
        # Define placeholders to replace
        placeholders = ['NA', '--', 'N/A', '']

        # List of required fields
        required_fields = [
            'strengths', 'weaknesses', 'net_profit_growth',
            'net_profit_growth_3yr_cagr', 'revenue_growth',
            'revenue_growth_3yr_cagr', 'piotroski_score',
            'ttm_pe', 'dividend_yield', 'estimates', 'technicals_trend', 'fundamental_insights'
        ]

        # Ensure all required fields are present
        for field in required_fields:
            if field not in metrics.columns:
                if field == 'dividend_yield':
                    metrics[field] = '0%'
                elif field in ['technicals_trend', 'fundamental_insights']:
                    metrics[field] = 'Neutral'
                else:
                    metrics[field] = '0'

        # Process and clean data

        # Clean 'strengths' and 'weaknesses'
        metrics['strengths'] = metrics['strengths'].apply(extract_numeric)
        metrics['weaknesses'] = metrics['weaknesses'].apply(extract_numeric)

        # Clean 'net_profit_growth'
        metrics['net_profit_growth'] = metrics['net_profit_growth'].replace(placeholders, '0') \
                                                                .str.replace('%', '', regex=False) \
                                                                .str.replace(',', '', regex=False) \
                                                                .astype(float)

        # Clean 'net_profit_growth_3yr_cagr'
        metrics['net_profit_growth_3yr_cagr'] = metrics['net_profit_growth_3yr_cagr'].replace(placeholders, '0') \
                                                                            .str.replace('%', '', regex=False) \
                                                                            .str.replace(',', '', regex=False) \
                                                                            .astype(float)

        # Clean 'revenue_growth'
        metrics['revenue_growth'] = metrics['revenue_growth'].replace(placeholders, '0') \
                                                    .str.replace('%', '', regex=False) \
                                                    .str.replace(',', '', regex=False) \
                                                    .astype(float)

        # Clean 'revenue_growth_3yr_cagr'
        metrics['revenue_growth_3yr_cagr'] = metrics['revenue_growth_3yr_cagr'].replace(placeholders, '0') \
                                                            .str.replace('%', '', regex=False) \
                                                            .str.replace(',', '', regex=False) \
                                                            .astype(float)

        # Clean 'piotroski_score' and ensure it's integer
        metrics['piotroski_score'] = metrics['piotroski_score'].replace(placeholders, '0') \
                                                            .fillna('0') \
                                                            .astype(int)

        # Clean 'ttm_pe'
        metrics['ttm_pe'] = metrics['ttm_pe'].replace(placeholders, '0') \
                                            .str.replace(',', '', regex=False) \
                                            .astype(float)

        # Clean 'dividend_yield'
        metrics['dividend_yield'] = metrics['dividend_yield'].replace(placeholders, '0') \
                                                            .str.replace('%', '', regex=False) \
                                                            .str.replace(',', '', regex=False) \
                                                            .astype(float)

        # Clean 'technicals_trend'
        metrics['technicals_trend'] = metrics['technicals_trend'].replace(placeholders, 'Neutral') \
                                                              .fillna('Neutral') \
                                                              .astype(str)

        # Clean 'fundamental_insights'
        metrics['fundamental_insights'] = metrics['fundamental_insights'].replace(placeholders, 'Neutral') \
                                                                  .fillna('Neutral') \
                                                                  .astype(str)

        # Clean 'estimates' - Keep as string for pattern matching
        metrics['estimates'] = metrics['estimates'].replace(placeholders, '0') \
                                            .str.extract(r'([-+]?\d*\.?\d+)', expand=False) \
                                            .astype(float)

        # Concatenate df and metrics
        df = pd.concat([df, metrics], axis=1)

        # Rename columns for display
        df.rename(columns={
            'net_profit_growth': 'Net Profit Growth %',
            'ttm_pe': 'TTM P/E',
            'estimates': 'Estimates (%)'
        }, inplace=True)

        # Prepare data for display (including 'TTM P/E')
        filtered_df = df[['Instrument', 'LTP', 'P&L', 'TTM P/E', 'Net Profit Growth %', 
                         'strengths', 'weaknesses', 'technicals_trend', 
                         'fundamental_insights', 'piotroski_score', 'Estimates (%)',
                          'dividend_yield', 'pb_ratio', 'sector_pe', 'revenue_growth',
                          'face_value', 'book_value', 'ttm_eps']]

        # Apply the consolidated recommendation function
        filtered_df = filtered_df.assign(Recommendation=filtered_df.apply(generate_stock_recommendation, axis=1))

        # Drop 'TTM P/E' 'dividend_yield', 'pb_ratio', 'sector_pe', 'revenue_growth','face_value', 'book_value', 'ttm_eps' from the display DataFrame
        display_df = filtered_df.drop(columns=['TTM P/E', 'dividend_yield', 'pb_ratio', 'sector_pe', 'revenue_growth', 'face_value', 'book_value', 'ttm_eps'])
        

        return create_portfolio_table(display_df)


    @app.callback(
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
    def handle_file_upload(contents, filename):
        if contents is None:
            return html.Div()

        # Clear existing holdings in the collection
        db.get_collection('holdings').delete_many({})

        # Split the contents to separate the content type from the actual data
        content_type, content_string = contents.split(',')

        # Decode the base64 content
        decoded = base64.b64decode(content_string)
        try:
            # Read the file based on its extension
            if 'csv' in filename.lower():
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            else:
                df = pd.read_excel(io.BytesIO(decoded))
            
            # Check if 'Instrument' column exists
            if 'Instrument' in df.columns:
                # Remove '-BE' suffix from Instrument names if present
                df['Instrument'] = df['Instrument'].astype(str).str.replace(r'-BE$', '', regex=True)
            else:
                return html.Div("Error: 'Instrument' column not found in the uploaded file.", className="text-danger")
            
            # Optionally, you can perform additional data cleaning or validation here

            # Convert DataFrame to dictionary records and insert into MongoDB
            db.get_collection('holdings').insert_many(df.to_dict("records"))
            return html.Div("Portfolio uploaded successfully!", className="text-success")
        except Exception as e:
            # Handle exceptions and provide feedback
            return html.Div([f'There was an error processing this file: {str(e)}'], className="text-danger")
