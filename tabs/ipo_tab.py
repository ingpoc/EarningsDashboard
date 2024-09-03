import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from util.ipo_utils import get_combined_ipo_data, fetch_ipo_details
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ipo_layout():
    return html.Div([
        dcc.Location(id='ipo-url', refresh=False),
        html.H3("IPO Dashboard", className="mb-4"),
        dbc.Button("Refresh IPO Data", id="refresh-ipo-data", color="primary", className="mb-3"),
        dbc.Spinner(
            html.Div(id="ipo-tables-container"),
            color="primary",
            type="border",
        ),
        html.Div(id="ipo-details-container"),
        dbc.Button("Generate Groq Prompt", id="generate-groq-prompt", color="success", className="mt-3"),
        html.Div(id="groq-prompt-container", className="mt-3"),
        html.Div(id="groq-prompt-text", style={"display": "none"}),  # Hidden div to store the text
        dcc.Clipboard(
            target_id="groq-prompt-text",
            title="Copy to clipboard",
            style={"display": "inline-block", "fontSize": 20, "verticalAlign": "top"}
        ),
        dcc.Store(id="combined-ipo-store"),
    ])

def create_ipo_table(df, title):
    if df.empty:
        return html.Div([
            html.H4(title, className="mb-3"),
            html.P("No data available for this category.")
        ])

    columns = [
        {"name": "Company Name", "id": "Company Name"},
        {"name": "IPO Type", "id": "IPO Type"},
        {"name": "Open", "id": "Open"},
        {"name": "Close", "id": "Close"},
        {"name": "Status", "id": "Status"}
    ]

    return html.Div([
        html.H4(title, className="mb-3"),
        dash_table.DataTable(
            id=f"{title.lower().replace(' ', '-')}-table",
            columns=columns,
            data=df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'whiteSpace': 'normal',
                'height': 'auto',
            },
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
                    'if': {'column_id': 'IPO Type', 'filter_query': '{IPO Type} eq "Main"'},
                    'backgroundColor': '#e6f3ff',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'column_id': 'IPO Type', 'filter_query': '{IPO Type} eq "SME"'},
                    'backgroundColor': '#fff0e6',
                    'fontWeight': 'bold'
                }
            ],
            style_as_list_view=True,
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
        )
    ])

def create_ipo_details_card(details, ipo_type):
    common_fields = [
        ("Issue Size", "issue_size"),
        ("Price Band", "price_band"),
        ("Lot Size", "lot_size"),
        ("Subscription Dates", "subscription_dates"),
        ("Revenue", "revenue"),
        ("Net Profit", "net_profit"),
        ("P/E Ratio", "pe_ratio"),
        ("ROCE", "roce"),
        ("Debt to Equity", "debt_to_equity"),
    ]

    sme_specific_fields = [
        ("Sector", "sector"),
        ("Promoter Holding", "promoter_holding"),
    ]

    fields = common_fields + (sme_specific_fields if ipo_type == 'SME' else [])

    return dbc.Card([
        dbc.CardHeader(html.H4(f"IPO Details: {details['company_name']} ({ipo_type})")),
        dbc.CardBody([
            html.Div([
                html.Strong(f"{label}: "),
                html.Span(details.get(key, "N/A")),
                html.Br()
            ]) for label, key in fields
        ])
    ], className="mt-4")

def register_ipo_callbacks(app):
    @app.callback(
        Output("combined-ipo-store", "data"),
        Input("refresh-ipo-data", "n_clicks"),
        Input("ipo-url", "pathname"),
        State("combined-ipo-store", "data"),
        prevent_initial_call=False
    )
    def update_ipo_data(n_clicks, pathname, current_data):
        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'none'

        logger.info(f"update_ipo_data called with trigger: {trigger}")

        if trigger == "refresh-ipo-data":
            # Always fetch fresh data when the refresh button is clicked
            logger.info("Refreshing IPO data")
            try:
                combined_data = get_combined_ipo_data(from_db=False)
                return {k: v.to_dict('records') for k, v in combined_data.items()}
            except Exception as e:
                logger.error(f"Error refreshing IPO data: {str(e)}")
                return current_data or {}
        elif trigger == "ipo-url" or trigger == 'none':
            # Load from DB when navigating to the page or on initial load
            logger.info("Loading IPO data from database")
            try:
                combined_data = get_combined_ipo_data(from_db=True)
                return {k: v.to_dict('records') for k, v in combined_data.items()}
            except Exception as e:
                logger.error(f"Error loading initial IPO data: {str(e)}")
                return {}

        return current_data or {}


    @app.callback(
        Output("ipo-tables-container", "children"),
        Input("combined-ipo-store", "data")
    )
    def render_ipo_tables(combined_data):
        if not combined_data:
            return html.Div("No IPO data available. Please try refreshing.", className="text-danger")

        upcoming_table = create_ipo_table(pd.DataFrame(combined_data.get('upcoming', [])), "Upcoming IPOs")
        current_table = create_ipo_table(pd.DataFrame(combined_data.get('current', [])), "Current IPOs")
        closed_table = create_ipo_table(pd.DataFrame(combined_data.get('closed', [])), "Recently Closed IPOs")
        return [upcoming_table, current_table, closed_table]

    @app.callback(
        Output("ipo-details-container", "children"),
        [Input("upcoming-ipos-table", "active_cell"),
         Input("current-ipos-table", "active_cell"),
         Input("recently-closed-ipos-table", "active_cell")],
        State("combined-ipo-store", "data")
    )
    def display_ipo_details(upcoming_cell, current_cell, closed_cell, combined_data):
        ctx = callback_context
        if not ctx.triggered:
            return html.Div()

        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        selected_ipo = None
        if triggered_id == "upcoming-ipos-table" and upcoming_cell:
            selected_ipo = combined_data['upcoming'][upcoming_cell['row']]
        elif triggered_id == "current-ipos-table" and current_cell:
            selected_ipo = combined_data['current'][current_cell['row']]
        elif triggered_id == "recently-closed-ipos-table" and closed_cell:
            selected_ipo = combined_data['closed'][closed_cell['row']]

        if not selected_ipo:
            return html.Div()

        company_name = selected_ipo['Company Name']
        ipo_type = selected_ipo['IPO Type']
        details = fetch_ipo_details(company_name, ipo_type)

        return create_ipo_details_card(details, ipo_type)

    @app.callback(
        Output("ipo-analysis-container", "children"),
        Input("generate-ipo-analysis", "n_clicks"),
        State("combined-ipo-store", "data")
    )
    def generate_ipo_analysis(n_clicks, combined_data):
        if not n_clicks:
            raise PreventUpdate

        upcoming_ipos = combined_data.get('upcoming', [])
        current_ipos = combined_data.get('current', [])

        analysis = html.Div([
            html.H4("IPO Market Analysis"),
            html.P(f"Total Upcoming IPOs: {len(upcoming_ipos)}"),
            html.P(f"Total Current IPOs: {len(current_ipos)}"),
            html.H5("Hottest Sectors:"),
            html.Ul([html.Li("Technology"), html.Li("Healthcare"), html.Li("Renewable Energy")]),
            html.H5("Market Sentiment:"),
            html.P("The IPO market is showing strong momentum with several high-profile offerings in the pipeline."),
            html.H5("Investor Tips:"),
            html.Ul([
                html.Li("Research company fundamentals thoroughly"),
                html.Li("Consider the competitive landscape"),
                html.Li("Evaluate the management team's track record"),
                html.Li("Be cautious of over-hyped offerings")
            ])
        ])

        return dbc.Card(dbc.CardBody(analysis), className="mt-4")
    
    @app.callback(
    [Output("groq-prompt-container", "children"),
     Output("groq-prompt-text", "children")],
    Input("generate-groq-prompt", "n_clicks"),
    State("combined-ipo-store", "data")
)
    def generate_groq_prompt(n_clicks, combined_data):
        if not n_clicks or not combined_data:
            raise PreventUpdate

        current_ipos = combined_data.get('current', [])

        if not current_ipos:
            return html.Div("No current IPOs available for analysis.", className="text-warning"), ""

        # Limit to 5 current IPOs for a more focused analysis
        current_ipos = current_ipos[:5]

        numbered_ipos = "\n".join(f"{i+1}. {ipo['Company Name'].split('(')[0].strip()} " for i, ipo in enumerate(current_ipos))

        prompt = f"""Analyze the following current IPOs:
    {numbered_ipos}

    For each IPO, provide:
        1. Investment Recommendation: Brief summary based on market sentiment.
        2. Ranking for Investment Potential: Compared to other IPOs.
        3. Financial Health: Key growth metrics and profitability.
        4. Valuation and Pricing: Is it overvalued or fairly priced?
        5. GMP (Grey Market Premium): Indication of market interest.
        6. Risk Factors: Major risks to consider.

        Keep each analysis concise. Include relevant hashtags like #stockname #stockanalysis #Valuation #Financials #Metrics. In the end provide recommendation based on data about which IPO to invest in and which IPO to avoid"""


        prompt_display = dbc.Card([
            dbc.CardHeader("Current IPO Analysis Prompt", className="bg-primary text-white"),
            dbc.CardBody([
                html.Pre(prompt, style={"white-space": "pre-wrap", "word-break": "keep-all", "font-size": "0.9rem"}),
            ]),
            
        ], className="shadow")

        return prompt_display, prompt