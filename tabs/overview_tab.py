import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc
import pandas as pd
from dash.dash_table.Format import Format, Scheme
from util.utils import fetch_latest_quarter_data, process_estimates
from util.recommendation import generate_stock_recommendation
from dash.dependencies import Input, Output, State
import dash
from tabs.stock_details_tab import stock_details_layout

def overview_layout():
    df = fetch_latest_quarter_data()
    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    df['processed_estimates'] = df['estimates'].apply(process_estimates)
    # Generate recommendations for each row
    df['recommendation'] = df.apply(generate_stock_recommendation, axis=1)

    # Extract unique quarters from the data and sort them
    unique_quarters = sorted(df['quarter'].unique(), reverse=True)
    
    # Set the latest quarter as the default value
    latest_quarter = unique_quarters[0] if unique_quarters else None

    return dbc.Container([
        html.H2("Market Overview", className="text-center mb-4"),
        dcc.Dropdown(
            id='quarter-dropdown',
            options=[{'label': quarter, 'value': quarter} for quarter in unique_quarters],
            value=latest_quarter,  # Set the default value to the latest quarter
            placeholder="Select a quarter",
            className="mb-4"
        ),
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
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="overview-modal-title", className="text-primary")),
            dbc.ModalBody(id="overview-details-body", className="p-0"),
        ], id="overview-details-modal", size="lg", scrollable=True),
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
            {"name": "Recommendation", "id": "recommendation"},  # New column
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
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'fontSize': '15px',
            'border': '1px solid #dee2e6',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden'
        },
        style_data={
            'border': '1px solid #dee2e6',
        },
        style_cell_conditional=[
            {'if': {'column_id': 'company_name_with_indicator'}, 'minWidth': '200px', 'maxWidth': '300px'},
            {'if': {'column_id': 'cmp'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'net_profit_growth'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'strengths'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'weaknesses'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'result_date_display'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'processed_estimates'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'piotroski_score'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'recommendation'}, 'minWidth': '150px', 'maxWidth': '200px'},  # New column style
        ],
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
            {'if': {'filter_query': '{processed_estimates} < 0', 'column_id': 'processed_estimates'}, 'color': '#dc3545'},
            {'if': {'filter_query': '{processed_estimates} > 0', 'column_id': 'processed_estimates'}, 'color': '#28a745'},
            {'if': {'column_id': 'strengths'}, 'backgroundColor': 'rgba(40, 167, 69, 0.1)'},
            {'if': {'column_id': 'weaknesses'}, 'backgroundColor': 'rgba(220, 53, 69, 0.1)'},
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
        [Input('quarter-dropdown', 'value')]
    )
    def update_tables(selected_quarter):
        df = fetch_latest_quarter_data()
        
        if selected_quarter:
            df = df[df['quarter'] == selected_quarter]
        
        top_performers = df.sort_values(by="net_profit_growth", ascending=False).head(10)
        worst_performers = df.sort_values(by="net_profit_growth", ascending=True).head(10)
        latest_results = df.sort_values(by="result_date", ascending=False).head(10)
        
        return (top_performers.to_dict('records'),
                worst_performers.to_dict('records'),
                latest_results.to_dict('records'),
                df.to_dict('records'))
