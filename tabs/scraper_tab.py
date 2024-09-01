# scraper_tab.py
import subprocess
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash import  html, callback_context

# Scraper page layout
def scraper_layout():
    return html.Div([
        html.H3("Stock Scraper"),
        dbc.Button("Scrape Latest Results", id="scrape-latest-button", color="primary"),
        dbc.Button("Scrape Best Performers", id="scrape-best-button", color="success", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Worst Performers", id="scrape-worst-button", color="danger", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Positive Turn Around", id="scrape-positive-turn-around-button", color="success", style={"marginLeft": "10px"}),
        dbc.Button("Scrape Negative Turn Around", id="scrape-negative-turn-around-button", color="danger", style={"marginLeft": "10px"}),
        html.Div(id='scraper-results', style={'marginTop': 20})
    ])

# Callback for scraper  
def register_scraper_callbacks(app):
    @app.callback(
        Output('scraper-results', 'children'),
        [Input('scrape-latest-button', 'n_clicks'),
         Input('scrape-best-button', 'n_clicks'),
         Input('scrape-worst-button', 'n_clicks'),
         Input('scrape-positive-turn-around-button', 'n_clicks'),
         Input('scrape-negative-turn-around-button', 'n_clicks')]
    )
    def trigger_scraper(latest_clicks, best_clicks, worst_clicks,positive_turnaround_clicks, negative_turnaround_clicks):
        ctx = callback_context

        if not ctx.triggered:
            return "Click a button to start scraping."
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        url_map = {
            'scrape-latest-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=LR&subType=yoy",
            'scrape-best-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=BP&subType=yoy",
            'scrape-worst-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=WP&subType=yoy",
            'scrape-positive-turn-around-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=PT&subType=yoy",
            'scrape-negative-turn-around-button': "https://www.moneycontrol.com/markets/earnings/latest-results/?tab=NT&subType=yoy"
        }

        url = url_map.get(button_id, None)
        if not url:
            return "Unknown button clicked."

        try:
            result = subprocess.run(['python3', './scraper/scrapedata.py', url], check=True, capture_output=True, text=True)
            return html.Div([
                html.P("Scraping started successfully!"),
                html.Pre(result.stdout)  # Display the output of the script
            ])
        except subprocess.CalledProcessError as e:
            return html.Div([
                html.P("There was an error during scraping."),
                html.Pre(e.stderr)  # Display any error messages
            ])
