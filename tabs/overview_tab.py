import dash_bootstrap_components as dbc
from dash import html, dash_table
import pandas as pd
from dash.dash_table.Format import Format, Scheme
from util.utils import process_estimates

def create_data_table(id, data):
    return dash_table.DataTable(
        id=id,
        columns=[
            {"name": "Company Name", "id": "company_name_with_indicator", "presentation": "markdown"},
            {"name": "CMP", "id": "cmp", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            {"name": "P/E Ratio", "id": "ttm_pe", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            {"name": "Net Profit", "id": "net_profit", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Net Profit Growth(%)", "id": "net_profit_growth", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
            {"name": "Strengths", "id": "strengths", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Weaknesses", "id": "weaknesses", "type": "numeric", "format": Format(precision=0, scheme=Scheme.fixed)},
            {"name": "Result Date", "id": "result_date_display"},
            {"name": "Estimates (%)", "id": "processed_estimates", "type": "numeric", "format": Format(precision=2, scheme=Scheme.fixed)},
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
            'padding': '5px',
            'fontSize': '14px',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'minWidth': '50px',
            'maxWidth': '180px',
        },
        style_cell_conditional=[
            {'if': {'column_id': 'company_name_with_indicator'}, 'minWidth': '200px', 'maxWidth': '300px'},
            {'if': {'column_id': 'cmp'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'ttm_pe'}, 'minWidth': '80px', 'maxWidth': '100px'},
            {'if': {'column_id': 'net_profit'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'net_profit_growth'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'strengths'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'weaknesses'}, 'minWidth': '70px', 'maxWidth': '90px'},
            {'if': {'column_id': 'result_date_display'}, 'minWidth': '100px', 'maxWidth': '120px'},
            {'if': {'column_id': 'processed_estimates'}, 'minWidth': '80px', 'maxWidth': '100px'},
        ],
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{processed_estimates} < 0', 'column_id': 'processed_estimates'}, 'color': 'red'},
            {'if': {'filter_query': '{processed_estimates} > 0', 'column_id': 'processed_estimates'}, 'color': 'green'},
            {'if': {'column_id': 'strengths'}, 'backgroundColor': 'rgba(0, 255, 0, 0.1)'},
            {'if': {'column_id': 'weaknesses'}, 'backgroundColor': 'rgba(255, 0, 0, 0.1)'},
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'fontSize': '15px',
        },
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

def overview_layout(df):
    df['result_date_display'] = df['result_date'].dt.strftime('%d %b %Y')
    df['processed_estimates'] = df['estimates'].apply(process_estimates)

    top_performers = df.sort_values(by="net_profit_growth", ascending=False).head(10)
    worst_performers = df.sort_values(by="net_profit_growth", ascending=True).head(10)
    latest_results = df.sort_values(by="result_date", ascending=False).head(10)

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
                create_data_table('stocks-table', df),
            ], md=12),
        ]),
    ], fluid=True)
