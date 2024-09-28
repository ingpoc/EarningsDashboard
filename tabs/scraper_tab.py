import subprocess
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash import html, callback_context
import threading
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scraper page layout
def scraper_layout():
    return html.Div([
        html.H3("Stock Scraper", className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("Scrape Latest Results", id="scrape-latest-button", color="primary", className="mb-2 w-100"), width=4),
            dbc.Col(dbc.Button("Scrape Best Performers", id="scrape-best-button", color="success", className="mb-2 w-100"), width=4),
            dbc.Col(dbc.Button("Scrape Worst Performers", id="scrape-worst-button", color="danger", className="mb-2 w-100"), width=4),
        ]),
        dbc.Row([
            dbc.Col(dbc.Button("Scrape Positive Turn Around", id="scrape-positive-turn-around-button", color="success", className="mb-2 w-100"), width=4),
            dbc.Col(dbc.Button("Scrape Negative Turn Around", id="scrape-negative-turn-around-button", color="danger", className="mb-2 w-100"), width=4),
            dbc.Col(dbc.Button("Scrape Actual vs Estimates", id="scrape-estimates-button", color="info", className="mb-2 w-100"), width=4),
        ]),
        dbc.Button("Scrape IPO Data", id="scrape-ipo-button", color="warning", className="mb-4"),
        dbc.Alert(id='scraper-results', is_open=False, duration=4000),
        html.Div(id='scraper-log', className="mt-3")
    ])

# Callback for scraper
def register_scraper_callbacks(app):
    @app.callback(
        [Output('scraper-results', 'children'),
         Output('scraper-results', 'color'),
         Output('scraper-results', 'is_open'),
         Output('scraper-log', 'children')],
        [Input('scrape-latest-button', 'n_clicks'),
         Input('scrape-best-button', 'n_clicks'),
         Input('scrape-worst-button', 'n_clicks'),
         Input('scrape-positive-turn-around-button', 'n_clicks'),
         Input('scrape-negative-turn-around-button', 'n_clicks'),
         Input('scrape-estimates-button', 'n_clicks'),
         Input('scrape-ipo-button', 'n_clicks')]
    )
    def trigger_scraper(latest_clicks, best_clicks, worst_clicks, positive_turnaround_clicks, negative_turnaround_clicks, estimates_clicks, ipo_clicks):
        ctx = callback_context

        if not ctx.triggered:
            return "", "", False, ""

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        url_map = {
            'scrape-latest-button': ("https://www.moneycontrol.com/markets/earnings/latest-results/?tab=LR&subType=yoy", "earnings"),
            'scrape-best-button': ("https://www.moneycontrol.com/markets/earnings/latest-results/?tab=BP&subType=yoy", "earnings"),
            'scrape-worst-button': ("https://www.moneycontrol.com/markets/earnings/latest-results/?tab=WP&subType=yoy", "earnings"),
            'scrape-positive-turn-around-button': ("https://www.moneycontrol.com/markets/earnings/latest-results/?tab=PT&subType=yoy", "earnings"),
            'scrape-negative-turn-around-button': ("https://www.moneycontrol.com/markets/earnings/latest-results/?tab=NT&subType=yoy", "earnings"),
            'scrape-estimates-button': ("https://www.moneycontrol.com/markets/earnings/estimates/?tab=Estimates%20Vs%20Actuals&type=All", "estimates"),
            'scrape-ipo-button': ("https://www.moneycontrol.com/ipo/", "ipo")
        }

        url, scrape_type = url_map.get(button_id, (None, None))
        if not url:
            return "Unknown button clicked.", "warning", True, ""

        def run_scraper():
            try:
                result = subprocess.run(['python3', './scraper/scrapedata.py', url, scrape_type], check=True, capture_output=True, text=True)
                logger.info(result.stdout)
                return (f"Scraping of {scrape_type} data completed successfully!", "success", True, html.Pre(result.stdout))
            except subprocess.CalledProcessError as e:
                logger.error(e.stderr)
                return (f"Error during scraping: {e.stderr}", "danger", True, html.Pre(e.stderr))

        # Run scraper in a separate thread to avoid blocking
        thread = threading.Thread(target=run_scraper)
        thread.start()

        return (f"Started scraping {scrape_type} data...", "info", True, "")
