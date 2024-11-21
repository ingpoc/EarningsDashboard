# overview_tab.py

import threading
import time
from datetime import datetime, timedelta
from functools import lru_cache
from bson import ObjectId
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dash_table.Format import Format, Scheme
from util.utils import (
    fetch_latest_quarter_data
)
from util.analysis import fetch_stock_analysis
from util.recommendation import generate_stock_recommendation
from tabs.stock_details_tab import stock_details_layout
from util.layout import ai_recommendation_modal
from util.general_util import process_estimates
from util.ai_recommendation import  get_previous_analyses
from util.database import DatabaseConnection as db

# Cache the processed data
@lru_cache(maxsize=1)
def get_cached_data():
    df = fetch_latest_quarter_data()
    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    df['processed_estimates'] = df['estimates'].apply(process_estimates)
    df['recommendation'] = df.apply(generate_stock_recommendation, axis=1)
    return df

def overview_layout():
    # Initial loading with cached data
    df = get_cached_data()
    unique_quarters = sorted(df['quarter'].unique(), reverse=True)
    latest_quarter = unique_quarters[0] if unique_quarters else None

    return dbc.Container([
        dcc.Store(id='overview-data-store'),
        dcc.Interval(
            id='overview-refresh-interval',
            interval=300_000,  # Refresh every 5 minutes
            n_intervals=0
        ),
        html.H2("Market Overview", className="text-center mb-4"),
        dcc.Dropdown(
            id='quarter-dropdown',
            options=[{'label': quarter, 'value': quarter} for quarter in unique_quarters],
            value=latest_quarter,  # Set the default value to the latest quarter
            placeholder="Select a quarter",
            className="mb-4"
        ),
        dbc.Button("Refresh AI Analysis for All Stocks", id="batch-ai-refresh-button", color="primary", className="mb-4"),
        html.Div(id='batch-ai-feedback', className="mb-4"),
        # Add the new Store component
        dcc.Store(id='batch-data-update-timestamp'),
        dbc.Tabs([
            dbc.Tab(label="Top Performers", children=[
                create_data_card("Top 10 Performers", 'top-performers-table', df)
            ]),
            dbc.Tab(label="Worst Performers", children=[
                create_data_card("Worst 10 Performers", 'worst-performers-table', df)
            ]),
            dbc.Tab(label="Latest Results", children=[
                create_data_card("Latest 10 Results", 'latest-results-table', df)
            ]),
            dbc.Tab(label="All Stocks", children=[
                create_data_card("Stocks Overview", 'stocks-table', df)
            ]),
        ], className="mb-4"),
        
        # Include the AI Recommendation Modal
        ai_recommendation_modal,
        
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="overview-modal-title", className="text-primary")),
            dbc.ModalBody(id="overview-details-body"),
        ], id="overview-details-modal", size="lg", scrollable=True),

        # Add this line to include the store
        dcc.Store(id='data-update-timestamp'),

    ], fluid=True)

def create_data_card(title, table_id, data):
    return dbc.Card([
        dbc.CardHeader(html.H4(title, className="mb-0")),
        dbc.CardBody([
            create_data_table(table_id, data)
        ])
    ], className="mb-4 shadow")

def create_data_table(id, data):
    return dash_table.DataTable(
        id=id,
        columns=[
            {"name": "Company Name", "id": "company_name_with_indicator", "presentation": "markdown"},
            {"name": "CMP", "id": "cmp", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},    
            {"name": "Net Profit Growth(%)", "id": "net_profit_growth", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            {"name": "Strengths", "id": "strengths", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Weaknesses", "id": "weaknesses", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Piotroski Score", "id": "piotroski_score", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Estimates (%)", "id": "processed_estimates", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            {"name": "Result Date", "id": "result_date_display"},
            {"name": "Recommendation", "id": "recommendation"},
            {"name": "AI", "id": "ai_indicator", "presentation": "markdown"},
        ],
        data=data.to_dict('records'),
        markdown_options={"html": True},
        style_table={
            'overflowX': 'auto',
            'overflowY': 'hidden',
            'minWidth': '100%',
            'width': '100%',
        },
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontSize': '14px',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'fontFamily': '"Segoe UI", Arial, sans-serif',
            # Removed 'color' and 'backgroundColor' properties
        },
        style_header={
            'fontWeight': 'bold',
            'fontSize': '15px',
            'border': '1px solid #dee2e6',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            # Removed 'backgroundColor' and 'color' properties
        },
        style_data={
            # Removed 'border', 'color', and 'backgroundColor' properties
        },
        style_cell_conditional=[
            {'if': {'column_id': 'company_name_with_indicator'}, 'minWidth': '150px', 'maxWidth': '200px'},
            {'if': {'column_id': 'cmp'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'net_profit_growth'}, 'minWidth': '100px', 'maxWidth': '150px'},
            {'if': {'column_id': 'strengths'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'weaknesses'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'result_date_display'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'processed_estimates'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'piotroski_score'}, 'minWidth': '80px', 'maxWidth': '120px'},
            {'if': {'column_id': 'recommendation'}, 'minWidth': '130px', 'maxWidth': '150px'},
            {'if': {'column_id': 'ai_indicator'}, 'textAlign': 'center', 'minWidth': '100px', 'maxWidth': '150px'},
        ],
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                # Removed 'backgroundColor'
            },
            {
                'if': {
                    'filter_query': '{processed_estimates} < 0',
                    'column_id': 'processed_estimates',
                },
                'className': 'negative-value',  # Use CSS class
            },
            {
                'if': {
                    'filter_query': '{processed_estimates} > 0',
                    'column_id': 'processed_estimates',
                },
                'className': 'positive-value',  # Use CSS class
            },
            {
                'if': {'column_id': 'strengths'},
                'color': '#28a745',
                'fontWeight': 'bold',
            },
            {
                'if': {'column_id': 'weaknesses'},
                'color': '#dc3545',
                'fontWeight': 'bold',
            },
            {
                'if': {
                    'filter_query': '{processed_estimates} > 0',
                    'column_id': 'processed_estimates',
                },
                'color': '#28a745',
            },
            {
                'if': {
                    'filter_query': '{processed_estimates} < 0',
                    'column_id': 'processed_estimates',
                },
                'color': '#dc3545',
            },
            # ...other conditional styles without hardcoded colors...
        ],
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        style_as_list_view=True,
        row_selectable='single',
        selected_rows=[],
        page_action='native',
        page_size=25,
        page_current=0,
        cell_selectable=True,  # Enable cell selection
    )

def register_overview_callbacks(app):
    @app.callback(
        [Output('overview-details-modal', 'is_open'),
         Output('overview-details-body', 'children'),
         Output('overview-modal-title', 'children')],
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
        return True, stock_details, f"Stock Details: {company_name}"
    
    @app.callback(
        [Output('top-performers-table', 'data'),
         Output('worst-performers-table', 'data'),
         Output('latest-results-table', 'data'),
         Output('stocks-table', 'data')],
        [Input('quarter-dropdown', 'value'),
         Input('data-update-timestamp', 'data'),
         Input('batch-data-update-timestamp', 'data'),
         Input('overview-data-store', 'data')]
    )
    def update_tables(selected_quarter, data_update_timestamp, 
                     batch_data_update_timestamp, overview_data):
        try:
            ctx = dash.callback_context
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

            # If triggered by overview data store, use that data
            if triggered_id == 'overview-data-store' and overview_data:
                df = pd.DataFrame(overview_data)
            else:
                # Otherwise fetch and process new data
                df = get_cached_data()
                if selected_quarter:
                    df = df[df['quarter'] == selected_quarter]

            # Ensure result_date is datetime and handle any conversion errors
            df['result_date'] = pd.to_datetime(df['result_date'], errors='coerce')
            
            # Handle any missing values
            df['net_profit_growth'] = pd.to_numeric(df['net_profit_growth'], errors='coerce').fillna(0)
            
            # Calculate tables
            top_performers = df.nlargest(10, 'net_profit_growth')
            worst_performers = df.nsmallest(10, 'net_profit_growth')
            latest_results = df.sort_values('result_date', ascending=False).head(10)
            
            return (
                top_performers.to_dict('records'),
                worst_performers.to_dict('records'),
                latest_results.to_dict('records'),
                df.to_dict('records')
            )
        except Exception as e:
            print(f"Error updating tables: {str(e)}")
            # Return empty data if there's an error
            empty_data = {'records': []}
            return empty_data, empty_data, empty_data, empty_data

    # Combined callback for opening and closing the AI Recommendation Modal
    @app.callback(
        [
            Output('ai-recommendation-modal', 'is_open'),
            Output('selected-stock-symbol', 'data'),
            Output('selected-stock-name', 'data'),
            Output('analysis-history-dropdown', 'options'),
            Output('analysis-history-dropdown', 'value'),
            Output('ai-recommendation-content', 'children'),
            Output('data-update-timestamp', 'data')
        ],
        [
            Input('stocks-table', 'active_cell'),
            Input('top-performers-table', 'active_cell'),
            Input('worst-performers-table', 'active_cell'),
            Input('latest-results-table', 'active_cell'),
            Input('close-ai-modal', 'n_clicks'),
            Input('analysis-history-dropdown', 'value'),
            Input('refresh-analysis-button', 'n_clicks')
        ],
        [
            State('ai-recommendation-modal', 'is_open'),
            State('stocks-table', 'derived_viewport_data'),
            State('top-performers-table', 'derived_viewport_data'),
            State('worst-performers-table', 'derived_viewport_data'),
            State('latest-results-table', 'derived_viewport_data'),
            State('selected-stock-name', 'data'),
            State('selected-stock-symbol', 'data'),
            State('analysis-history-dropdown', 'options')
        ],
        prevent_initial_call=True
    )
    def handle_ai_recommendation(
        stocks_active_cell, top_active_cell, worst_active_cell,
        latest_active_cell, close_n_clicks, selected_analysis_id,
        refresh_n_clicks, is_open, stocks_data, top_data, worst_data,
        latest_data, stock_name, stock_symbol, existing_options
    ):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Handle close button
        if triggered_id == 'close-ai-modal':
            return handle_close_modal()

        # Handle analysis history selection
        if triggered_id == 'analysis-history-dropdown' and selected_analysis_id:
            return handle_analysis_history_selection(is_open, stock_symbol, stock_name, existing_options, selected_analysis_id)

        # Handle refresh analysis
        if triggered_id == 'refresh-analysis-button' and refresh_n_clicks:
            return handle_refresh_analysis(stock_name, stock_symbol, existing_options)

            # Store new analysis
            analysis_doc = {
                'company_name': stock_name,
                'symbol': stock_symbol,
                'analysis': new_analysis_text,
                'timestamp': datetime.now(),
            }
            get_collection('ai_analysis').insert_one(analysis_doc)

            # Update options with the new analysis
            analyses = get_previous_analyses(stock_symbol)
            options = [{'label': format_label(a['timestamp']), 'value': str(a['_id'])} for a in analyses]

            # Update data-update-timestamp to trigger table refresh
            timestamp = datetime.now().timestamp()  # Use current timestamp as a trigger

            return (
                is_open, stock_symbol, stock_name, options, str(analysis_doc['_id']),
                new_analysis_text, timestamp
            )

        # Handle cell selection
        active_cell = None
        data = None

        if triggered_id == 'stocks-table':
            active_cell, data = stocks_active_cell, stocks_data
        elif triggered_id == 'top-performers-table':
            active_cell, data = top_active_cell, top_data
        elif triggered_id == 'worst-performers-table':
            active_cell, data = worst_active_cell, worst_data
        elif triggered_id == 'latest-results-table':
            active_cell, data = latest_active_cell, latest_data

        # *** This is where your code snippet goes ***
        # When handling cell selection:
        if active_cell and data and active_cell['column_id'] == 'ai_indicator':
            # Use 'data' from 'derived_viewport_data'
            row = data[active_cell['row']]
            stock_name = row['company_name']
            stock_symbol = row['symbol']
            analyses = get_previous_analyses(stock_symbol)

            if analyses:
                options = [{'label': format_label(a['timestamp']), 'value': str(a['_id'])} for a in analyses]
                latest_analysis = analyses[-1]
                default_value = str(latest_analysis['_id'])
                content = latest_analysis['analysis']
            else:
                options = []
                default_value = None
                content = 'No previous analysis available.'

            return (
                True, stock_symbol, stock_name, options, default_value,
                content, dash.no_update
            )

        return (
            is_open, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update
        )

    @app.callback(
        [Output('batch-data-update-timestamp', 'data'),
         Output('batch-ai-feedback', 'children')],
        Input('batch-ai-refresh-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def batch_ai_analysis(n_clicks):
        if n_clicks is None:
            raise dash.exceptions.PreventUpdate

        def process_batch():
            df = fetch_latest_quarter_data()
            latest_quarter = df['quarter'].max()
            latest_stocks = df[df['quarter'] == latest_quarter]

            symbols = latest_stocks['symbol'].unique().tolist()

            # Fetch existing symbols with analyses
            existing_symbols = set(db.get_collection('ai_analysis').distinct('symbol', {'symbol': {'$in': symbols}}))

            # Filter out stocks that already have analyses
            stocks_to_analyze = latest_stocks[~latest_stocks['symbol'].isin(existing_symbols)]

            for index, row in stocks_to_analyze.iterrows():
                symbol = row['symbol']
                company_name = row['company_name']

                print(f"Fetching analysis for {company_name}")
                analysis_text = fetch_stock_analysis(company_name)

                if analysis_text is None:
                    print(f"Failed to fetch analysis for {company_name}")
                    continue

                analysis_doc = {
                    'company_name': company_name,
                    'symbol': symbol,
                    'analysis': analysis_text,
                    'timestamp': datetime.now(),
                }
                db.get_collection('ai_analysis').insert_one(analysis_doc)

                # Optional: Add a delay to respect API rate limits
                time.sleep(1)

            print("Batch AI analysis completed.")

        thread = threading.Thread(target=process_batch)
        thread.start()

        timestamp = datetime.now().timestamp()
        return timestamp, "Batch AI analysis started. This may take several minutes."
    
    # Add new callback for data refresh
    @app.callback(
        Output('overview-data-store', 'data'),
        [Input('overview-refresh-interval', 'n_intervals'),
         Input('quarter-dropdown', 'value')],
        background=True  # Use background callback for non-blocking updates
    )
    def refresh_data(n_intervals, selected_quarter):
        # Clear the cache to force refresh
        get_cached_data.cache_clear()
        df = get_cached_data()
        
        if selected_quarter:
            df = df[df['quarter'] == selected_quarter]
        
        return df.to_dict('records')


def format_label(timestamp):
    now = datetime.now()
    if timestamp.date() == now.date():
        return 'Today ' + timestamp.strftime('%H:%M')
    elif timestamp.date() == (now - timedelta(days=1)).date():
        return 'Yesterday ' + timestamp.strftime('%H:%M')
    else:
        return timestamp.strftime('%d %B %Y')

def handle_close_modal():
    return (
        False, dash.no_update, dash.no_update, dash.no_update,
        dash.no_update, dash.no_update, dash.no_update
    )

def handle_analysis_history_selection(is_open, stock_symbol, stock_name, existing_options, selected_analysis_id):
    analysis_doc = db.get_collection('ai_analysis').find_one({'_id': ObjectId(selected_analysis_id)})
    content = analysis_doc['analysis'] if analysis_doc else 'Analysis not found.'
    return (
        is_open, stock_symbol, stock_name, existing_options,
        selected_analysis_id, content, dash.no_update
    )

def handle_refresh_analysis(stock_name, stock_symbol, existing_options):
    new_analysis_text = fetch_stock_analysis(stock_name)
    if new_analysis_text is None:
        return (
            True, stock_symbol, stock_name, existing_options,
            dash.no_update, 'Error fetching new analysis.', dash.no_update
        )

    # Store new analysis
    analysis_doc = {
        'company_name': stock_name,
        'symbol': stock_symbol,
        'analysis': new_analysis_text,
        'timestamp': datetime.now(),
    }
    db.get_collection('ai_analysis').insert_one(analysis_doc)

    # Update options with the new analysis
    analyses = get_previous_analyses(stock_symbol)

    options = [{'label': format_label(a['timestamp']), 'value': str(a['_id'])} for a in analyses]

    # Update data-update-timestamp to trigger table refresh
    timestamp = datetime.now().timestamp()

    return (
        True, stock_symbol, stock_name, options, str(analysis_doc['_id']),
        new_analysis_text, timestamp
    )




